import pymongo

def get_connection():
    return pymongo.MongoClient().bittrails
