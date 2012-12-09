from blinker import Namespace
import auth
from flask import url_for, session
from flask.ext.login import login_user, current_user
from register.models import User
from bson.objectid import ObjectId
from auth.signals import oauth_completed
from auth.auth_settings import TOKENS_KEY

def update_user(sender, response, access_token):
    if sender.name == 'twitter' and 'screen_name' in response.content:
        register_twitter_user(sender, response, access_token)
    elif current_user.is_authenticated():
        session[TOKENS_KEY][sender.name] = access_token
        current_user.access_keys = session[TOKENS_KEY]
        User.get_collection().update(
            {'_id':current_user._id},
            {'$set': {'access_keys': current_user.access_keys}})
        

def register_twitter_user(sender, response, access_token):
    if sender.name == 'twitter' and 'screen_name' in response.content:
        users = User.get_collection()
        twitter_handle = response.content['screen_name']
        user = users.find_one({'twitter_handle': twitter_handle})
        
        if user:
            user = User(**user)
        else:
            user = User(twitter_handle, session[TOKENS_KEY], confirmed = True)
            user_id = User.get_collection().insert(dict(user))
            user._id = user_id
        
        session[TOKENS_KEY] = user.access_keys
        login_user(user)

def load_user(user_id):
    return User(**(User.get_collection().find_one(ObjectId(user_id))))

def connect_signals(app):
    signals = Namespace()
    #user_registered = signals.signal('register.user_registered')
    #user_registered.connect(send_confirmation_email)

    auth.signals.oauth_completed.connect(update_user)
    app.login_manager.user_loader(load_user)
