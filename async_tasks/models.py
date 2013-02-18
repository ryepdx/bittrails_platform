import datetime
import string
import json
from decimal import Decimal
from db.models import Model, mongodb_init
from oauthlib.common import add_params_to_uri

class AsyncModel(Model):    
    @classmethod
    def get_collection(cls, database = "async_tasks"):
        return super(AsyncModel, cls).get_collection(database = database)
        
        
class LastPostRetrieved(AsyncModel):
    '''
    Saves state for the iterators.
    '''
    table = 'last_post_retrieved'
    do_not_convert = ('post_id',)
    
    @mongodb_init
    def __init__(self, uid = '', datastream = '', post_id = ''):
        self.uid = uid
        self.datastream = datastream
        self.post_id = post_id


class TimeSeriesPath(AsyncModel):
    table = "timeseries"
    
    @mongodb_init
    def __init__(self, user_id = '', parent_path = '', name = ''):
        # They're keyword arguments, sure, but they're not optional.
        assert user_id
        assert name
        
        self.user_id = user_id
        self.name = name
        self.parent_path = parent_path
        
    @property
    def path(self):
        return self.parent_path + self.name
        
    @property
    def children(self):
        return self.get_collection().find({parent_path: self.path})
        
    def save(self, *args, **kwargs):
        # No, really. it's not optional.
        assert 'user_id' in self and self['user_id']
        return super(TimeSeriesPath, self).save(*args, **kwargs)

   
class TimeSeriesData(TimeSeriesPath):
    dimensions = ['year', 'month', 'week', 'day', 'day_of_week', 'hour']
    
    @classmethod
    def find_one(cls, attrs, **kwargs):
        if 'timestamp' in attrs:
            attrs['timestamp'] = cls.simplify_timestamp(attrs['timestamp'])
            
        return super(TimeSeriesData, cls).find_one(attrs, **kwargs)
    
    @classmethod
    def simplify_timestamp(cls, timestamp):
        # For now we are roughing up the timestamp's granularity to match the
        # granularity of what we record. Otherwise we end up with more database
        # entries than necessary.
        return timestamp.replace(minute=0, second=0, microsecond=0)
    
    @mongodb_init
    def __init__(self, total = 0, timestamp = None, name = 'total.json', **kwargs):
        super(TimeSeriesData, self).__init__(name = name, **kwargs)
        self.timestamp = self.simplify_timestamp(timestamp)
        self.year = timestamp.year
        self.month = timestamp.month
        self.week = timestamp.isocalendar()[1]
        self.day = timestamp.day
        self.day_of_week = timestamp.isoweekday()
        self.hour = timestamp.hour
        self.total = total
    
    @property
    def path(self):
        return self.parent_path + 'total.json'
        
    @property
    def children(self):
        return None
        
        
class Correlation(AsyncModel):
    '''
    Keeps track of what correlations we've found.
    '''
    table = "correlation"
    
    @mongodb_init
    def __init__(self, user_id = '', dimension = '', start = '',
    end = '', correlation = 0, threshold = '', paths = {}, key = ''):
        self.user_id = user_id
        self.dimension = dimension
        self.start = start
        self.end = end
        self.correlation = correlation
        self.threshold = threshold
        self.paths = paths
        self.lookup_key = lookup_key # For easy retrieval based on query params.
