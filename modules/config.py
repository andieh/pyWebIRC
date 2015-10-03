import ConfigParser
import sys
import os

class CoreConfig:
    def __init__(self, cfg):
        self.configFile = cfg
        login = None
        password = None
        self.config = ConfigParser.ConfigParser()
        self.users = []
        if not self.config.read(self.configFile):
            print "failed to read config file {}".format(self.configFile)
            sys.exit(1)

        login = self.config.get("config", "login")
        password = self.config.get("config", "password")

        if login is None or password is None:
            print "please set admin login and password"
            sys.exit(1)

    def __getitem__(self, key):
        return self.config.get("config", key)

class UserConfig:
    def __init__(self, cfg):
        self.configFile = cfg
        self.servers = []
        self.login = os.path.split(cfg)[1][:-4]
        self.password = None
        
        config = ConfigParser.ConfigParser()
        if not config.read(self.configFile):
            print "failed to read config file {}".format(self.configFile)
            sys.exit(1)
        self.config = {}
        self.config["login"] = self.login
        self.srv = {}

        for section in config.sections():
            if section == "config":
                for (k,v) in config.items(section):
                    self.config[k] = v
                continue

            self.servers.append(section)
            self.srv[section] = {}
            for (key, value) in config.items(section):
                v = value
                if key == "channel":
                    v = value.split(" ")
                elif key == "port":
                    v = int(value)
                self.srv[section][key] = v

    def server(self, server, key):
        return self.srv[server][key]

    def __getitem__(self, key):
        return self.config[key]

    def setLogPath(self, path):
        p = os.path.join(path, self.login)
        if not os.path.exists(p):
            os.mkdir(p)
            print "created log path for user {}".format(self.login)
        self.config["logPath"] = p

if __name__ == "__main__":
    cfg = MyConfig("pyIrc.cfg")
    for s in cfg.sections():
        print cfg[s]
