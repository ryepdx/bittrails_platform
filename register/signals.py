from blinker import Namespace
from flask import url_for, session
from flask.ext.login import login_user, current_user, logout_user
from oauth_provider.models import User, UID
from bson.objectid import ObjectId
from auth.signals import oauth_completed
from auth.auth_settings import TOKENS_KEY
import auth

def update_user(sender, response, access_token):
    # Has this account been connected before?
    uid = auth.APIS[session['realm']].get_uid(response, oauth_token = access_token)
    uid_obj = UID.find_one(
        {'uid': uid, 'datastream': session['realm']}, as_obj = True)
    
    if not uid_obj:
        if not current_user.is_authenticated():
            user = User()
            user.insert()
        else:
            user = current_user
            
        uid_obj = UID(uid = uid,
                      datastream = session['realm'],
                      user_id = user['_id'])
        uid_obj.insert()
    
    else:
        user = User.find_one({'_id':uid_obj['user_id']}, as_obj = True)
        
    if not 'external_tokens' in user or not isinstance(user['external_tokens'], dict):
        user['external_tokens'] = {}
        
    if not 'refresh_tokens' in user:
        user['refresh_tokens'] = {}
    
    if 'refresh_token' in response.content:
        user['refresh_tokens'][session['realm']] = response.content['refresh_token']
        
    user['external_tokens'][session['realm']] = access_token
    
    if not current_user.is_authenticated():
        login_user(user)
    
    user.save()
    

def load_user(user_id):
    return User.find_one(ObjectId(user_id), as_obj = True)

def connect_signals(app):
    signals = Namespace()
    #user_registered = signals.signal('register.user_registered')
    #user_registered.connect(send_confirmation_email)

    auth.signals.oauth_completed.connect(update_user)
    app.login_manager.user_loader(load_user)
