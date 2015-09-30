# -*- coding: utf-8 -*-

import irc.bot
import irc.strings 

import sys
import os

class PyIrcBouncer(irc.bot.SingleServerIRCBot):
    def __init__(self, cfg):
        self.connected = False
        try:
            self.channel = cfg["channel"]
            self.nick = cfg["nick"]
            self.port = cfg["port"]
            self.server = cfg["server"]
        except KeyError:
            print "key missing in config file, channel, nick, port and server needed"
            sys.exit(1)

        irc.bot.SingleServerIRCBot.__init__(self, \
                [(self.server, self.port)], \
                self.nick, \
                self.nick)

        # check for log file
        self.logpath = "logs/{}".format(self.server)
        if not os.path.exists(self.logpath):
            print "create log path {}".format(self.logpath)
            os.mkdir(self.logpath)
        self.logfiles = {}
        
        self.connected = True

    def on_welcome(self, c, e):
        for channel in self.channel:
            print "join channel {} on {}".format(channel, self.server)
            c.join(channel)
            # log file
            fn = os.path.join(self.logpath, "{}.log".format(channel))
            self.logfiles[channel] = open(fn, "a")

    def leave(self):
        if not self.connected:
            return

        for chan in self.channels:
            self.send(chan, "goodbye")
            self.logfiles[chan].close()
        
        self.connection.close()
        self.connected = False
        
    def send(self, channel, msg):
        if not self.connected:
            print "not connected to {}".format(self.server)
            return 

        self.connection.privmsg(channel, msg.decode("utf-8"))
        self.log(channel, self.nick, msg.decode("utf-8"))

    def on_pubmsg(self, c, e):
        nick = e.source.split("!")[0]
        msg = e.arguments[0]
        self.log(e.target, nick, msg)

    def log(self, channel, nick, msg):
        w = "{}> {}".format(nick, msg.encode("utf-8"))
        self.logfiles[channel].write("{}\n".format(w))
        self.logfiles[channel].flush()
        print "[{}] {}".format(channel, w)


