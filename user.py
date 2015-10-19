# -*- coding: utf-8 -*-

import hashlib
from flask.ext.login import UserMixin

class User(UserMixin):
    """User-profile-data storage"""
    user_database = {}

    def __init__(self, username, password):
        self.id = username
        self.password = password

    @classmethod
    def get(cls,id):
        return cls.user_database.get(id)

    @classmethod
    def get_password_hash(cls, password):
        if password is None:
            return None
        data = "pyWebIRC-salt-" + password
        h = hashlib.new("sha512")
        h.update(data)
        return h.hexdigest()

    def __repr__(self):
        return "<UserData login:'{}'>".format(self.id)

if __name__ == "__main__":
    import sys 

    print "You may start me to generate a password-hash, use one argument!"
    print "Usage: python(2) user.py my_secure_password"
    print "Returns the password-hash for the provided password"
    print 
    print "---------------------------------------------"
    print User.get_password_hash(sys.argv[1])    
    print "---------------------------------------------"

