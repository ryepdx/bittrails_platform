import unittest
import datetime
from auth.mocks import APIS
from bson import ObjectId
from async_tasks.posts import TwitterPosts
from async_tasks.posts_count import TwitterPostCounter
from oauth_provider.models import User

class TestPosts(object):
    def test_more_than_zero(self):
        self.should_have_more_than_zero_posts(
            self.when_counted(
                self.given_posts()
            )
        )
        
    def test_no_duplicate_ids(self):
        self.should_have_no_duplicate_ids(
            self.given_posts()
        )
    
    def should_have_more_than_zero_posts(self, num):
        self.assertTrue(num > 0)    
    
    def when_counted(self, posts):
        return sum(1 for _ in posts)


class TestTwitterPosts(TestPosts, unittest.TestCase):
    def setUp(self):
        self.user = User(
            _id = ObjectId('50e3da15ab0ddcff7dd3c187'),
            external_tokens = { 
                "twitter" : [ 
                    "14847576-NtVpk6iONznNMC7AQmYuI138nf9bualJZG0Jpd5Q0", 
                    "JbmAHGyE2n485Yp7hs6dpTT8eFSn5AFAiiwJ52OHetw"
                ]
            }
        )
        self.username = 'ryepdx'
        
    def given_posts(self):
        return TwitterPosts(self.user, self.username, api = APIS['twitter'])


    def should_have_no_duplicate_ids(self, posts):
        ids = set()
        for post in posts:
            self.assertNotIn(post['id_str'], ids)
            ids.add(post['id_str'])
                
class TestTwitterPostCounter(unittest.TestCase):
    def setUp(self):
        self.user = User.find_one(ObjectId("50e3da15ab0ddcff7dd3c187"), as_obj = True)
        self.username = 'ryepdx'
        self.counter = TwitterPostCounter()
        
    def given_posts(self):
        return TwitterPosts(self.user, self.username, api = APIS['twitter'])
        
    def when_all_are_counted(self, posts):
        for post in posts:
            self.counter.handle(self.user, post)
        return self.counter.counts
        
    def should_have_correct_counts(self, counts):
        self.assertEqual(
            counts['day:2012-11-10 00:00:00'],
            {
                'interval_start': datetime.datetime(2012, 11, 10, 0, 0),
                'datastream': 'twitter',
                'interval': 'day',
                'user_id': self.user._id,
                'posts_count': 15
            })

        self.assertEqual(
            counts['week:2012-10-29 00:00:00'],
            {
                'interval_start': datetime.datetime(2012, 10, 29, 0, 0),
                'datastream': 'twitter',
                'interval': 'week',
                'user_id': self.user._id,
                'posts_count': 42
            })
            
        self.assertEqual(
            counts['month:2009-03-01 00:00:00'],
            {
                'interval_start': datetime.datetime(2009, 3, 1, 0, 0),
                'datastream': 'twitter',
                'interval': 'month',
                'user_id': self.user._id,
                'posts_count': 9
            })
            
    def test_counts(self):
        self.should_have_correct_counts(
            self.when_all_are_counted(
                self.given_posts()
            )
        )
