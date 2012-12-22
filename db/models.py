from db import get_connection
from settings import DATABASE
from bson.objectid import ObjectId
from functools import wraps

def mongodb_init(f):
    @wraps(f)
    def init(self, *args, **kwargs):
        if '_id' in kwargs:
            _id = kwargs.pop('_id')
            self._id = _id
            
        f(self, *args, **kwargs)
        self.convert_ids()
        
    return init

class Model(dict):
    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(self, *args, **kwargs)
        self.convert_ids()
    
    @classmethod
    def get_collection(cls):
        conn = get_connection(DATABASE)
        return conn[cls.table]
        
    @classmethod
    def find_one(cls, attrs):
        return cls.get_collection().find_one(attrs)
    
    @classmethod
    def insert(cls, obj):
        if hasattr(obj, 'convert_ids'):
            obj.convert_ids()
        return cls.get_collection().insert(obj)
        
    @classmethod
    def save(cls, obj):
        if hasattr(obj, 'convert_ids'):
            obj.convert_ids()
        return cls.get_collection().save(obj)

    def convert_ids(self):
        for key in filter(lambda x: x[-3:] == '_id', self.keys()):
            if not isinstance(self[key], ObjectId) and self[key]:
                self[key] = ObjectId(self[key])

    def __getattr__(self, attr):
        return self[attr]
        
    def __setattr__(self, attr, value):
        self[attr] = value
    
    
