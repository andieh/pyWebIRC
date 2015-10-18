# -*- coding: utf-8 -*-

import time 
import math

class IP(object):
    def __init__(self, ip):
        timestamp = int(time.time())
        self.ip = ip
        self.lastAccess = self.firstAccess = timestamp
        # store access tries in the last n seconds
        self.accesses = []
        self.logTime = 10

    def update(self):
        timestamp = int(time.time())
        self.lastAccess = timestamp
        self.accesses.append(timestamp)
        self.accesses = [ts for ts in self.accesses if timestamp - ts < self.logTime ]

    def tries(self):
        return len(self.accesses)

    def age(self):
        return int(time.time()) - self.firstAccess

class Waiter(object):
    def __init__(self, config):
        print "waiter initialized"
        self.ips = {}
        self.conf = config
        
    def cleanup(self):
        # cleanup ips after a threshold of time
        threshold = 60*60*24 # seconds
        
        current = int(time.time())
        for ip in self.ips.keys():
            if self.ips[ip].age() > threshold:
                self.ips.pop(ip)

    def check(self, ip):
        self.cleanup()
        
        if not ip in self.ips:
            self.ips[ip] = IP(ip)

        self.ips[ip].update()
        tries = self.ips[ip].tries()
        wait = math.exp(tries-5)
        if wait < 1:
            return True
        return False
        
        #else:
            #if wait > 60:
            #    wait = 60
            #time.sleep(wait)
        #    return False   
        #return True

