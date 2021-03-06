"""Supporting models for all asynchronous tasks."""
import app as platform
from json import JSONEncoder
from db.models import Model, mongodb_init

if 'DATABASES' in platform.app.config:
    DEFAULT_DATABASE = platform.app.config['DATABASES']['async']
else:
    DEFAULT_DATABASE = 'platform_async'

class AsyncModel(Model):
    @classmethod
    def get_collection(cls, database = DEFAULT_DATABASE):
        return super(AsyncModel, cls).get_collection(database = database)
        
        
class LastCustomDataPull(AsyncModel):
    '''
    Keeps track of when custom datastreams were last checked for updates.
    '''
    table = 'last_post_retrieved'
    
    @mongodb_init
    def __init__(self, user_id = None, path = '', last_pulled = None):
        self.user_id = user_id
        self.path = path
        self.last_pulled = last_pulled
        
        
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
    def __init__(self, user_id = '', parent_path = None, name = '',
    title = None):
        # They're keyword arguments, sure, but they're not optional.
        assert user_id
        assert name
        
        self.user_id = user_id
        self.name = name
        
        if parent_path:
            self.parent_path = parent_path
        
        if title:
            self.title = title
        
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
        
        
class CustomTimeSeriesPath(TimeSeriesPath):
    table = "timeseries"
    
    @mongodb_init
    def __init__(self, url = None, client_id = None, **kwargs):
        # Keyword arguments, but not optional.
        assert client_id
        self.client_id = client_id
        
        if url:
            self.url = url
        
        super(CustomTimeSeriesPath, self).__init__(**kwargs)

   
class TimeSeriesData(TimeSeriesPath):
    dimensions = ['year', 'month', 'week', 'day', 'day_of_week', 'hour', 
        'isoyear', 'isoweek', 'isoweekday', 'value']
    default_group_by = ['year', 'month', 'day']
    
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
    def __init__(self, value = 0, timestamp = None, name = 'totals',
    hour = None, day = None, week = None, month = None, year = None,
    isoyear = None, isoweek = None, isoweekday = None, **kwargs):
        assert timestamp
        
        super(TimeSeriesData, self).__init__(name = name, **kwargs)
        isocalendar = timestamp.isocalendar()
        self.timestamp = self.simplify_timestamp(timestamp)
        self.year = year if year else timestamp.year
        self.month = month if month else timestamp.month
        self.week = week if week else int(timestamp.strftime("%W"))
        self.day = day if day else timestamp.day
        self.isoyear = isoyear if isoyear else isocalendar[0]
        self.isoweek = isoweek if isoweek else isocalendar[1]
        self.isoweekday = isoweekday if isoweekday else isocalendar[2]
        self.hour = hour if hour else timestamp.hour
        self.value = value
    
    @property
    def path(self):
        return self.parent_path + 'totals'
        
    @property
    def children(self):
        return None
        
class CustomTimeSeriesData(TimeSeriesData):
    def __init__(self, client_id, **kwargs):
        self.client_id = client_id
        super(CustomTimeSeriesData, self).__init__(**kwargs)
        
class Correlation(AsyncModel):
    '''
    Keeps track of what correlations we've found.
    '''
    table = "correlation"
    
    @mongodb_init
    def __init__(self, user_id = '', dimension = '', start = '', end = '',
    paths = [], group_by = [], sort = {}, correlation = 0, threshold = '',
    key = ''):
        self.user_id = user_id
        self.start = start
        self.end = end
        self.paths = paths
        self.group_by = group_by
        self.sort = sort
        self.correlation = correlation
        self.threshold = threshold
        self.key = key # For easy retrieval based on query params.

    def json_filter(self):
        return {field: self[field]
            for field in ["paths", "group_by", "start", "end", "correlation"]}
        
