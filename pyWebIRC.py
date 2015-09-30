# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, Response
from jinja2 import evalcontextfilter, Markup, escape

from flask.ext.login import LoginManager, UserMixin, login_required, current_user

import re
import os
import time
import hashlib
from thread import start_new_thread

from modules.config import MyConfig
from modules.bouncer import PyIrcBouncer

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
app = Flask(__name__)
loginManager = LoginManager()
loginManager.init_app(app)
passes = {}

class User(UserMixin):
    # proxy for a database of users
    user_database = {}

    def __init__(self, username, password):
        self.id = username
        self.password = password

    @classmethod
    def get(cls,id):
        return cls.user_database.get(id)


@loginManager.request_loader
def load_user(request):
    password = request.form.get("password")
    login = request.form.get("login")

    if not password: password = None
    if not login: login = None

    if password is None or login is None:
        return None

    #pwd = User.get(login)
    pwd = passes.get(login)
    if pwd is None:
        return None
    
    h = hashlib.sha224(password).hexdigest()
    if (pwd == h):
        return User(login, pwd)

    return None


@app.route("/settings/", methods=["POST"])
@login_required
def protected():
    return render_template("settings.html", current_user=current_user, irc=app.ircServer)
    #return Response(response="Hello Protected World!", status=200)



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
def send():
    if request.method == 'POST':
        if request.form["msg"] and \
            request.form["server"] and \
            request.form["channel"]:
            msg = request.form["msg"].encode("utf-8")
            server = request.form["server"]
            channel = request.form["channel"]
            adr = "/channel/{}/{}".format(server, channel)
            app.ircServer.send("#{}".format(channel), msg)
            return redirect(adr)
    return "error"

@app.route("/channel/<server>/<channel>")
def show_channel(server=None, channel=None):
    if server is None or channel is None:
        return "error"

    fn = "logs/{}/#{}.log".format(server, channel)
    log = ""
    if os.path.exists(fn):
        f = open(fn, "r")
        log = f.read().decode("utf-8")
        log = log.split("\n")
        f.close()
    
    return render_template("channel.html", server=server, channel=channel, log=log)

if __name__ == "__main__":
    if not os.path.exists("logs"):
        os.mkdir("logs")

    cfg = MyConfig("pyIrc.cfg")
    
    passes[cfg.flaskLogin] = cfg.flaskPassword
    server = cfg["server"]
    bouncer = PyIrcBouncer(server)
    start_new_thread(bouncer.start, ())

    #app.debug = True
    app.ircServer = bouncer
    time.sleep(5)


    app.run()
