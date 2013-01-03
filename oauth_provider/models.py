import pymongo
from db.models import Model, mongodb_init

class User(Model):
    table = "users"
    
    @mongodb_init
    def __init__(self, name="", email="", openid="", confirmed=True,
    external_tokens = {}, client_ids = [], **kwargs):
        self.name = name
        self.email = email
        self.openid = openid
        self.confirmed = confirmed
        self.external_tokens = external_tokens
        self.client_ids = client_ids
        vars(self).update(kwargs)

    def is_active(self):
        return self.confirmed
        
    def is_authenticated(self):
        return hasattr(self, '_id')
        
    def is_anonymous(self):
        return not hasattr(self, '_id')
        
    def get_id(self):
        return unicode(self._id)

    def __repr__(self):
        return "<User (%s, %s)>" % (self.name, self.email)


class Client(Model):
    table = "clients"

    @mongodb_init
    def __init__(self, client_key, name, description, secret=None, pubkey=None,
    request_tokens = [], access_tokens = [], callbacks = [], user_id = ''):
        self.client_key = client_key
        self.name = name
        self.description = description
        self.secret = secret
        self.pubkey = pubkey
        self.request_tokens = request_tokens
        self.access_tokens = access_tokens
        self.callbacks = callbacks
        self.user_id = user_id

    def __repr__(self):
        return "<Client (%s, %s)>" % (self.name, self._id)


class Nonce(Model):
    table = "nonces"

    @mongodb_init
    def __init__(self, nonce, timestamp, client_id = '', request_token_id = '',
    access_token_id = ''):
        self.nonce = nonce
        self.timestamp = timestamp
        self.client_id = client_id
        self.request_token_id = request_token_id
        self.access_token_id = access_token_id

    def __repr__(self):
        return "<Nonce (%s, %s, %s, %s)>" % (self.nonce, self.timestamp, 
            self.client_id, self.user_id)


class RequestToken(Model):
    table = "requestTokens"

    @mongodb_init
    def __init__(self, token = '', callback = '', secret=None, verifier=None,
    realm=None, user_id = '', client_id = ''):
        self.token = token
        self.callback = callback
        self.secret = secret
        self.verifier = verifier
        self.realm = realm
        self.user_id = user_id
        self.client_id = client_id
        
    def __repr__(self):
        return "<RequestToken (%s, %s, %s)>" % (self.token, self.client_id, self.user_id)


class AccessToken(Model):
    table = "accessTokens"

    @mongodb_init
    def __init__(self, token='', secret=None, verifier=None, realm=None,
    user_id = '', client_id = ''):
        self.token = token
        self.secret = secret
        self.verifier = verifier
        self.realm = realm
        self.user_id = user_id
        self.client_id = client_id

    def __repr__(self):
        return "<AccessToken (%s, %s, %s)>" % (self.token, self.client_id, self.user_id)


class UID(Model):
    table = "UIDs"
    
    @mongodb_init
    def __init__(self, uid, datastream, user_id):
        self.uid = uid
        self.datastream = datastream
        self.user_id = user_id
    
    def __repr__(self):
        return "<UID (%s, %s, %s)>" % (
            self.uid, self.datastream, self.user_id)
