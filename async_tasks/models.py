import datetime
import string
import json
from db.models import Model, mongodb_init
from oauthlib.common import add_params_to_uri

class AsyncModel(Model):
    @classmethod
    def get_collection(cls, database = "async_tasks"):
        return super(AsyncModel, cls).get_collection(database = database)
        
class LastPostRetrieved(AsyncModel):
    table = 'last_post_retrieved'
    do_not_convert = ('post_id',)
    
    @mongodb_init
    def __init__(self, uid = '', datastream = '', post_id = ''):
        self.uid = uid
        self.datastream = datastream
        self.post_id = post_id

class PostsCount(AsyncModel):
    table = 'posts_count'
    
    interval_funcs = {
            'day': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, date_obj.day),
            'week': lambda date_obj: datetime.datetime.strptime(
                date_obj.strftime('%Y %U 1'), '%Y %U %w'),
            'month': lambda date_obj: datetime.datetime(
                date_obj.year, date_obj.month, 1),
            'year': lambda date_obj: datetime.datetime(date_obj.year, 1, 1)
        }
    
    @mongodb_init
    def __init__(self, user_id = '', interval = '', interval_start = None,
    datastream = '', posts_count = 0):
        self.user_id = user_id
        self.interval = interval
        self.interval_start = interval_start
        self.datastream = datastream
        self.posts_count = posts_count

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
