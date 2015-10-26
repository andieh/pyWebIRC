import ConfigParser
import sys
import os



## TODO: maybe make access to config-vals attr-based instead of getitem-based
## now:         config["admin"]["stuff"]
## maybe later: config.admin.stuff

class BaseConfig:
    """
    Base for configuration handling.
    Allows dispatching into 'deeper' hierarchies through __getitem__.
    TODO: also apply to 'UserConfig' -> see TODO below...
    """
    section = None
    delim = "."

    def __init__(self, cfg):
        self.dispatch = {}
        self.vals = {}
        self.defaults = {}

        self.configFile = cfg
        self.config = ConfigParser.ConfigParser()
        
        if not self.config.read(self.configFile):
            print "failed to read config file {}".format(self.configFile)
            sys.exit(1)

    def __contains__(self, key):
        """
        Used for the 'in' operator, returns 'True' if 'key' in regualar 
        config, NOT if just a default is available
        """
        return key in self.vals or self.config.has_option(self.section, key)

    def __getitem__(self, key):
        """
        Key in'self.dispatch'? redirect/dispatch to value of 
        dict, anything _after_the 'cls.delim' 
        """

        # dispatch, if applicable
        toks = key.split(self.delim)
        if self.delim in key and toks[0] in self.dispatch:
            return self.dispatch[toks[0]][self.delim.join(toks[1:])]

        # handle this scope
        if key in self.vals:
            return self.vals[key]
        if key not in self and key in self.defaults:
            return self.defaults[key]
        return self.read_config(self.section, key)

    def read_config(self, section, key):
        """Return option 'key' from [section] from the actual config file"""
        if not self.config.has_option(section, key):
            return None
        return self.config.get(section, key)

    def set_default(self, key, val):
        """Returns 'val' for 'key', if 'key' was not explicitly set"""
        self.defaults[key] = val

    def set_val(self, key, val):
        """Returns 'val' in any case (overwrites), instead of the original one"""
        self.vals[key] = val 

    def process_val(self, key, func):
        """Applies 'func' on value 'key' (if existing), save it to 'self.vals'"""
        if key in self:
            self.vals[key] = func(self.read_config(self.section, key))

class ParanoidConfig(BaseConfig):
    """
    Section: [paranoid]
    Vars: allow_servers, max_requests_{sec,min,hour}, login_timeout
    """
    section = "paranoid"
    
    def __init__(self, cfg):
        BaseConfig.__init__(self, cfg)

        self.set_default("login_timeout", 1.0)
        self.set_default("max_requests_sec", 6.0)
        self.set_default("max_requests_min", 120.0)
        self.set_default("max_requests_hour", 3600.0)
        self.set_default("max_users", 1000)

        self.process_val("max_users", int)
        self.process_val("allow_servers", lambda x: x.split(","))

        
class CoreConfig(BaseConfig):
    """
    Section: [config]
    Vars: login, password, log_directory, config_directory, host, port
    """
    section = "config" 

    def __init__(self, cfg):
        BaseConfig.__init__(self, cfg)

        self.dispatch = {ParanoidConfig.section: ParanoidConfig(cfg)}

        login = None
        password = None
        self.users = []

        login = self.config.get(self.section, "login")
        password = self.config.get(self.section, "password")

        if login is None or password is None:
            print "please set admin login and password"
            sys.exit(1)

# mmh somehow not consistent with CoreConfig, avoid using BaseConfig for now...
# TODO: move user managment into pyWebIRC::User and this should only provide the
#       configurations for them, nothing more...
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
                        if v == ['']:
                            v = []
                        print v
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

    def removeChannel(self, server, channel):
        bouncer = self.srv[server]["bouncer"]
        f = open(self.configFile, "r")
        content = f.read()
        f.close()

        channel = "#{}".format(channel)
        srv = "[{}]".format(server)
        found = False
        nc = ""
        for line in content.split("\n"):
            if line == srv:
                found = True

            if line.startswith("channel"):
                line = line.split("=")[1].strip()
                channels = line.split()
                channels.remove(channel)
                newChannels = " ".join(channels)
                line = "channel = {}".format(newChannels)
                found = True
            
            nc += "{}\n".format(line)

        f = open(self.configFile, "w")
        f.write(nc)
        print nc
        f.close()
        
        bouncer.part(channel)

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

    def addChannel(self, name, channels):
        for chan in channels:
            if chan not in self.srv[name]["channel"]:
                self.srv[name]["channel"].append(chan)
                self.srv[name]["bouncer"].connection.join(chan)

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
