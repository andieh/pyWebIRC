import ConfigParser
import sys

class MyConfig:
    def __init__(self, cfg):
        self.configFile = cfg
        self.servers = {}
        self.flaskLogin = None
        self.flaskPassword = None
        
        self.config = ConfigParser.ConfigParser()
        if not self.config.read(self.configFile):
            print "failed to read config file {}".format(self.configFile)
            sys.exit(1)

        for section in self.config.sections():
            if section == "user":
                try:
                    self.flaskLogin = self.config.get(section, "login")          
                    self.flaskPassword = self.config.get(section, "password")          
                except ConfigParser.NoOptionError:
                    print "login and password are needed!"
                    sys.exit(1)
                except:
                    print "error parsing config!"
                    sys.exit(1)

                continue
            self.servers[section] = {}
            for (key, value) in self.config.items(section):
                v = value
                if key == "channel":
                    v = value.split(" ")
                elif key == "port":
                    v = int(value)

                self.servers[section][key] = v

        if self.flaskLogin is None or self.flaskPassword is None:
            print "no user or password set!"
            sys.exit(1)

    def sections(self):
        return self.servers.keys()

    def __getitem__(self, key):
        return self.servers[key]

if __name__ == "__main__":
    cfg = MyConfig("pyIrc.cfg")
    for s in cfg.sections():
        print cfg[s]
