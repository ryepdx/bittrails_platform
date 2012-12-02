from db import get_connection

class Model(dict):
    @classmethod
    def get_collection(cls):
        conn = get_connection()
        return conn[cls.table]

    def __getattr__(self, attr):
        return self[attr]
        
    def __setattr__(self, attr, value):
        self[attr] = value
