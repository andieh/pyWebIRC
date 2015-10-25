# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, \
        Response, session, jsonify, g
from jinja2 import evalcontextfilter, Markup, escape

from flask.ext.login import LoginManager, UserMixin, login_required, \
        current_user, login_user, logout_user

import re
import os
import time, datetime
import hashlib
from thread import start_new_thread

from modules.config import UserConfig, CoreConfig
from modules.bouncer import PyIrcBouncer

from utils import Waiter, IP
from user import User

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
app = Flask(__name__)

# init login manager
loginManager = LoginManager()
loginManager.session_protection = "strong"


app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'hmmseeeecret!'
loginManager.init_app(app)

# mmmh, threaded-web-applic using un-managed globals, is this a good idea?
config = None
waiter = None
enableDebug = False

if not enableDebug:
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)


# TODO: move views to an actual views.py file instead of littering the main exe
@app.route("/")
def main():
    if not waiter.check(request.remote_addr):
        return "denied!"
    return render_template("login.html")

# executed before view is rendered. maybe needed
@app.before_request
def before_request():
    pass

@loginManager.unauthorized_handler
def unauthorized_callback():
    # check when exactly these function is called.
    logout_user()
    session.clear()
    return redirect("/")
    
@loginManager.user_loader
def load_user_from_session(userid):
    """Load user session using our UserManager (TODO: 'UserManager' :D)"""
    user = User(userid, "from_session")
    login_user(user)
    return user

@loginManager.request_loader
def load_user(request):
    """Request handler for an user login"""
    password = request.form.get("password")
    login = request.form.get("login")
    phash = User.get_password_hash(password)

    # invalid or no credentials
    if not password: password = None
    if not login: login = None
    if password is None or login is None:
        return None
    
    # check for admin account
    ad = config["admin"]
    # i really don't understand your password hashing style :D
    if login == ad["login"] and phash == User.get_password_hash(ad["password"]):
        user = User(ad["login"], ad["password"])
        login_user(user)
        return user

    # try to login regular User
    if login not in config["admin"].users:
        return None

    # admin user login
    if config[login]["password"] == phash:
        user = User(login, phash)
        login_user(user)
        return user

    return None

@app.route("/logout/")
#@login_required
def logout():
    """Logout the user and destroy session"""
    logout_user()
    session.clear()
    return redirect("/")

@app.route("/admin/", methods=["GET", "POST"])
@login_required
def admin():
    """Show admin interface to add/remove/edit users"""
    # TODO: mmh, what if I choose an login equal to the admin user-login-name
    if current_user.id != config["admin"]["login"]:
        return "No access!"

    # check for config dir, create if necassary
    cfgDir = config["admin"]["config_directory"]
    if not os.path.exists(cfgDir):
        os.mkdir(cfgDir)

    error = []
    # add user config
    if "add" in request.args:
        login = request.form.get("login")
        password = request.form.get("password")
        if login and password:
            phash = User.get_password_hash(password)

            fn = "{}/{}.cfg".format(cfgDir,login)
            if phash is None:
                error.append("Could not generate password hash")
            elif os.path.exists(fn):
                error.append("user already exists")
            elif login.find(" ") != -1:
                error.append("no whitespaces allowed in username")
            elif len(config["admin"].users) > config["admin"]["paranoid.max_users"]:
                error.append("server is configured to not allow any more users!")
            else:
                f = open(fn, "w")
                f.write("[config]\n")
                f.write("password = {}\n".format(phash))
                f.write("timeout = 10\n")
                f.write("\n")
                f.close()

                values = {}
                values["password"] = phash
                values["timeout"] = str(10)
                values["file"] = os.path.join(cfgDir, "{}.cfg".format(login))
                values["login"] = login
                cfg = UserConfig(values, True)
                cfg.setLogPath(config["admin"]["log_directory"])
                config[login] = cfg
                config["admin"].users.append(login)

    # delete user config
    if "del" in request.args:
        if "login" in request.args:
            login = request.args["login"]
            if login:
                fn = "{}/{}.cfg".format(cfgDir, login)
                if login and os.path.exists(fn):
                    os.unlink(fn)

    # every file inside the config-dir is an user-config-file ? mmmh, 
    cfgs = [ f[:-4] for f in os.listdir(cfgDir) \
            if os.path.isfile(os.path.join(cfgDir, f)) ]
    return render_template("admin.html", users=cfgs, error=error)

@app.route("/settings/", methods=["GET", "POST"])
@login_required
def settings():
    """Access and modify the user-specific config, i.e., irc-server config(s)"""
    values = {}
    error = []
    # remove server entry
    if "del" in request.args:
        if "server" in request.args:
            server = request.args["server"]
            config[current_user.id].removeServer(server)

    # add new server entry
    elif request.method == "POST":
        names = ["name", "server", "nick", "port", "channel"]
        # check field contents
        for n in names:
            values[n] = request.form.get(n)
            if values[n] is None:
                error = []
                values = {}
                break
            if not values[n]:
                error.append("missing value for field {}".format(n))

        # check, if server/host is allowed due to restrictions
        asrv = config["admin"]["paranoid.allow_servers"]
        if asrv and not any(re.match("^" + pat + "$", values["server"]) for pat in asrv):
            error.append("Server is configured to accept only specific hosts")
            error.append("The chosen one does not match!")
            
        if len(values) and not len(error):
            print "add new server {}".format(values["name"])
            if config[current_user.id].addNewServer(values):
                
                config[current_user.id].srv[values["name"]]["bouncer"] = \
                        PyIrcBouncer(config[current_user.id], values["name"])
                # start bouncer thread
                start_new_thread(config[current_user.id].srv[
                    values["name"]]["bouncer"].start, ())

                values = {}
            else:
                error.append("failed to parse values!")
        
    return render_template("settings.html", cfg=config[current_user.id], 
            error=error, values=values)

@app.route("/load/", methods=["POST"])
@login_required
def protected():
    """Called directly after login, might be the place to add some security :D"""

    if current_user.id == config["admin"]["login"]:
        return redirect("/admin/")
    
    if current_user.id not in config:
        return redirect("/")

    servers = config[current_user.id].servers
    if not len(servers):
        error = []
        values = {}
        return render_template("settings.html", cfg=config[current_user.id], \
                error=error, values=values)

    server = servers[0]
    channel = config[current_user.id].server(server, "channel")[0][1:]
    adr = "/channel/{}/{}".format(server, channel)
    return redirect(adr)

# TODO: why also 'GET' ... 'POST' seems enough and more obvious for 'posting'
@app.route("/send", methods = ['POST', 'GET'])
@login_required
def send():
    """Receiving user data/msg -> forward to irc server"""
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
    """Render a single 'channel' chat-log on a given 'server'. FIXME: enc?"""

    #\TODO: log must be limited by length!
    #       either in json or "full" mode.a
    
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
        # \TODO move this to css
        for line in l:
            try:
                line = line.encode("utf-8")
            except Exception, e:
                print "failed to decode line: {}".format(line)
                continue

            ar = line.split(", ", 1)
            if len(ar) < 2:
                continue
            if ar[1].startswith("*>"):
                nl = "<i>{}</i>".format(ar[1])
            elif ar[1].find(nick) != -1 and not ar[1].startswith(nick):
                nl = "<b>{}</b>".format(ar[1])
            else:
                nl = ar[1]

            tss = datetime.datetime.fromtimestamp(int(ar[0])).strftime("%Y-%m-%d %H:%M:%S")
            log.append("<span class=small>[{}]</span> {}".format(tss, nl))

    # get a user list
    users = srv.getUsers(channel)
    
    # either jsonify the output to be handled by jQuery or render a HTML page
    json = request.args.get('json', None)
    if json is not None:
        return jsonify(log=log, users=users)

    return render_template("channel.html", \
            server=server, channel=channel, \
            log=log, \
            cfg=config[current_user.id], \
            users=users\
        )

if __name__ == "__main__":
    
    # read configuration
    config = {}
    
    # admin configuration
    config["admin"] = CoreConfig("pyWebIRC.cfg")

    # setup logs
    logPath = config["admin"]["log_directory"]
    if not os.path.exists(logPath):
        os.mkdir(logPath)
        print "create log path {}".format(logPath)

    # find & setup user config dir
    cfgDir = config["admin"]["config_directory"]
    if not os.path.exists(cfgDir):
        os.mkdir(cfgDir)

    # load user config is there are any
    cfgs = [ f for f in os.listdir(cfgDir) \
            if os.path.isfile(os.path.join(cfgDir,f)) ]
    for cf in cfgs:
        conf = UserConfig(os.path.join(cfgDir, cf))
        conf.setLogPath(logPath)
        config[conf.login] = conf
        config["admin"].users.append(conf.login)

    # bring up each user's bouncer
    for user in config["admin"].users:
        print "load server settings for user {}".format(user)
        for srv in config[user].servers:
            print "start server {}".format(srv)
            config[user].srv[srv]["bouncer"] = PyIrcBouncer(config[user], srv)
            # start bouncer thread
            start_new_thread(config[user].srv[srv]["bouncer"].start, ())
            cnt = 0
            while not config[user].srv[srv]["bouncer"].connected:
                print "wait until server is ready..."
                time.sleep(1)
                cnt += 1
                if cnt > 5:
                    print "failed to connect all channels."
                    break 
    # login timeout handler ? TODO: include into 'UserManager' (tm)
    waiter = Waiter(config["admin"])

    app.debug = enableDebug
    try:
        host = config["admin"]["host"]
        port = int(config["admin"]["port"])
    except:
        print "failed to parse host and port from config file!"
        sys.exit(1)
    
    app.run(host=host, port=port)
