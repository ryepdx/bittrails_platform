import string
import json
import logging
from db.models import Model, mongodb_init
from oauth_provider.models import User
from ..models import LastPostRetrieved
from handlers import (TwitterTweet, LastfmScrobble,
    GoogleCompletedTask, LastfmScrobbleEchonest)
from iterators import TwitterPosts, LastfmScrobbles, GoogleCompletedTasks
from auth import APIS

class Tasks(object):
    handler_classes = []
    
    def __init__(self, user, uid, api = None, logger = None):  
        self.user = user
        self.uid = uid
        self.api = api if api else APIS[self.datastream_name]
        self.logger = logger if logger else logging.getLogger(__name__)
        self.handlers = [handler_class(self.user, self.datastream_name + '/'
            ) for handler_class in self.handler_classes]
    
    def run(self):
        last_post = LastPostRetrieved.find_or_create(
            uid = self.uid, datastream = self.datastream_name)
        
        kwargs = {'api': self.api}
        if last_post.post_id:
            kwargs['latest_position'] = last_post.post_id
            
        # Query our datastream for objects of interest.
        posts = self.iterator_class(self.user, self.uid, **kwargs)
        
        try:
            # Process all the returned objects with the task's defined handlers.
            for post in posts:
                for handler in self.handlers:
                    handler.handle(post)
                last_post.post_id = posts.latest_position
                
        except:
            # If there was an exception, log it.
            self.logger.exception(
                "Exception while handling %s tasks for user %s.\n"
                    % (self.datastream_name, self.user['_id']))
            
        finally:
            # No matter what, we want to finalize all of the handlers and then
            # save the last post position successfully processed.
            try:
                for handler in self.handlers:
                    handler.finalize()
                last_post.save()
            
            except:
                # If finalizing the handlers and/or saving last_post failed,
                # we definitely want to log that!
                self.logger.exception(
                    ("Exception while finalizing %s task handlers "
                    + "for user %s. Last post: %s\n") % (self.datastream_name,
                        self.user['_id'], last_post.post_id))
        
    @property
    def iterator_class(self):
        '''
        Should return an iterator that iterates through the results of
        some call to the datastream's API.
        '''
        NotImplemented("Child classes must define this property.")
        
    @property
    def datastream_name(self):
        '''
        Should return the key for the API object in the auth.APIS dictionary
        that the iterator will use to grab its data.
        '''
        NotImplemented("Child classes must define this property.")
        
        
class TwitterTasks(Tasks):
    datastream_name = 'twitter'
    handler_classes = [TwitterTweet]
    iterator_class = TwitterPosts

class LastfmTasks(Tasks):
    datastream_name = 'lastfm'
    handler_classes = [LastfmScrobble, LastfmScrobbleEchonest]
    iterator_class = LastfmScrobbles

class GoogleTasks(Tasks):
    datastream_name = 'google'
    handler_classes = [GoogleCompletedTask]
    iterator_class = GoogleCompletedTasks
