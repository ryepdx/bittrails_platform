from bson import ObjectId
from tasks import TwitterTasks, LastfmTasks
from oauth_provider.models import User, UID
from celery import Celery

def run_tasks(APIS):
    celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')

    tasks = {'twitter': TwitterTasks, 'lastfm': LastfmTasks}
    users = User.get_collection().find()
        
    for user in users:
        uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
        
        for uid in uids:
            if uid['datastream'] in tasks:
                task = tasks[uid['datastream']](
                    user, uid['uid'], api = APIS[uid['datastream']])
                task.run()
