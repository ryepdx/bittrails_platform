from json import JSONEncoder

class CorrelationJSONEncoder(JSONEncoder):
    json_fields = ["start", "end", "correlation"]
    
    def default(self, obj):
        if isinstance(obj, list):
            return [self.default(o) for o in obj]
        elif isinstance(obj, dict):
            return {field: objs[field] for field in self.json_fields}
        else:
            return super(CorrelationJSONEncoder, self).default(obj)
