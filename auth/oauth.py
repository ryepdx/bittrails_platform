"""
Base classes for accessing OAuth services.
"""

import auth
import flask
import logging
import flask_rauth
import oauthlib.common

from flask.ext.rauth import ACCESS_DENIED

class Datastream(object):
    """
    Provides the foundation for every datastream we hook up. Forces every
    datastream to implement get_uid and provides each one with a logger.
    """
    def __init__(self, **kwargs):
        self._logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__)
        super(Datastream, self).__init__(**kwargs)
        
    def get_uid(self, request, oauth_token = None):
        """
        Should return a string that can be used to identify the user when they
        log in with this service. Can be anything as long as it is guaranteed
        to be unique and to never change.
        
        Gets passed a copy of the request the OAuth service makes to our server
        when the user authorizes us to access their account on that service, and
        a copy of the OAuth access token.
        """
        raise NotImplementedError("Child class must implement this method!")


class OAuth(Datastream, flask_rauth.RauthOAuth1):
    """
    Spec-compliant OAuth v1 implementation.
    """
    def __init__(self, auth_params = None, request_params = None, **kwargs):
        self.auth_params = auth_params if auth_params != None else {}
        self.request_params = request_params if request_params != None else {}
        super(OAuth, self).__init__(**kwargs)
        
    def request(self, method, uri, user = None, **kwargs):
        """
        Make an HTTP request against the OAuth service.
        """
        if user:
            return super(OAuth, self).request(method, uri,
                oauth_token = user['external_tokens'][self.name], **kwargs)
        else:
            return super(OAuth, self).request(method, uri, **kwargs)

class OAuth2(Datastream, flask_rauth.RauthOAuth2):
    """
    Spec-compliant OAuth v2 implementation.
    """
    def __init__(self, auth_params = None, request_params = None, **kwargs):
        self.auth_params = auth_params if auth_params != None else {}
        self.request_params = request_params if request_params != None else {}
        super(OAuth2, self).__init__(**kwargs)
        
    def request(self, method, uri, user = None, **kwargs):
        """
        Make an HTTP request against the OAuth service.
        """
        if self.request_params:
            params = []
            for key, value in self.request_params.items():
                params.append(key+'='+value)
                
            if '?' in uri:
                uri = (uri + '&' + '&'.join(params))
            else:
                uri = (uri + '?' + '&'.join(params))
        
        if user:
            return super(OAuth2, self).request(method, uri,
                access_token = user['external_tokens'][self.name], **kwargs)
        else:
            return super(OAuth2, self).request(method, uri, **kwargs)



class OAuthBlueprint(flask.Blueprint):
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
            return flask.render_template('oauth_blueprint/index.html',
                                    service_name = self.name.title(),
                                    begin_url = flask.url_for('.begin'))
        return index
            
    def generate_begin_oauth(self):
        """
        Creates the endpoint that prompts the user to authorize our app to use
        their data on the webservice we're connecting to.
        """
        def begin_oauth():
            url = flask.url_for('.finished', _external = True)
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
                return flask.redirect(
                    flask.url_for(self.oauth_refused_view))
            
            auth.signals.oauth_completed.send(self, response = resp,
                access_token = access_token)
            
            token_key = flask.session.get(u"original_token", None)
            
            if token_key:
                flask.session.pop(u"original_token", None)
                query = resp._cached_content
                query.update({u'oauth_token': token_key})
                return flask.redirect(
                    oauthlib.common.add_params_to_uri(
                        flask.url_for('oauth_provider.authorize'), query.items()
                    ) + "&done")
                
            return flask.redirect(flask.url_for(self.oauth_completed_view))
        return oauth_finished
