from db import get_connection
from settings import DATABASE
    
class Model(dict):
    @classmethod
    def get_collection(cls):
        conn = get_connection(DATABASE)
        return conn[cls.table]

    def __getattr__(self, attr):
        return self[attr]
        
    def __setattr__(self, attr, value):
        self[attr] = value
