import unittest
import views_funcs
import datetime
from bson import ObjectId
from oauth_provider.models import User

class PostsCountTestCase(unittest.TestCase):    
    def setUp(self):
        self.user = User(_id = ObjectId("50e209f8fb5d1b6d96ad37b7"))
        
    def test_post_count(self):
        counts = views_funcs.get_posts_count_func(
            self.user, 'twitter', 'by/week')
        self.assertTrue(len(counts) > 0)


class IncrementTimeTestCase(unittest.TestCase):
    def test_increment_by_a_week(self):
        self.should_get_a_datetime_of(2012, 8, 1,
        self.when_incrementing_by(1, 'week',
        self.a_datetime_of(2012, 7, 25)))
        
    def should_get_a_datetime_of(self, year, month, day, datetime_obj):
        self.assertEqual(datetime_obj. year, year)
        self.assertEqual(datetime_obj.month, month)
        self.assertEqual(datetime_obj.day, day)
        
    def when_incrementing_by(self, number, interval, datetime_obj):
        for i in range(0, number):
            datetime_obj = views_funcs.increment_time(datetime_obj, interval)
            
        return datetime_obj

    def a_datetime_of(self, year, month, day):
        return datetime.datetime(year, month, day)
