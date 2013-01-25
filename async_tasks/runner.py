from pyechonest import config
from bson import ObjectId
from tasks import TwitterTasks, LastfmTasks, GoogleTasks
from oauth_provider.models import User, UID
from celery import Celery
from settings import ECHO_NEST_KEY

def run_tasks(APIS):
    config.ECHO_NEST_API_KEY = ECHO_NEST_KEY
    
    celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')

    #tasks = { 'twitter': TwitterTasks, 'lastfm': LastfmTasks, 'google_tasks': GoogleTasks }
    tasks = { 'lastfm': LastfmTasks }
    users = User.get_collection().find()
        
    for user in users:
        uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
        
        for uid in uids:
            if uid['datastream'] in tasks:
                task = tasks[uid['datastream']](
                    user, uid['uid'], api = APIS[uid['datastream']])
                task.run()
