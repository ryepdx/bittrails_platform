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
    def get_collection(cls, database = DATABASE):
        conn = get_connection(database)
        return conn[cls.table]
        
    @classmethod
    def find(cls, *args, **kwargs):
        return cls.get_collection().find(*args, **kwargs)
        
    @classmethod
    def find_one(cls, attrs, as_obj = False):
        if as_obj:
            result = cls.get_collection().find_one(attrs)
            
            if result:
                return cls(**result)
            else:
                return result
        else:
            return cls.get_collection().find_one(attrs)
            
    @classmethod
    def find_or_create(cls, **kwargs):
        result = cls.find_one(kwargs, as_obj = True)
        
        if result:
            return result
        else:
            return cls(**kwargs)
    
    def insert(self):
        if hasattr(self, 'convert_ids'):
            self.convert_ids()
        self._id = self.get_collection().insert(self)
        return self._id
        
    def save(self):
        if hasattr(self, 'convert_ids'):
            self.convert_ids()
        self._id = self.get_collection().save(self)
        return self._id

    def convert_ids(self):
        if hasattr(self, 'do_not_convert'):
            skip_keys = self.do_not_convert
        else:
            skip_keys = []
            
        for key in filter(
        lambda x: x[-3:] == '_id' and x not in skip_keys, self.keys()):
            if not isinstance(self[key], ObjectId) and self[key]:
                self[key] = ObjectId(self[key])

    def __getattr__(self, attr):
        return self[attr]
        
    def __setattr__(self, attr, value):
        self[attr] = value
    
    
