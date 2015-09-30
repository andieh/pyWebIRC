# pyWebIRC
a fully server side based IRC bouncer written in python and flask

# SOFTWARE
you need 
flask, flask-login and the mini IRC library.
with archlinux, simply run
pacman -S python2-flask, python2-flask-login, python2-irc

# INSTALLATION
Move pyWebIRC.cfg.template to pyWebIRC.cfg and edit the files according to your needs.
the password is a sha224 hash, which can be generated with python:
python> import hashlib
        print hashlib.sha224("your password").hexdigest()

currently only one server is supported, but as much channels as you want.

start the client with 
python2 pyWebIRC. 

the bouncer can be reached with any browser and your localip:
http://localhost:5000

# TODO
a lot of todos:
- multiple server support 
- move flask stuff to class
- login procedure?
- log need another user structure for multiple user support.
- i have no idea
