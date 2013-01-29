import inspect
import .tasks
from pyechonest import config
from bson import ObjectId
from tasks import TwitterTasks, LastfmTasks, GoogleTasks
from oauth_provider.models import User, UID
from async_tasks.models import LastPostRetrieved
from celery import Celery
from settings import ECHO_NEST_KEY

def run_tasks(APIS):
    config.ECHO_NEST_API_KEY = ECHO_NEST_KEY
    
    celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')

    task_classes = inspect.getmembers(tasks, inspect.isclass)
    users = User.get_collection().find()
    
    for user in users:
        uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
        posts = LastPostRetrieved.get_collection().find({
            '$or': [{'datastream': row['datastream'],
                     'uid': row['uid']} for row in uids]
        })
        
        for task_class in task_classes:
            task = task_class(user, [post['datastream'] for post in posts])
            task.run()
