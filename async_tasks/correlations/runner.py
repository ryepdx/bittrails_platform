import inspect
import tasks
from bson import ObjectId
from tasks import CorrelationTask
from oauth_provider.models import User, UID
from async_tasks.models import LastPostRetrieved
from celery import Celery

def run_tasks():
    celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')
    
    users = User.get_collection().find()
    
    for user in users:
        uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
        
        if uids.count() > 0:
            posts = LastPostRetrieved.get_collection().find({
                '$or': [{'datastream': row['datastream'],
                         'uid': row['uid']} for row in uids]
            })
            available_datastreams = [post['datastream'] for post in posts]
            # Cycle through every class that inherits from CorrelationTask
            # in tasks.py, instantiate it, and run it.
            for task_class in CorrelationTask.__subclasses__():
                task = task_class(user, available_datastreams)
                task.run()
