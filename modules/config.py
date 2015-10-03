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
    def __init__(self, cfg, new=False):
        self.servers = []
        self.srv = {}
        
        if new:
            self.config = cfg
            self.login = cfg["login"]
            self.config.pop("login")
            self.configFile = cfg["file"]
            self.config.pop("file")
            self.password = cfg["password"]

            return

        self.configFile = cfg
        self.login = os.path.split(cfg)[1][:-4]
        self.password = None
        
        config = ConfigParser.ConfigParser()
        if not config.read(self.configFile):
            print "failed to read config file {}".format(self.configFile)
            sys.exit(1)
        self.config = {}
        self.config["login"] = self.login

        for section in config.sections():
            if section == "config":
                for (k,v) in config.items(section):
                    self.config[k] = v
                continue

            self.servers.append(section)
            self.srv[section] = {}
            try:
                for (key, value) in config.items(section):
                    v = value
                    if key == "channel":
                        v = value.split(" ")
                    elif key == "port":
                        v = int(value)
                    self.srv[section][key] = v
            except:
                print "failed to parse config file"
                sys.exit(1)
            self.srv[section]["name"] = section

    def server(self, server, key):
        return self.srv[server][key]

    def __getitem__(self, key):
        return self.config[key]

    def removeServer(self, name):
        bouncer = self.srv[name]["bouncer"]
        bouncer.leave()
        self.servers.remove(name)
        self.srv.pop(name)
        f = open(self.configFile, "r")
        content = f.read()
        f.close()

        nc = ""
        delete = False
        for line in content.split("\n"):
            if line == "[{}]".format(name):
                delete = True
            elif line.startswith("["):
                delete = False
            if not delete:
                nc += "{}\n".format(line)

        f = open(self.configFile, "w")
        f.write(nc)
        f.close()

    def addNewServer(self, values):
        names = values.keys()
        name = values["name"]
        content = ""
        content += "[{}]\n".format(name)
        names.remove("name")
        self.servers.append(name)
        self.srv[name] = {}
        for n in names:
            content += "{} = {}\n".format(n, values[n])
            self.srv[name][n] = values[n]
        
        try:
            self.srv[name]["port"] = int(self.srv[name]["port"])
            self.srv[name]["channel"] = self.srv[name]["channel"].split(" ")
            self.srv[name]["name"] = name
        except:
            self.srv.pop(name)
            self.servers.remove(name)
            return False

        f = open(self.configFile, "a")
        f.write(content)
        f.close()

        return True

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
