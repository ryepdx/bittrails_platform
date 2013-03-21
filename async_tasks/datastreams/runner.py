from pyechonest import config
from bson import ObjectId
from tasks import TwitterTasks, LastfmTasks, GoogleTasks, CSVDatastreamTasks
from oauth_provider.models import User, UID
from celery import Celery
from settings import ECHO_NEST_KEY
from async_tasks.models import CustomTimeSeriesPath

def run_tasks(APIS):
    config.ECHO_NEST_API_KEY = ECHO_NEST_KEY
    
    csvDatastreamTasks = CSVDatastreamTasks()
    celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')
    tasks = { 'twitter': TwitterTasks, 'lastfm': LastfmTasks, 'google': GoogleTasks }
    users = User.get_collection().find()
        
    for user in users:
        uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
        
        for uid in uids:
            if uid['datastream'] in tasks:
                task = tasks[uid['datastream']](
                    user, uid['uid'], api = APIS[uid['datastream']])
                task.run()
                
        # Custom datastreams
        custom_streams = CustomTimeSeriesPath.find(
            {'url': {'$exists': True}, 'user_id': ObjectId(user['_id'])})
        
        for stream in custom_streams:
            csvDatastreamTasks.run(stream)
            
