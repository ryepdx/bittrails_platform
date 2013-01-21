# Mock classes to facilitate testing.
from twitter_mock_responses import TWITTER_MOCK_RESPONSES
from lastfm_mock_responses import LASTFM_MOCK_RESPONSES

class MockResponse(object):
    def __init__(self, content):
        self.content = content

class MockAPI(object):
    def get(self, uri, user = None):
        if uri in self.uris:
            return MockResponse(self.uris[uri])
        else:
            raise Exception(
                "%s does not recognize this URI: %s"
                % (self.__class__.__name__, uri))


class MockTwitterAPI(MockAPI):
    @property
    def uris(self):
        return TWITTER_MOCK_RESPONSES
        

class MockLastFmAPI(MockAPI):
    @property
    def uris(self):
        return LASTFM_MOCK_RESPONSES

APIS = {'twitter': MockTwitterAPI(), 'lastfm': MockLastFmAPI()}
