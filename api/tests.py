import unittest
import views_funcs
import datetime
from bson import ObjectId
from oauth_provider.models import User

def should_get_a_datetime_of(year, month, day, datetime_obj):
    return (datetime_obj. year == year 
        and datetime_obj.month == month 
        and datetime_obj.day == day)
    
def when_incrementing_by(number, interval, datetime_obj):
    for i in range(0, number):
        datetime_obj = views_funcs.increment_time(datetime_obj, interval)
        
    return datetime_obj

def a_datetime_of(year, month, day):
    return datetime.datetime(year, month, day)


class PostsCountTestCase(unittest.TestCase):    
    def setUp(self):
        self.user = User(_id = ObjectId("50e209f8fb5d1b6d96ad37b7"))
        
    def test_post_count(self):
        counts = views_funcs.get_posts_count_func(
            self.user, 'twitter', 'by/week')
        self.assertTrue(len(counts) > 0)


class IncrementTimeTestCase(unittest.TestCase):
    def test_increment_by_a_week(self):
        self.assertTrue(
            should_get_a_datetime_of(2012, 8, 1,
            when_incrementing_by(1, 'week',
            a_datetime_of(2012, 7, 25)))
        )
