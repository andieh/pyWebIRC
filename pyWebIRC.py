# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, Response
from jinja2 import evalcontextfilter, Markup, escape

from flask.ext.login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user

import re
import os
import time
from thread import start_new_thread

from modules.config import MyConfig
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

    if login == "admin":
        user = User("admin", "test")
        login_user(user)
        return user

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

    if "add" in request.args:
        login = request.form.get("login")
        password = request.form.get("password")
        if login and password:
            print "add user {} with password {}".format(login, password)
    
    if "del" in request.args:
        if "login" in request.args:
            login = request.args["login"]
            if login:
                print "delete user {}".format(login)

    if "edit" in request.args:
        if "login" in request.args:
            login = request.args["login"]
            if login:
                print "edit user {}".format(login)
    
    return render_template("admin.html")

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

    config = MyConfig("pyWebIRC.cfg")
    config.logBase = os.path.join("logs", config.flaskLogin)
    if not os.path.exists(config.logBase):
        print "create log path for user {}".format(config.flaskLogin)
        os.mkdir(config.logBase)

    for srv in config.servers.keys():
        print "start server {}".format(srv)
        server = config[srv]
        # TODO: logbase to config object
        config[srv]["bouncer"] = PyIrcBouncer(server, config.logBase)
        start_new_thread(config[srv]["bouncer"].start, ())
        cnt = 0
        while not config[srv]["bouncer"].connected:
            print "wait until server is ready..."
            time.sleep(1)
            cnt += 1
            if cnt > 5:
                print "failed to connect all channels."
                break

    app.debug = True

    app.run()
