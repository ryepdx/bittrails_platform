import unittest
import oauth_provider

class ProviderTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = oauth_provider.app.test_client()

    def tearDown(self):
        pass
