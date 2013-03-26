import rauth
import unittest
import settings_test as settings
import bson

# Values below taken from the Dashboard and Platform data fixtures.
CLIENT_KEY = "dAcFo8K6ArRC6zb3fZepVUvhGSU433"
CLIENT_SECRET = "Ka0dSMaJwy2xGuxcw13nCk5c9VnVUR"
OAUTH_TOKEN = [
    "UpRbR8LrIyrDwn4a9nZLxPMlDGVj1P",
    "uT5ZtYQv5uPYrjiJkFQV5wQj3AJJ0f"
]

class V1EndpointTestCase(unittest.TestCase):
    needs_server = True
    
    def setUp(self):
        self.api = rauth.OAuth1Service(
            name = 'bittrails',
            base_url = 'http://api.%s:%s/v1/' % (settings.HOST, settings.PORT),
            request_token_url = 'http://%s:%s/request_token' % (
                settings.HOST, settings.PORT),
            access_token_url = 'http://%s:%s/access_token' % (
                settings.HOST, settings.PORT),
            authorize_url = 'http://%s:%s/authorize' % (
                settings.HOST, settings.PORT),
            consumer_key = CLIENT_KEY,
            consumer_secret = CLIENT_SECRET
        )

    def testRoot(self):
        # Should get 403.
        self.get("root.json")
