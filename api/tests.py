import unittest
import views_funcs
import datetime
import correlations.mocks

from async_tasks.datastreams.handlers import TwitterTweet
from bson import ObjectId
from correlations.constants import MINIMUM_DATAPOINTS_FOR_CORRELATION
from api.constants import INTERVALS
from oauth_provider.models import User

class PostsCountTestCase(unittest.TestCase):    
    def setUp(self):
        self.user = User(_id = ObjectId("50e209f8fb5d1b6d96ad37b7"))
        
    def test_post_count(self):
        counts = views_funcs.get_service_data_func(
            self.user, 'twitter', TwitterTweet.aspect, 'Count', 'by/week')
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


class GetCorrelationsTestCase(unittest.TestCase):
    def setUp(self):
        self.user = User(_id = ObjectId("50e209f8fb5d1b6d96ad37b7"))
        self.Mockmodel_aspects = {'mockDatastream': 
            ['song_mockmodel', 'task_mockmodel']}
        self.Mockmodel2_aspects = {'mockDatastream':
            ['song_mockmodel2', 'task_mockmodel2']}
        self.window_size = 3
            
    def test_correlations_view_func(self):
        self.should_have_a_correlation_of_one(
            self.given_correlations_on_Mockmodel())
            
        self.should_have_a_correlation_of_one(
            self.given_correlations_on_Mockmodel2())
    
    def given_correlations_on_Mockmodel(self):
        return views_funcs.get_correlations(
            self.user, self.Mockmodel_aspects, None, None,
            self.window_size, ['> 0.5', '< -0.5'],
            INTERVALS, model_module = correlations.mocks, use_cache = False)
            
    def given_correlations_on_Mockmodel2(self):
        return views_funcs.get_correlations(
            self.user, self.Mockmodel2_aspects, None, None,
            self.window_size, ['> 0.5', '< -0.5'],
            INTERVALS, model_module = correlations.mocks, use_cache = False)

    def should_have_a_correlation_of_one(self, correlations):
        self.assertEqual(len(correlations), len(INTERVALS))
        for interval, correlation in correlations.items():
            self.assertEqual(correlation[0]['correlation'], 1)
