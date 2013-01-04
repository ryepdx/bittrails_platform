import unittest
import views_funcs
from bson import ObjectId
from oauth_provider.models import User

class PostsCountTestCase(unittest.TestCase):    
    def setUp(self):
        self.user = User(_id = ObjectId("50e209f8fb5d1b6d96ad37b7"))
        
    def test_post_count(self):
        counts = views_funcs.get_posts_count_func(
            self.user, 'twitter', 'by/week')
        self.assertTrue(len(counts) > 0)
