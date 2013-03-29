from flask import abort, request
from oauth_provider.models import User, AccessToken

def provide_oauth_token(_f):
    def wrapped(*args, **kwargs):
        if request.method ==  "GET":
            token_key = request.args.get('oauth_token')
        elif request.method == "POST":
            token_key = request.form.get('oauth_token')
            
        token = AccessToken.find_one({'token': token_key})
        
        if token:
            token = AccessToken(**token)
            
            return _f(token, *args, **kwargs)
            
        else:
            # No OAuth token? Give them an "unauthorized" response.
            abort(403)
            
    return wrapped

def provide_oauth_user(_f):
    def wrapped(*args, **kwargs):
        
        def _provide_user(token, *args, **kwargs):
            user = User.find_one({'_id': token['user_id']})
            return _f(user, *args, **kwargs)
            
        return provide_oauth_token(_provide_user)(*args, **kwargs)
    return wrapped
