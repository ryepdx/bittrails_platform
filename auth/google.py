"""
Classes for connecting to Google
"""
import json
import requests
import auth.oauth

from flask.ext.login import current_user
from oauth_provider.models import User

class GoogleOAuth(auth.oauth.OAuth2):
    """
    Provides Google's get_uid function and provides support for automatic
    access token refreshing in the request function via OAuth2 refresh tokens.
    """
    refresh_token_url = "https://accounts.google.com/o/oauth2/token"
    
    def get_uid(self, request, oauth_token = None):
        if not oauth_token:
            resp = self.get('oauth2/v1/userinfo', user = current_user)
        else:
            resp = self.get('oauth2/v1/userinfo', access_token = oauth_token)

        if resp.status == 200:
            return resp.content['email']
        else:
            return None
            
    def request(self, *args, **kwargs):
        response = super(GoogleOAuth, self).request(*args, **kwargs)
            
        # If the token has expired, we need to request a new one and try again.
        # We can only do this, though, if a user was passed in.
        if ("error" in response.content
        and "message" in response.content["error"]
        and response.content["error"]["message"] == u'Invalid Credentials'
        and kwargs.get('user', False)):
            
            user = kwargs.get('user')
            
            self._logger.info(
                    "Refreshing expired token for user %s." % user['_id'])
                                
            # Is there a refresh token for this user?
            if ('refresh_tokens' not in user
            or self.name not in user['refresh_tokens']):
                self._logger.error(
                    "User %s does not have a refresh token. Abandoning request." % (
                        user['_id'])
                    )
                import pdb; pdb.set_trace()
                self._logger.info("Abandoned request for user %s was %s" % (
                    user['_id'], args))
            else:
                # Request a new access token.
                refresh = requests.post(
                    self.refresh_token_url,
                    data = { 'refresh_token': user['refresh_tokens'][self.name],
                             'grant_type': 'refresh_token',
                             'client_id': self.consumer_key,
                             'client_secret': self.consumer_secret }
                )
                refresh = json.loads(refresh.content)
            
                # If the user variable is not a User object, retrieve the
                # corresponding object.    
                if ((not hasattr(user, 'save') or not callable(user.save))
                and '_id' in user):
                    user = User.find_one({'_id': user['_id']}, as_obj = True)
                    
                # Was the request for a new token successful?
                if 'access_token' in refresh and refresh['access_token']:
                    
                    # Update the user's Google access token and save it.
                    user['external_tokens'][self.name] = refresh['access_token']
                    user.save()
                    
                    # Retry the original request wit the new token.
                    kwargs['user'] = user
                    response = super(GoogleOAuth, self).request(*args, **kwargs)
                else:
                    # If the request for a new token was not successful, log
                    # Google's response so we can debug later.
                    self._logger.error(
                        "Tried to refresh token for user %s. Instead got: %s" % (
                        user['_id'], response.content)
                    )
        
        return response
        
    
