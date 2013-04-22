import pymongo
import app as platform

if 'DATABASE_PORT' in platform.app.config:
    PORT = platform.app.config['DATABASE_PORT']
else:
    PORT = 27017

def get_connection(db_name):
    return pymongo.MongoClient(port = PORT)[db_name]
