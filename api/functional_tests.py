import time
import flask_rauth
import unittest
import settings_test as settings
import bson
import json

# Values below taken from the Dashboard and Platform data fixtures.
CLIENT_KEY = "dAcFo8K6ArRC6zb3fZepVUvhGSU433"
CLIENT_SECRET = "Ka0dSMaJwy2xGuxcw13nCk5c9VnVUR"
OAUTH_TOKEN = [
    "UpRbR8LrIyrDwn4a9nZLxPMlDGVj1P",
    "uT5ZtYQv5uPYrjiJkFQV5wQj3AJJ0f"
]

TEST_CSV_URL = "http://ryepdx.com/test.csv"
TEST_CVS_JSON = [
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 1, u'value': 90, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 11}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 2, u'value': 95, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 12}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 3, u'value': 89, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 13}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 4, u'value': 70, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 14}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 5, u'value': 80, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 15}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 6, u'value': 92, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 16}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 7, u'value': 99, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 17}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 1, u'value': 78, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 18}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 2, u'value': 94, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 19}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 3, u'value': 98, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 20}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 4, u'value': 92, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 21}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 5, u'value': 93, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 22}
]
TEST2_CSV_URL = "http://ryepdx.com/test2.csv"
TEST2_CVS_JSON = [
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 1, u'value': 90, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 11}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 2, u'value': 95, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 12}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 3, u'value': 89, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 13}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 4, u'value': 70, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 14}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 5, u'value': 80, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 15}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 6, u'value': 92, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 16}, 
    {u'week': 10, u'isoyear': 2013, u'hour': 0, u'isoweekday': 7, u'value': 99, 
     u'month': 3, u'year': 2013, u'isoweek': 11, u'day': 17}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 1, u'value': 78, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 18}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 2, u'value': 94, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 19}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 3, u'value': 98, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 20}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 4, u'value': 92, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 21}, 
    {u'week': 11, u'isoyear': 2013, u'hour': 0, u'isoweekday': 5, u'value': 93, 
     u'month': 3, u'year': 2013, u'isoweek': 12, u'day': 22}
]

EXPECTED_CORRELATION = [
    {"correlation": 1.0, 
     "paths": ["test/totals", "test2/totals"],
     "group_by": ["year", "month", "day"],
     "end": [2013, 3, 22],
     "start": [2013, 3, 13]
    }
]


class V1EndpointTestCase(unittest.TestCase):
    api_test = True
    
    def setUp(self):
        self.api = flask_rauth.RauthOAuth1(
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

    def create_custom_datastream(self, name, url, oauth_token = OAUTH_TOKEN):
        return self.api.post('root.json', data = {
            'url': url, 'path': '/%s' % name,'title': name.title()
            }, oauth_token = oauth_token)
    
    def get_custom_datastream(self, name):
        tries = 0
        success = False
        
        while tries < 10 and not success:
            result = self.api.get(name + '.json', oauth_token = OAUTH_TOKEN)
            tries += 1
            success = (result.status == 200)
            
            if not success:
                time.sleep(1)
                
        return result
    
    def testRoot(self):
        # Should get 403.
        assert self.api.get("root.json").status == 403
        
        # But this should succeed.
        assert self.api.get(
            "root.json", oauth_token = OAUTH_TOKEN).status == 200
            
    def testCustomDatastream(self):
        
        # Test endpoint protection first.
        assert self.create_custom_datastream('test', TEST_CSV_URL,
            oauth_token = None).status == 403
            
        # Make sure that we can't get to the endpoint before we've created it.
        assert self.api.get('test.json', oauth_token=OAUTH_TOKEN).status == 404
        
        # Now test a valid, authenticated request.
        assert self.create_custom_datastream('test', TEST_CSV_URL
            ).status == 200

        # Alright, now let's try to get our datastream back.
        # Since pulling in data is supposed to be handled asynchronously,
        # we're going to try a few times with pauses in between before we
        # declare failure.
        if not self.get_custom_datastream('test').status == 200:
            raise Exception("Could not get back our custom datastream.")

        # Let's check the contents of test/totals.json
        totals = self.get_custom_datastream('test/totals').content['data']
        assert totals == TEST_CVS_JSON, totals
        
        # Alright, we need to add another custom datastream.
        # Now test a valid, authenticated request.
        assert self.create_custom_datastream('test2', TEST2_CSV_URL
            ).status == 200
            
        if not self.get_custom_datastream('test2').status == 200:
            raise Exception("Could not get back our custom datastream.")
            
        totals = self.get_custom_datastream('test2/totals').content['data']
        assert totals == TEST2_CVS_JSON, totals
        
        # And finally, let's test the correlations calculator.
        correlation = self.api.get(
            'correlations.json?paths=["test/totals","test2/totals"]&groupBy=["year","month","day"]&thresholds=[">0.5","<-0.5"]',
            oauth_token = OAUTH_TOKEN)
        assert (json.loads(correlation.content) == EXPECTED_CORRELATION
            ), correlation.content
