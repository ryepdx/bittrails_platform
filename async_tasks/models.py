import datetime
import string
import json
from correlations.settings import MINIMUM_DATAPOINTS_FOR_CORRELATION
from decimal import Decimal
from db.models import Model, mongodb_init
from oauthlib.common import add_params_to_uri

class AsyncModel(Model):
    @classmethod
    def get_collection(cls, database = "async_tasks"):
        return super(AsyncModel, cls).get_collection(database = database)
        
    @classmethod
    def get_data(cls, entry):
        raise NotImplemented("Inheriting classes must implement this.")
        
class LastPostRetrieved(AsyncModel):
    table = 'last_post_retrieved'
    do_not_convert = ('post_id',)
    
    @mongodb_init
    def __init__(self, uid = '', datastream = '', post_id = ''):
        self.uid = uid
        self.datastream = datastream
        self.post_id = post_id


class TimeSeriesModel(AsyncModel):
    table = None
    
    interval_funcs = {
            'day': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, date_obj.day),
            'week': lambda date_obj: datetime.datetime.strptime(
                date_obj.strftime('%Y %U 1'), '%Y %U %w'),
            'month': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, 1),
            'year': lambda date_obj: datetime.datetime(date_obj.year, 1, 1)
        }
        
    @classmethod
    def get_year_start(cls, date_obj):
        return cls.get_start_of('year', date_obj)

    @classmethod
    def get_month_start(cls, date_obj):
        return cls.get_start_of('month', date_obj)

    @classmethod
    def get_week_start(cls, date_obj):
        return cls.get_start_of('week', date_obj)

    @classmethod
    def get_day_start(cls, date_obj):
        return cls.get_start_of('day', date_obj)

    @classmethod
    def get_start_of(cls, interval, date_obj):
        return cls.interval_funcs[interval](date_obj)
        
    @mongodb_init
    def __init__(self, user_id = '', interval = '', interval_start = None,
    datastream = '', aspect = ''):
        # It's a keyword argument, sure, but it's not optional.
        assert user_id
        
        self.user_id = user_id
        self.interval = interval
        self.interval_start = interval_start
        self.datastream = datastream
        self.aspect = aspect
    
    def save(self, *args, **kwargs):
        # No, really. It's not optional.
        assert 'user_id' in self and self['user_id']
        return super(TimeSeriesModel, self).save(*args, **kwargs)
        

class Count(TimeSeriesModel):
    table = 'count'
    
    def __init__(self, count = 0, **kwargs):
        self.count = count
        super(Count, self).__init__(**kwargs)
        
    @classmethod
    def get_data(cls, entry):
        return int(entry['count'])


class Average(TimeSeriesModel):
    table = 'average'
    
    def __init__(self, numerator = 0, denominator = 0, **kwargs):
        self.numerator = numerator
        self.denominator = denominator
        super(Average, self).__init__(**kwargs)
        
    def __str__(self):
        return self.numerator / self.denominator
        
    @classmethod
    def get_data(cls, entry):
        if entry['denominator'] == 0:
            return 0
        return float(Decimal(entry['numerator']) / Decimal(entry['denominator']))

class Correlation(Model):
    table = "correlation"
    
    @mongodb_init
    def __init__(self, user_id = '', interval = '', interval_start = '',
    interval_end = '', correlation = 0, key = '',
    window_size = MINIMUM_DATAPOINTS_FOR_CORRELATION):
        self.user_id = user_id
        self.interval = interval
        self.interval_start = interval_start
        self.interval_end = interval_end
        self.correlation = correlation
        self.window_size = window_size
        self.key = key
        
    @classmethod
    def generate_key(cls, aspects):
        '''
        Takes a dictionary of lists of aspect names with service names as the
        keys. Returns a key for looking up a correlation.
        '''
        key = []
        for datastream in aspects:
            for aspect in aspects[datastream]:
                key.append(datastream + ':' + aspect)
                
        return ','.join(key)
