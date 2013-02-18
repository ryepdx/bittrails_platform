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
    continuous = True
    #dimensions = ['interval', 'start']
    #dimensions = ['interval']
    dimensions = []
    extra_dimensions = {}
    extra_grouping = {}
    
    interval_funcs = {
            'day': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, date_obj.day,
                tzinfo = date_obj.tzinfo),
            'week': lambda date_obj: datetime.datetime.strptime(
                date_obj.strftime('%Y %U 1'), '%Y %U %w').replace(
                tzinfo = date_obj.tzinfo),
            'month': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, 1, tzinfo = date_obj.tzinfo),
            'year': lambda date_obj: datetime.datetime(
                date_obj.year, 1, 1,  tzinfo = date_obj.tzinfo)
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
        
    @classmethod
    def get_data(cls, entry):
        return dict([(dimension, entry[dimension]
            ) for dimension in cls.dimensions if dimension in entry])
                
    @classmethod
    def get_empty_data(cls, dimensions):
        return dict([(dimension, 0) for dimension in dimensions])
        
    @mongodb_init
    def __init__(self, user_id = '', interval = '', start = None,
    datastream = '', aspect = ''):
        # It's a keyword argument, sure, but it's not optional.
        assert user_id
        
        self.user_id = user_id
        self.interval = interval
        self.start = start
        self.datastream = datastream
        self.aspect = aspect
    
    def save(self, *args, **kwargs):
        # No, really. It's not optional.
        assert 'user_id' in self and self['user_id']
        return super(TimeSeriesModel, self).save(*args, **kwargs)
        

class Count(TimeSeriesModel):
    table = 'count'
    dimensions = TimeSeriesModel.dimensions + ['count']
    
    def __init__(self, count = 0, **kwargs):
        self.count = count
        super(Count, self).__init__(**kwargs)

class HourCount(Count):
    table = 'hour_count'
    dimensions = Count.dimensions + ['hour']
    
    def __init__(self, hour = None, **kwargs):
        self.hour = hour
        super(HourCount, self).__init__(**kwargs)

class Average(TimeSeriesModel):
    table = 'average'
    dimensions = TimeSeriesModel.dimensions + ['average']
    extra_grouping = {'num_sum':{'$sum':'$numerator'},
        'den_sum':{'$sum':'$denominator'}}
    extra_dimensions = {'average': {'$divide':['$num_sum', '$den_sum']}}
    
    def __init__(self, numerator = 0, denominator = 0, **kwargs):
        self.numerator = numerator
        self.denominator = denominator
        super(Average, self).__init__(**kwargs)
        
    def __str__(self):
        return self.numerator / self.denominator

class Correlation(AsyncModel):
    '''
    Keeps track of what correlations we've found.
    '''
    table = "correlation"
    
    @mongodb_init
    def __init__(self, user_id = '', interval = '', start = '',
    end = '', correlation = 0, threshold = '', aspects = {}, key = ''):
        self.user_id = user_id
        self.interval = interval
        self.start = start
        self.end = end
        self.correlation = correlation
        self.threshold = threshold
        self.aspects = aspects
        self.key = key
