import json
import bson
import datetime

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, bson.ObjectId):
            return str(obj)
            
        return super(JSONEncoder, self).default(obj)
