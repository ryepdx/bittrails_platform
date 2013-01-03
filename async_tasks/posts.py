from oauthlib.common import add_params_to_uri
from auth import APIS

class TwitterPosts(object):
    
    def __init__(self, user, uid, latest_id = 1, api = APIS['twitter']):
        self.uid = uid
        self.user = user
        self.latest_id = latest_id
        self.tweets = []
        self.max_index = 0
        self.index = 0
        self.api = api
        
    def __iter__(self):
        return self
        
    def next(self):
        if not self.tweets or self.index > self.max_index:
            self.index = 0
            self.tweets = self.get_tweets()
        
            if self.tweets:
                self.max_index = len(self.tweets) - 1
                
                if int(self.tweets[0]['id_str']) > int(self.latest_id):
                    self.latest_id = self.tweets[0]['id_str']
            else:
                raise StopIteration      

        tweet = self.tweets[self.index]
        self.index += 1
        return tweet
        
    def get_tweets(self):
        all_tweets = []
        request_uri = 'statuses/user_timeline.json'
        params = {'screen_name': self.uid, 'count': '200'}
        
        if self.latest_id:
            params['since_id'] = self.latest_id
        
        i = 0
        keep_requesting = True
        
        while keep_requesting:
            tweets = self.api.get(
                add_params_to_uri(request_uri, params.items()),
                user = self.user)
            if tweets.content and not 'errors' in tweets.content:
                params['max_id'] = int(tweets.content[-1]['id_str']) - 1
                all_tweets.extend(tweets.content)
                
                i += 1
                keep_requesting = i < 15
            else:
                keep_requesting = False
                
        return all_tweets
