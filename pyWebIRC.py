# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, Response
from jinja2 import evalcontextfilter, Markup, escape

from flask.ext.login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user

import re
import os
import time
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

class User(UserMixin):
    # proxy for a database of users
    user_database = {}

    def __init__(self, username, password):
        self.id = username
        self.password = password

    @classmethod
    def get(cls,id):
        return cls.user_database.get(id)

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

    # try to login regular user
    return None

    #pwd = User.get(login)
    if config.flaskLogin != login:
        pwd = None
    else:
        pwd = config.flaskPassword
    if pwd is None:
        return None
    
    if (pwd == password):
        user = User(login, pwd)
        login_user(user)
        return user

    return None

@app.route("/logout/")
@login_required
def logout():
    logout_user()
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

@app.route("/load/", methods=["POST"])
@login_required
def protected():
    # maybe show settings page here, but take first 
    # server / channel to show something.
    # could be better
    #return render_template("settings.html", current_user=current_user, cfg=config)

    if current_user.id == "admin":
        return redirect("/admin/")
    
    srv = config.servers.items()[0][1]
    server = srv["server"]
    channel = srv["channel"][0][1:]
    adr = "/channel/{}/{}".format(server, channel)
    return redirect(adr)



@app.template_filter()
@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br\>\n') \
        for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

@app.route("/")
def main():
    return render_template("login.html")

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
            adr = "/channel/{}/{}".format(server, channel)
            for srv in config.servers.keys():    
                if config.servers[srv]["server"] == server:
                    config.servers[srv]["bouncer"].send("#{}".format(channel), msg)
            return redirect(adr)
    return "error"

@app.route("/channel/<server>/<channel>")
@login_required
def show_channel(server=None, channel=None):
    if server is None or channel is None:
        return "error"

    log = ""
    fn = os.path.join(config.logBase, server, "#{}.log".format(channel))
    if os.path.exists(fn):
        f = open(fn, "r")
        log = f.read().decode("utf-8")
        log = log.split("\n")
        f.close()
    
    return render_template("channel.html", server=server, channel=channel, log=log, cfg=config)

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
    cfgs = [ f for f in os.listdir(cfgDir) if os.path.isfile(os.path.join(cfgDir,f)) ]
    for cf in cfgs:
        conf = UserConfig(os.path.join(cfgDir, cf))
        conf.setLogPath(os.path.join(logPath))
        config[conf.login] = conf
        config["admin"].users.append(conf.login)

    for user in config["admin"].users:
        print "load server settings for user {}".format(user)
        for srv in config[user].servers:
            print "start server {}".format(srv)
            config[user].bouncer = PyIrcBouncer(config[user], srv)
            start_new_thread(config[user].bouncer.start, ())
            cnt = 0
            while not config[user].bouncer.connected:
                print "wait until server is ready..."
                time.sleep(1)
                cnt += 1
                if cnt > 5:
                    print "failed to connect all channels."
                    break

    #app.debug = True
    app.run()
