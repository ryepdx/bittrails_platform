"""
Classes to support Last.fm connection.
"""

import auth
import auth.oauth
import flask
import hashlib
import json
import oauthlib.common
import requests

from flask.ext.login import current_user

class LastFmAuth(auth.oauth.Datastream, requests.Session):
    """
    Last.fm doesn't implement OAuth at all. This class allows us to interact
    with Last.fm in the the same way we interact with all the other services,
    most of which *do* implement some version of OAuth.
    """
    
    def __init__(self, app = None, name = None, base_url = None,
    auth_params = None, request_params = None, access_token_url = None,
    authorize_url = None, consumer_key = None, consumer_secret = None,
    **kwargs):
        self.app = app
        self.name = name
        self.base_url = base_url
        self.access_token_url = access_token_url
        self.authorize_url = authorize_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth_params = auth_params if auth_params else {}
        self.request_params = request_params if request_params else {}
        
        super(LastFmAuth, self).__init__(headers=None, cookies=None, auth=None,
            timeout=None, proxies=None, hooks=None, params=None, config=None,
            prefetch=True, verify=True, cert=None, **kwargs)
        
    def call(self, method, user = None, http_method = "GET", **kwargs):
        """
        An abstraction for making Last.fm method calls. Adds a "method" request
        parameter to the request before making it using the method specified
        via http_method.
        """
        if http_method == "GET":
            return self.get('%s?method=%s%s' 
                % (self.base_url, method, ''.join(
                    ['&%s=%s' % (key, kwargs[key]) for key in kwargs.keys()])),
                user = user)
        elif http_method == "POST":
            kwargs['method'] = method
            return self.post('', user = user, data = kwargs)
    
    def request(self, method, uri, user = None, **kwargs):
        """
        Makes an authorized request against Last.fm for the specified user.
        """
        if 'data' in kwargs:
            kwargs['data'] = self.get_signed_params(kwargs['data'], user)
            
        if '?' in uri:
            (uri, params) = uri.split('?')
            uri = oauthlib.common.add_params_to_uri(uri,
                self.get_signed_params(dict(
                    [param.split('=') for param in params.split('&')]
                ), user).items())
        
        return super(LastFmAuth, self).request(method, self.base_url + uri,
            data = kwargs.get('data'), **kwargs)
            
    def get_signed_params(self, params, user):
        """
        Last.fm requires that all requests include a hash of the request's
        parameters after they have been sorted alphabetically and had the
        client secret appended. This generates that hash and adds it to the
        parameters dictionary passed in.
        """
        sig_string = ''
        params['api_key'] = self.consumer_key
        
        if user and self.name in user['external_tokens']:
            params['sk'] = user['external_tokens'][self.name]
            
        for key in sorted(params.keys()):
            if key not in ('format', 'callback'):
                sig_string = '%s%s%s' % (sig_string, key, params[key])
            
        sig_string = sig_string + self.consumer_secret
        params['api_sig'] = hashlib.md5(sig_string).hexdigest()
        
        return params
            
    def authorize(self, callback):
        """
        Sends the user off to Last.fm to authorize our client to access their
        account information.
        """
        url = '%s?api_key=%s' % (self.authorize_url, self.consumer_key)
        
        if callback:
            url = '%s&cb=%s' % (url, callback)
        
        return flask.redirect(url)
    
            
    def get_uid(self, request, oauth_token = None):
        """
        Returns the user's Last.fm ID.
        """
        if not oauth_token:
            resp = self.call('user.getInfo', format='json', user = current_user)
        else:
            resp = self.call('user.getInfo', format='json', sk = oauth_token)

        if resp.status_code == 200:
            return json.loads(resp.content)['user']['id']
        else:
            return None


class LastFmAuthBlueprint(auth.oauth.OAuthBlueprint):
    """
    Provides a custom oauth_finished function for Last.fm.
    """
    
    def generate_oauth_finished(self):
        """
        Creates the endpoint that handles a successful OAuth completion.
        """
        def oauth_finished():
            if 'token' not in flask.request.args:
                return flask.redirect(self.oauth_refused_url)
                
            token = flask.request.args['token']
            
            http_resp = self.api.get(
                '%s&token=%s' % (self.api.access_token_url, token))
                
            # Create an object with a "content" attribute set to the (decoded)
            # JSON data returned by Last.fm.
            resp = type('obj', (object,),
                {'content' : json.loads(http_resp.content)})
            
            auth.signals.oauth_completed.send(self, response = resp,
                access_token = resp.content['session']['key'])
            
            token_key = flask.session.pop(u"original_token", None)
            
            if token_key:
                del resp.content['session']['key']
                resp.content.update({u'oauth_token': token_key})
                return flask.redirect(
                    oauthlib.common.add_params_to_uri(
                        flask.url_for('oauth_provider.authorize'), 
                        resp.content.items()) + "&done")
                
            return flask.redirect(flask.url_for(self.oauth_completed_view))
        return oauth_finished
