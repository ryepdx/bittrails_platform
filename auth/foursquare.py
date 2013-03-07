"""
Classes for connecting to Foursquare
"""
import flask
import auth.oauth

from flask.ext.login import current_user


class FoursquareOAuth(auth.oauth.OAuth2):
    """
    Provides Foursquare's get_uid function and provides a request function that
    passes the OAuth access token back to Foursquare in the way it expects.
    """
    
    def request(self, method, uri, user = None, oauth_token = None, **kwargs):
        """
        Foursquare requires the OAuth token to be passed back differently than
        the OAuth2 class does it. Overriding the request method here to
        accomodate the difference.
        """
        if user:
            oauth_token = user['external_tokens'][self.name]
        
        if oauth_token:    
            if '?' in uri:
                uri = (uri + '&oauth_token=%s' % oauth_token)
            else:
                uri = (uri + '?oauth_token=%s' % oauth_token)
            return super(FoursquareOAuth, self).request(method, uri,
                access_token = oauth_token, **kwargs)
        else:
            return flask.abort(400)
            
            
    def get_uid(self, request, oauth_token = None):
        """
        Supply Platform with a unique ID for this user's Foursquare account.
        """
        if not oauth_token:
            resp = self.get('users/self', user = current_user)
        else:
            resp = self.get('users/self', oauth_token = oauth_token)
        
        if resp.status == 200:
            return resp.content['response']['user']['id']
        else:
            return None
