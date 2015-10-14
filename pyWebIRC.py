# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, \
        Response, session, jsonify, g
from jinja2 import evalcontextfilter, Markup, escape

from flask.ext.login import LoginManager, UserMixin, login_required, \
        current_user, login_user, logout_user

import re
import os
import time
import math
from thread import start_new_thread

from modules.config import UserConfig, CoreConfig
from modules.bouncer import PyIrcBouncer

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
app = Flask(__name__)
loginManager = LoginManager()
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'hmmseeeecret!'
loginManager.init_app(app)
config = None
waiter = None

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class IP():
    def __init__(self, ip):
        timestamp = int(time.time())
        self.ip = ip
        self.lastAccess = self.firstAccess = timestamp
        # store access tries in the last n seconds
        self.accesses = []
        self.logTime = 10

    def update(self):
        timestamp = int(time.time())
        self.lastAccess = timestamp
        self.accesses.append(timestamp)
        self.accesses = [ts for ts in self.accesses if timestamp - ts < self.logTime ]

    def tries(self):
        return len(self.accesses)

    def age(self):
        return int(time.time()) - self.firstAccess

class Waiter():
    def __init__(self):
        print "waiter initialized"
        self.ips = {}
        
    def cleanup(self):
        # cleanup ips after a threshold of time
        threshold = 60*60*24 # seconds
        
        current = int(time.time())
        for ip in self.ips.keys():
            if self.ips[ip].age() > threshold:
                self.ips.pop(ip)

    def check(self, ip):
        self.cleanup()
        
        if not ip in self.ips:
            self.ips[ip] = IP(ip)

        self.ips[ip].update()
        tries = self.ips[ip].tries()
        wait = math.exp(tries-5)
        if wait < 1:
            return True
        
        else:
            if wait > 60:
                wait = 60
            #time.sleep(wait)
            return False
            
        return True

class User(UserMixin):
    # proxy for a database of users
    user_database = {}

    def __init__(self, username, password):
        self.id = username
        self.password = password

    @classmethod
    def get(cls,id):
        return cls.user_database.get(id)

@app.route("/")
def main():
    if not waiter.check(request.remote_addr):
        return "denied!"

    return render_template("login.html")

#executed before view is rendered. maybe needed
@app.before_request
def before_request():
    pass

@loginManager.user_loader
def load_user_from_session(userid):
    user = User(userid, "from_session")
    login_user(user)
    return user

@loginManager.request_loader
def load_user(request):
    password = request.form.get("password")
    login = request.form.get("login")
    if not password: password = None
    if not login: login = None

    if password is None or login is None:
        return None

    # check for admin account
    ad = config["admin"]
    if login == ad["login"] and password == ad["password"]:
        user = User(ad["login"], ad["password"])
        login_user(user)
        return user

    # try to login regular User
    if login not in config["admin"].users:
        return None

    if config[login]["password"] == password:
        user = User(login, password)
        login_user(user)
        return user

    return None

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")

@app.route("/admin/", methods=["GET", "POST"])
@login_required
def admin():
    if current_user.id != "admin":
        return "No access!"

    cfgDir = "config"
    if not os.path.exists(cfgDir):
        os.mkdir(cfgDir)

    error = []
    if "add" in request.args:
        login = request.form.get("login")
        password = request.form.get("password")
        if login and password:
            fn = "{}/{}.cfg".format(cfgDir,login)
            if os.path.exists(fn):
                error.append("user already exists")
            elif login.find(" ") != -1:
                error.append("no whitespaces allowed in username")
            else:
                f = open(fn, "w")
                f.write("[config]\n")
                f.write("password = {}\n".format(password))
                f.write("timeout = 10\n")
                f.write("\n")
                f.close()

                values = {}
                values["password"] = password
                values["timeout"] = str(10)
                values["file"] = os.path.join(config["admin"]["config_directory"], "{}.cfg".format(login))
                values["login"] = login
                cfg = UserConfig(values, True)
                cfg.setLogPath(config["admin"]["log_directory"])
                config[login] = cfg
                config["admin"].users.append(login)

                print "add user {} with password {}".format(login, password)
    
    if "del" in request.args:
        if "login" in request.args:
            login = request.args["login"]
            if login:
                print "delete user {}".format(login)
                fn = "{}/{}.cfg".format(cfgDir, login)
                if login and os.path.exists(fn):
                    os.unlink(fn)

    cfgs = [ f[:-4] for f in os.listdir(cfgDir) if os.path.isfile(os.path.join(cfgDir,f)) ]
    return render_template("admin.html", users=cfgs, error=error)

@app.route("/settings/", methods=["GET", "POST"])
@login_required
def settings():

    values = {}
    error = []
    if "del" in request.args:
        if "server" in request.args:
            server = request.args["server"]
            config[current_user.id].removeServer(server)

    else:
        names = ["name", "server", "nick", "port", "channel"]

        for n in names:
            values[n] = request.form.get(n)
            if values[n] is None:
                error = []
                values = {}
                break
            if not values[n]:
                error.append("missing value for field {}".format(n))

        if len(values) and not len(error):
            print "add new server {}".format(values["name"])
            if config[current_user.id].addNewServer(values):
                config[current_user.id].srv[values["name"]]["bouncer"] = PyIrcBouncer(config[current_user.id], values["name"])
                start_new_thread(config[current_user.id].srv[values["name"]]["bouncer"].start, ())
                values = {}
            else:
                error.append("failed to parse values!")
        
    return render_template("settings.html", cfg=config[current_user.id], error=error, values=values)

@app.route("/load/", methods=["POST"])
@login_required
def protected():
    # maybe show settings page here, but take first 
    # server / channel to show something.
    # could be better
    #return render_template("settings.html", current_user=current_user, cfg=config)

    if current_user.id == config["admin"]["login"]:
        return redirect("/admin/")
    
    servers = config[current_user.id].servers
    if not len(servers):
        error = []
        values = {}
        return render_template("settings.html", cfg=config[current_user.id], error=error, values=values)

    server = servers[0]
    channel = config[current_user.id].server(server, "channel")[0][1:]
    adr = "/channel/{}/{}".format(server, channel)
    return redirect(adr)

@app.route("/send", methods = ['POST', 'GET'])
@login_required
def send():
    if request.method == 'POST':
        if request.form["msg"] and \
            request.form["server"] and \
            request.form["channel"]:
            msg = request.form["msg"].encode("utf-8")
            server = request.form["server"]
            channel = request.form["channel"]
            print "send {} to {} and {}".format(msg, server, channel)
            adr = "/channel/{}/{}".format(server, channel)
            b = config[current_user.id].server(server, "bouncer")
            b.send("#{}".format(channel), msg)
            return redirect(adr)
    return "error"

@app.route("/channel/<server>/<channel>")
@login_required
def show_channel(server=None, channel=None):
    if server is None or channel is None:
        return "error"

    log = []
    srv = config[current_user.id].srv[server]["bouncer"]
    nick = config[current_user.id].srv[server]["nick"]
    fn = os.path.join(srv.logpath, "#{}.log".format(channel))
    if os.path.exists(fn):
        f = open(fn, "r")
        l = f.read().decode("utf-8")
        l = l.split("\n")
        f.close()

        # do html editing in the renderer
        for line in l:
            if line.startswith("*>"):
                nl = "<i>{}</i>".format(line)
            elif line.find(nick) != -1 and not line.startswith(nick):
                nl = "<b>{}</b>".format(line)
            else:
                nl = line
            log.append(nl)

    json = request.args.get('json', None)
    if json is not None:
        return jsonify(log=log)
    else:
        return render_template("channel.html", server=server, channel=channel, log=log, cfg=config[current_user.id])

if __name__ == "__main__":
    # TODO: replace logs path with path from config?
    if not os.path.exists("logs"):
        print "create log path"
        os.mkdir("logs")

    # read configuration
    config = {}
    # admin configuration
    config["admin"] = CoreConfig("pyWebIRC.cfg")
    logPath = config["admin"]["log_directory"]
    if not os.path.exists(logPath):
        os.mkdir(logPath)
        print "create log path {}".format(logPath)

    # user configs
    cfgDir = config["admin"]["config_directory"]
    if not os.path.exists(cfgDir):
        os.mkdir(cfgDir)

    cfgs = [ f for f in os.listdir(cfgDir) if os.path.isfile(os.path.join(cfgDir,f)) ]
    for cf in cfgs:
        conf = UserConfig(os.path.join(cfgDir, cf))
        conf.setLogPath(logPath)
        config[conf.login] = conf
        config["admin"].users.append(conf.login)

    for user in config["admin"].users:
        print "load server settings for user {}".format(user)
        for srv in config[user].servers:
            print "start server {}".format(srv)
            config[user].srv[srv]["bouncer"] = PyIrcBouncer(config[user], srv)
            start_new_thread(config[user].srv[srv]["bouncer"].start, ())
            cnt = 0
            while not config[user].srv[srv]["bouncer"].connected:
                print "wait until server is ready..."
                time.sleep(1)
                cnt += 1
                if cnt > 5:
                    print "failed to connect all channels."
                    break
    waiter = Waiter()

    #app.debug = True
    try:
        host = config["admin"]["host"]
        port = int(config["admin"]["port"])
    except:
        print "failed to parse host and port from config file!"
        sys.exit(1)
    app.run(host=host, port=port)
