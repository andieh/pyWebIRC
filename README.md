# pyWebIRC
A fully server side based IRC bouncer and web client written in python and flask. Joined channels are logged, so you don't miss anything. Write messages from every computer you want. Multiple servers are supported. 

# NEEDED SOFTWARE
What you need:
- flask
- flask-login 
- and the mini IRC library.
Everything should be available through your package manager. With archlinux, simply run:
 pacman -S python2-flask, python2-flask-login, python2-irc

# INSTALLATION
Move pyWebIRC.cfg.template to pyWebIRC.cfg and edit the files according to your needs.
- set a login and password (plain text)
- more settings are commented

Start the client with:
 python2 pyWebIRC.py

the bouncer can be reached with any browser at the address specified in the config file:
 http://localhost:5000

Now login as the admin user and add as much user you need. Each user can specify their own servers and channels on the settings page.

# TODO
a lot of todos:
- move flask stuff to class
- more event handlers
- add CSS
- error handling!
- send commands to IRC server (/nick, /part, etc.)

Feel free to contribute!
