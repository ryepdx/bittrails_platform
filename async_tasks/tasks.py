import string
import json
from db.models import Model, mongodb_init
from oauth_provider.models import User
from models import PostsCount, LastPostRetrieved
from posts_count import TwitterPostCounter
from posts import TwitterPosts
from auth import APIS

class Tasks(object):
    def __init__(self, user, uid, api = None):  
        self.user = user
        self.uid = uid       
        self.api = api if api else APIS[self.datastream_name]
    
    def run(self):
        last_post = LastPostRetrieved.find_or_create(
            uid = self.uid, datastream = self.datastream_name)
        last_post_id = last_post.post_id if last_post.post_id else 1
        posts = self.iterator_class(self.user, self.uid,
            latest_id = last_post_id, api = self.api)
            
        for post in posts:
            for handler in self.handlers:
                handler.handle(self.user, post)
            
        for handler in self.handlers:
            handler.finalize()
            
        last_post.post_id = posts.latest_id
        last_post.save()
        
    @property
    def datastream_name(self):
        NotImplemented("Child classes must define this property.")
        
        
class TwitterTasks(Tasks):
    def __init__(self, *args, **kwargs):
        super(TwitterTasks, self).__init__(*args, **kwargs)
        self.handlers = [
            TwitterPostCounter()
        ]
    
    @property
    def iterator_class(self):
        return TwitterPosts
        
    @property
    def datastream_name(self):
        return 'twitter'
