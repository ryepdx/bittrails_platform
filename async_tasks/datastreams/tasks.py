import csv
import urllib2
import string
import json
import logging
import pytz
import datetime
from db.models import Model, mongodb_init
from oauth_provider.models import User
from ..models import LastPostRetrieved, LastCustomDataPull
from handlers import (TwitterTweet, LastfmScrobble,
    GoogleCompletedTask, LastfmScrobbleEchonest, CSVHandler)
from iterators import TwitterPosts, LastfmScrobbles, GoogleCompletedTasks
from auth import APIS

class Tasks(object):
    handler_classes = []
    
    def __init__(self, user, uid, api = None, logger = None):  
        self.user = user
        self.uid = uid
        self.api = api if api else APIS[self.datastream_name]
        self.logger = logger if logger else logging.getLogger(__name__)
        self.handlers = [handler_class(user
            ) for handler_class in self.handler_classes]
    
    def run(self):
        last_post = LastPostRetrieved.find_or_create(
            uid = self.uid, datastream = self.datastream_name)
        
        kwargs = {'api': self.api}
        
        if last_post.post_id:
            kwargs['latest_position'] = last_post.post_id
            
        iterator = self.iterator_class(self.user, self.uid, **kwargs)
            
        # Query our datastream for objects of interest.        
        try:
            # Process all the returned objects with the task's defined handlers.
            for post in iterator:
                for handler in self.handlers:
                    handler.handle(post)
                last_post.post_id = iterator.latest_position
                
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

class CSVDatastreamTasks(object):
    datastream_name = 'custom'

    def __init__(self, logger = None):  
        self.logger = logger if logger else logging.getLogger(__name__)
        
    def run(self, stream):
        handler = CSVHandler(stream)
        
        try:
            # Grab the CSV data and save it in the database.
            csv_file = urllib2.urlopen(stream['url'])
            
            for post in csv.DictReader(
            csv_file, fieldnames = ['date', 'value']):
                handler.handle(post)
                
            csv_file.close()
            
            # Update the "last pulled" timestamp.
            last_pull = LastCustomDataPull.find_or_create(
                path = stream.get('parent_path', '') + stream['name'] + '/',
                user_id = stream['user_id'])
            last_pull.last_pulled = datetime.datetime.now(pytz.utc)
            last_pull.save()
            
        except Exception as e:
            # If there was an exception, log it.
            self.logger.exception(
                "Exception while reading custom datastreams for user %s: %s.\n"
                    % (stream['user_id'], e.message))
