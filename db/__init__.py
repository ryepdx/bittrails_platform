import pymongo

def get_connection(db_name):
    return pymongo.MongoClient()[db_name]
