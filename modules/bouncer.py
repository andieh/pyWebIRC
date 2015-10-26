# -*- coding: utf-8 -*-

import irc.bot
import irc.strings 
import irc.buffer

import sys
import os
import time, datetime

class PyIrcBouncer(irc.bot.SingleServerIRCBot):
    def __init__(self, cfg, name):
        self.connected = False
        self.channel = cfg.server(name, "channel")
        self.nick = cfg.server(name, "nick")
        self.port = cfg.server(name, "port")
        self.server = cfg.server(name, "server")

        self.users = {}

        irc.bot.SingleServerIRCBot.__init__(self, \
                [(self.server, self.port)], \
                self.nick, \
                self.nick)

        # i don't know, if this is a huge bug in 
        # the irc lib implementation?
        # the buffer only decodes utf-8 streams, 
        # and raises an exeption otherwise. this 
        # exeption can not be catched?
        # replace default buffer to Lenient Buffer,
        # which tries to decode it in latin-1 instead
        # of utf-8.
        self.connection.buffer_class = irc.buffer.LenientDecodingLineBuffer

        # check for log file
        self.logpath = os.path.join(cfg["logPath"], self.server)
        if not os.path.exists(self.logpath):
            print "create log path {}".format(self.logpath)
            os.mkdir(self.logpath)
        self.logfiles = {}

    def start(self):
        # is there a running variable?
        # maybe move this to a watchdog function?
        while 1:
            try:
                super(PyIrcBouncer, self).start()
            except Exception, e:
                print "this can't be true. the irc bouncer need a restart!"
                time.sleep(1)
                print str(e)

    def getUsers(self, channel=None):
        if channel is None:
            return self.users
        else:
            channel = "#{}".format(channel)
            if self.users.has_key(channel):
                return self.users[channel]
            else:
                return []

    def on_welcome(self, c, e):
        for channel in self.channel:
            print "join channel {} on {}".format(channel, self.server)
            c.join(channel)
            # log file
            fn = os.path.join(self.logpath, "{}.log".format(channel))
            self.logfiles[channel] = open(fn, "a")
            
            # keep a list of users in this channel
            self.users[channel] = []

        # connected, maybe add some error handling here...
        self.connected = True

    def part(self, channel):
        if not self.connected:
            return
        channel = "#{}".format(channel)
        if channel in self.channels:
            self.logfiles[channel].close()
            self.logfiles.pop(channel)
            self.connection.part(channel, "goodbye dudes")
            self.channels.remove(channel)
            
    def leave(self):
        if not self.connected:
            return

        for chan in self.channels:
            self.send(chan, "goodbye")
            self.logfiles[chan].close()
            self.logfiles.pop(chan)
        
        self.connection.close()
        self.connected = False
        
    def send(self, channel, msg):
        if not self.connected:
            print "not connected to {}".format(self.server)
            return 

        self.connection.privmsg(channel, msg.decode("utf-8"))
        self.log(channel, self.nick, msg.decode("utf-8"))

    def get_nick(self, full):
        return full.split("!")[0]

    def on_pubmsg(self, c, e):
        nick = self.get_nick(e.source)
        msg = e.arguments[0]
        self.log(e.target, nick, msg)

    def log(self, channel, nick, msg):
        try:
            ts = int(time.time())
            tstr = datetime.datetime.fromtimestamp(ts).\
                    strftime('%d-%m-%Y %H:%M:%S')
            msg = msg.encode("utf-8")
            w = "{}, {}> {}".format(ts, nick, msg)
            self.logfiles[channel].write("{}\n".format(w))
            self.logfiles[channel].flush()
            print "{} [{}] {}> {}".format(tstr, channel, nick, msg)
        except Exception, e:
            print "failed to log received IRC message, error was:"
            print str(e)

    def on_error(self, connection, event):
        print 15,
        print "error: {}".format(str(event.arguments))
        print event.source, event.target

    def on_join(self, connection, event):
        channel = event.target
        nick = self.get_nick(event.source)
        self.log(channel, "*", "{} enters the room!".format(nick))
        
        if nick not in self.users[channel]:
            self.users[channel].append(nick)
        else:
            print "warning: user {} already in list?".format(nick)

    def on_kick(self, connection, event):
        print 13,
        print "kick: {}".format(str(event.arguments))
        print event.source, event.target

    def on_mode(self, connection, event):
        print 12,
        print "mode: {}".format(str(event.arguments))
        print event.source, event.target

    def on_part(self, connection, event):
        channel = event.target
        nick = self.get_nick(event.source)

        
        if not channel.startswith("#"):
            channel = "#{}".format(channel)
        
        if nick in self.users[channel]:
            self.users[channel].remove(nick)
            self.log(channel[1:], "*", "{} leaves the room!".format(nick))
        else:
            print "warning: user {} was not on this server\
                    (but he / she should)!".format(nick)


    def on_ping(self, connection, event):
        #print "receive ping from server {}".format(event.target)
        pass

    def on_privmsg(self, connection, event):
        sender = self.get_nick(event.source)
        receiver = event.target
        msg = str(event.arguments[0])
        print "[{}> {}]".format(sender, msg)

    def on_privnotice(self, connection, event):
        server = event.source
        method = event.target
        msg = str(event.arguments[0])
        print "[{}] {}".format(server, msg)

    def on_pubnotice(self, connection, event):
        print 7,
        print "pubnotice: {}".format(str(event.arguments))
        print event.source, event.target

    def on_quit(self, connection, event):
        user = self.get_nick(event.source)
        for chan in self.channel:
            self.log(chan, "*", "{} leaves the server!".format(user))

    def on_invite(self, connection, event):
        print 5,
        print "invite: {}".format(str(event.arguments))
        print event.source, event.target

    def on_pong(self, connection, event):
        print 4,
        print "pong: {}".format(str(event.arguments))
        print event.source, event.target

    def on_action(self, connection, event):
        print 3,
        print "action: {}".format(str(event.arguments))
        print event.source, event.target

    def on_topic(self, connection, event):
        print 2,
        print "topic: {}".format(str(event.arguments))
        print event.source, event.target

    def on_namreply(self, connection, event):
        channel = event.arguments[1]#[1:]
        users = event.arguments[2]
        self.users[channel] = users.split(" ")

    def on_nick(self, connection, event):
        nick = self.get_nick(event.source)
        nNick = event.target
        for chan in self.channel:
            self.log(chan, "*", "{} is now known as {}".format(nick, nNick))

