from flask_rauth import RauthOAuth1, RauthOAuth2
from flask import redirect, url_for, request, Blueprint, render_template, session
from blinker import Namespace
from auth_settings import TOKENS_KEY
from auth import signals

def oauth_completed(sender, response, access_token):
    if TOKENS_KEY not in session:
        session[TOKENS_KEY] = {}
    session[TOKENS_KEY][sender.name] = access_token
    
signals.oauth_completed.connect(oauth_completed)

'''
TODO: Split the below class into two classes? Right now it mixes the OAuth API
concept and the Blueprint concept.
'''

class OAuthBlueprintBase(Blueprint):
    """
    Creates the endpoints necessary to connect to a webservice using OAuth.
    
    Sends a blinker signal called 'oauth_completed' when OAuth is completed.
    """
    
    def __init__(self, name, oauth_refused_view = '.index',
    oauth_completed_view = '.index'):
        """
        Dynamically builds views and creates endpoints in the routing table for
        connecting to an OAuth-protected webservice.
        """
        super(OAuthBlueprintBase, self).__init__(name, __name__)
        
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
            resp = self.api.authorize(callback = url)
            return resp
        return begin_oauth

    def generate_oauth_finished(self):
        """
        Creates the endpoint that handles a successful OAuth completion.
        """
        @self.api.authorized_handler
        def oauth_finished(resp, access_token):
            if resp is None or resp == 'access_denied':
                return redirect(self.oauth_refused_url)
            
            signals.oauth_completed.send(self, response = resp,
                access_token = access_token)
            
            return redirect(url_for(self.oauth_completed_view))
        return oauth_finished

class OAuth(RauthOAuth1):
    def request(self, method, uri, user = None, **kwargs):
        if user:
            return super(OAuth, self).request(method, uri,
                oauth_token = user.access_keys[self.name], **kwargs)
        else:
            return super(OAuth, self).request(method, uri, **kwargs)

class OAuth2(RauthOAuth2):
    def request(self, method, uri, user = None, **kwargs):
        if user:
            return super(OAuth2, self).request(method, uri,
                access_token = user.access_keys[self.name], **kwargs)
        else:
            return super(OAuth2, self).request(method, uri, **kwargs)

class FoursquareOAuth(OAuth2):
    def request(self, method, uri, user = None, data = {}, **kwargs):
        uri = uri + '&oauth_token=%s' % user.access_keys[self.name]
        return super(FoursquareOAuth, self).request(method, uri,
            user = user, **kwargs)
            

class OAuthBlueprint(OAuthBlueprintBase):
    """
    Creates the endpoints necessary to connect to a webservice using OAuth.
    
    Sends a blinker signal called 'oauth_completed' when OAuth is completed.
    """
    
    def __init__(self, name, base_url, request_token_url, access_token_url,
    authorize_url, consumer_key, consumer_secret, **kwargs):
        """
        Dynamically builds views and creates endpoints in the routing table for
        connecting to an OAuth-protected webservice.
        """
        
        self.api = OAuth(
            name = name,
            base_url = base_url,
            request_token_url = request_token_url,
            access_token_url = access_token_url,
            authorize_url = authorize_url,
            consumer_key = consumer_key,
            consumer_secret = consumer_secret
        )
        return super(OAuthBlueprint, self).__init__(name, **kwargs)
            
class OAuth2Blueprint(OAuthBlueprintBase):
    """
    Creates the endpoints necessary to connect to a webservice using OAuth.
    
    Sends a blinker signal called 'oauth_completed' when OAuth is completed.
    """
    
    def __init__(self, name, base_url, access_token_url, authorize_url, 
    consumer_key, consumer_secret, oauth_class = OAuth2, **kwargs):
        """
        Dynamically builds views and creates endpoints in the routing table for
        connecting to an OAuth-protected webservice.
        """
        
        self.api = oauth_class(
            name = name,
            base_url = base_url,
            access_token_url = access_token_url,
            authorize_url = authorize_url,
            consumer_key = consumer_key,
            consumer_secret = consumer_secret
        )
        
        return super(OAuth2Blueprint, self).__init__(name, **kwargs)
