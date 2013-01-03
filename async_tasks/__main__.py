## For testing purposes.
## Does *almost* the same thing as runner.py, but uses mock API objects instead
## and runs synchronously instead of asynchronously through Celery.

from bson import ObjectId
from tasks import TwitterTasks
from oauth_provider.models import User, UID
from celery import Celery
from auth.mocks import APIS

celery = Celery('bittrails_tasks', broker='amqp://guest@localhost//')

tasks = {'twitter': TwitterTasks}
users = User.get_collection().find()
    
for user in users:
    uids = UID.get_collection().find({'user_id': ObjectId(user['_id'])})
    
    for uid in uids:
        task = tasks[uid['datastream']](
            user, uid['uid'], api = APIS[uid['datastream']])
        task.run()
