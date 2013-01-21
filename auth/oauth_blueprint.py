import auth
import hashlib
import requests
import json
import rauth.service

from functools import wraps
from flask_rauth import RauthOAuth1, RauthOAuth2
from flask import redirect, url_for, request, Blueprint, render_template, session, abort
from flask.ext.login import current_user
from flask.ext.rauth import ACCESS_DENIED, RauthException, RauthResponse
from blinker import Namespace
from auth_settings import TOKENS_KEY
from auth import signals
from oauthlib.common import add_params_to_uri

def oauth_completed(sender, response, access_token):
    if TOKENS_KEY not in session:
        session[TOKENS_KEY] = {}
    session[TOKENS_KEY][sender.name] = access_token
    
signals.oauth_completed.connect(oauth_completed)

'''
TODO: Split the below class into two classes? Right now it mixes the OAuth API
concept and the Blueprint concept.
'''

class OAuthBlueprint(Blueprint):
    """
    Creates the endpoints necessary to connect to a webservice using OAuth.
    
    Sends a blinker signal called 'oauth_completed' when OAuth is completed.
    """
    
    def __init__(self, name, api, oauth_refused_view = '.index',
    oauth_completed_view = '.index'):
        """
        Dynamically builds views and creates endpoints in the routing table for
        connecting to an OAuth-protected webservice.
        """
        super(OAuthBlueprint, self).__init__(name, __name__)
        
        self.api = api
        self.oauth_refused_view = oauth_refused_view
        self.oauth_completed_view = oauth_completed_view
        
        self.add_url_rule('/', 'index', self.generate_index())
        self.add_url_rule('/begin', 'begin', self.generate_begin_oauth())
        self.add_url_rule('/finished', 'finished',
            self.generate_oauth_finished())
            
    def generate_index(self):
        """
        Creates a view that prompts the user to connect the OAuth webservice
        to ours.
        """
        def index():
            return render_template('oauth_blueprint/index.html',
                                    service_name = self.name.title(),
                                    begin_url = url_for('.begin'))
        return index
            
    def generate_begin_oauth(self):
        """
        Creates the endpoint that prompts the user to authorize our app to use
        their data on the webservice we're connecting to.
        """
        def begin_oauth():
            url = url_for('.finished', _external = True)
            resp = self.api.authorize(callback = url, **self.api.auth_params)
            return resp
        return begin_oauth

    def generate_oauth_finished(self):
        """
        Creates the endpoint that handles a successful OAuth completion.
        """
        @self.api.authorized_handler
        def oauth_finished(resp, access_token):
            if resp is None or resp == ACCESS_DENIED:
                return redirect(self.oauth_refused_url)
            
            signals.oauth_completed.send(self, response = resp,
                access_token = access_token)
            
            token_key = session.get(u"original_token", None)
            
            if token_key:
                session.pop(u"original_token", None)
                qs = resp._cached_content
                qs.update({u'oauth_token': token_key})
                return redirect(
                    add_params_to_uri(url_for('oauth_provider.authorize'), 
                        qs.items()) + "&done")
                
            return redirect(url_for(self.oauth_completed_view))
        return oauth_finished

class LastFmAuthBlueprint(OAuthBlueprint):
    
    def generate_oauth_finished(self):
        """
        Creates the endpoint that handles a successful OAuth completion.
        """
        def oauth_finished():
            if 'token' not in request.args:
                return redirect(self.oauth_refused_url)
                
            token = request.args['token']
            resp = json.loads(
                self.api.get('%s&token=%s' % (self.api.access_token_url, token)).content
            )
            
            signals.oauth_completed.send(self, response = resp,
                access_token = resp['session']['key'])
            
            token_key = session.pop(u"original_token", None)
            
            if token_key:
                del resp['session']['key']
                resp.update({u'oauth_token': token_key})
                return redirect(
                    add_params_to_uri(url_for('oauth_provider.authorize'), 
                        resp.items()) + "&done")
                
            return redirect(url_for(self.oauth_completed_view))
        return oauth_finished

class OAuthGetUID(object):
    def get_uid(self, request):
        raise NotImplemented("Child class must implement this method!")


class OAuth(RauthOAuth1, OAuthGetUID):
    def __init__(self, auth_params = {}, **kwargs):
        self.auth_params = auth_params
        super(OAuth, self).__init__(**kwargs)
        
    def request(self, method, uri, user = None, **kwargs):
        if user:
            return super(OAuth, self).request(method, uri,
                oauth_token = user['external_tokens'][self.name], **kwargs)
        else:
            return super(OAuth, self).request(method, uri, **kwargs)

class OAuth2(RauthOAuth2, OAuthGetUID): 
    def __init__(self, auth_params = {}, **kwargs):
        self.auth_params = auth_params
        super(OAuth2, self).__init__(**kwargs)
        
    def request(self, method, uri, user = None, **kwargs):
        if user:
            return super(OAuth2, self).request(method, uri,
                access_token = user['external_tokens'][self.name], **kwargs)
        else:
            return super(OAuth2, self).request(method, uri, **kwargs)

class FoursquareOAuth(OAuth2):
    def request(self, method, uri, user = None, **kwargs):
        if user:
            if '?' in uri:
                uri = (uri + '&oauth_token=%s'
                    % user['external_tokens'][self.name])
            else:
                uri = (uri + '?oauth_token=%s'
                    % user['external_tokens'][self.name])
            return super(FoursquareOAuth, self).request(method, uri,
                user = user, **kwargs)
        else:
            return abort(400)
            
    def get_uid(self, response, oauth_token = None):
        if not oauth_token:
            resp = self.get('users/self', user = current_user)
        else:
            resp = self.get('users/self', oauth_token = oauth_token)
        
        if resp.status == 200:
            return resp.content['response']['user']['id']
        else:
            return None
            
class TwitterOAuth(OAuth):
    def get_uid(self, response, oauth_token = None):
        if hasattr(response, 'args'):
            return response.args.get('screen_name')
        elif hasattr(response, 'content'):
            return response.content.get('screen_name')
        else:
            return None
            
class GoogleOAuth(OAuth2):
    def get_uid(self, response, oauth_token = None):
        if not oauth_token:
            resp = self.get('oauth2/v1/userinfo', user = current_user)
        else:
            resp = self.get('oauth2/v1/userinfo', access_token = oauth_token)

        if resp.status == 200:
            return resp.content['email']
        else:
            return None
    
class LastFmAuth(requests.Session, OAuthGetUID):
    def __init__(self, app = None, name = None, base_url = None,
    access_token_url = None, authorize_url = None, consumer_key = None,
    consumer_secret = None):
        self.app = app
        self.name = name
        self.base_url = base_url
        self.access_token_url = access_token_url
        self.authorize_url = authorize_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        super(LastFmAuth, self).__init__(headers=None, cookies=None, auth=None,
            timeout=None, proxies=None, hooks=None, params=None, config=None,
            prefetch=True, verify=True, cert=None)
        
    def call_with_post(self, method, **kwargs):
        return self.call(method, http_method = "POST", **kwargs)
            
    def call(self, method, user = None, http_method = "GET", **kwargs):
        if http_method == "GET":
            return self.get('%s?method=%s%s' 
                % (self.base_url, method, ''.join(
                    ['&%s=%s' % (key, kwargs[key]) for key in kwargs.keys()])),
                user = user)
        elif http_method == "POST":
            kwargs['method'] = method
            return self.post('', user = user, data = kwargs)
    
    def request(self, method, uri, user = None, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = self.get_signed_params(kwargs['data'], user)
            
        if '?' in uri:
            (uri, params) = uri.split('?')
            uri = add_params_to_uri(uri,
                self.get_signed_params(dict(
                    [param.split('=') for param in params.split('&')]
                ), user).items())
             
        return super(LastFmAuth, self).request(method, self.base_url + uri,
            data = kwargs.get('data'), **kwargs)
            
    def get_signed_params(self, params, user):
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
        url = '%s?api_key=%s' % (self.authorize_url, self.consumer_key)
        
        if callback:
            url = '%s&cb=%s' % (url, callback)
        
        return redirect(url)
    
            
    def get_uid(self, response, oauth_token = None):
        if not oauth_token:
            resp = self.call('user.getInfo', format='json', user = current_user)
        else:
            resp = self.call('user.getInfo', format='json', sk = oauth_token)

        if resp.status_code == 200:
            return json.loads(resp.content)['user']['id']
        else:
            return None
