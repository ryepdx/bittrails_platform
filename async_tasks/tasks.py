import string
import json
import sys
from db.models import Model, mongodb_init
from oauth_provider.models import User
from models import Count, LastPostRetrieved
from posts_count import (TwitterPostCounter, LastfmScrobbleCounter,
    GoogleCompletedTasksCounter, LastfmSongEnergyAverager)
from posts import TwitterPosts, LastfmScrobbles, GoogleCompletedTasks
from auth import APIS

class Tasks(object):
    def __init__(self, user, uid, api = None):  
        self.user = user
        self.uid = uid
        self.api = api if api else APIS[self.datastream_name]
    
    def run(self, logger = None):
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
            err_msg = ("Exception while handling %s tasks for user %s.\n"
                    % (self.datastream_name, self.user['_id']))
            if logger:
                logger.error(err_msg, exc_info = err)
            else:
                # No logger? We don't want to fail silently!
                sys.stderr.write(err_msg)
                raise
        finally:
            # No matter what, we want to finalize all of the handlers and then
            # save the last post position successfully processed.
            try:
                for handler in self.handlers:
                    handler.finalize()
                last_post.save()
            
            except:
                err_msg = ("Exception while finalizing %s task handlers "
                    + "for user %s. Last post: %s\n" % (self.datastream_name,
                        self.user['_id'], last_post.post_id))
                # If finalizing the handlers and/or saving last_post failed,
                # we definitely want to log that!
                if logger:
                    logger.error(err_msg, exc_info = err)
                else:
                    # No logger? Well, we don't want to fail silently!
                    sys.stderr.write(err_msg)
                    raise
            
        
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
    def __init__(self, *args, **kwargs):
        super(TwitterTasks, self).__init__(*args, **kwargs)
        self.handlers = [
            TwitterPostCounter(self.user)
        ]
    
    @property
    def iterator_class(self):
        return TwitterPosts
        
    @property
    def datastream_name(self):
        return 'twitter'


class LastfmTasks(Tasks):
    def __init__(self, *args, **kwargs):
        super(LastfmTasks, self).__init__(*args, **kwargs)
        self.handlers = [
            LastfmScrobbleCounter(self.user),
            #LastfmArtistMoodRanker(self.user),
            LastfmSongEnergyAverager(self.user)
        ]
    
    @property
    def iterator_class(self):
        return LastfmScrobbles
        
    @property
    def datastream_name(self):
        return 'lastfm'


class GoogleTasks(Tasks):
    def __init__(self, *args, **kwargs):
        super(GoogleTasks, self).__init__(*args, **kwargs)
        self.handlers = [
            GoogleCompletedTasksCounter(self.user)
        ]
    
    @property
    def iterator_class(self):
        return GoogleCompletedTasks
        
    @property
    def datastream_name(self):
        return 'google_tasks'
