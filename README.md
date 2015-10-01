# pyWebIRC
A fully server side based IRC bouncer written in python and flask. Joined channels are logged, so you don't miss anything. Write messages from every computer you want. Multiple servers are supported. 

# NEEDED SOFTWARE
What you need:
- flask
- flask-login 
- and the mini IRC library.
Everything should be available through your package manager. With archlinux, simply run:
 pacman -S python2-flask, python2-flask-login, python2-irc

# INSTALLATION
Move pyWebIRC.cfg.template to pyWebIRC.cfg and edit the files according to your needs.
the password is a sha224 hash, which can be generated with python:
- set a login and password (plain text)
- For each server you want to connect add a new (unique) section with server adress, port, nick and channels to Join

Start the client with:
 python2 pyWebIRC.py

the bouncer can be reached with any browser and your localip:
 http://localhost:5000

# TODO
a lot of todos:
- set port and ip in config file
- move flask stuff to class
- more event handlers
- add CSS
- keep messages on reload (set interval in the config file)
- error handling!
Feel free to contribute!
