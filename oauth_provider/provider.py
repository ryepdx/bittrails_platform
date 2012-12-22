import oauth_provider
from flask import request, render_template, g, url_for, redirect, session
from flask.ext.oauthprovider import OAuthProvider
from flask.ext.login import current_user
from bson.objectid import ObjectId
from models import User, UID, Client, Nonce
from models import RequestToken, AccessToken
from utils import require_openid
from auth import APIS
from oauthlib.common import generate_token, add_params_to_uri

class BitTrailsProvider(OAuthProvider):

    @property
    def enforce_ssl(self):
        return False

    @property
    def realms(self):
        #return [u"twitter", u"foursquare"]
        return APIS.keys()
        
    @property
    def nonce_length(self):
        return 20, 40

    def init_app(self, app):
        pass
        
    def init_blueprint(self, blueprint):
        """Setup the 4 default routes."""
        blueprint.add_url_rule(self.request_token_url, view_func=self.request_token,
                         methods=[u'POST'])
        blueprint.add_url_rule(self.access_token_url, view_func=self.access_token,
                         methods=[u'POST'])
        blueprint.add_url_rule(self.register_url, view_func=self.register,
                         methods=[u'GET', u'POST'])
        blueprint.add_url_rule(self.authorize_url, view_func=self.authorize,
                         methods=[u'GET', u'POST'])

    #@require_openid
    def authorize(self):
        if request.method == u"POST" or 'done' in request.args:
            token = request.form.get("oauth_token")
            
            if not token:
                token = request.args.get("oauth_token")
            
            return self.authorized(token, request = request)
        else:
            # TODO: Authenticate client
            token_key = request.args.get(u"oauth_token")
            token = RequestToken.find_one({'token': token_key})
            realm = token['realm']
            
            # TODO: Make this more robust.
            session['realm'] = realm
            
            if realm and realm in APIS:
                #url = ("%s?first_oauth_token=%s" % 
                #    (url_for('%s.finished' % realm, _external = True), token_key))
                session['original_token'] = token_key
                url = url_for('%s.finished' % realm, _external = True)
                resp = APIS[realm].authorize(callback = url)
                
                return resp
            
            return render_template(u"authorize.html", token=token_key,
                realm = token['realm'].title())

    @require_openid
    def register(self):
        if request.method == u'POST':
            client_key = self.generate_client_key()
            secret = self.generate_client_secret()
            # TODO: input sanitisation?
            name = request.form.get(u"name")
            description = request.form.get(u"description")
            callback = request.form.get(u"callback")
            pubkey = request.form.get(u"pubkey")
            # TODO: redirect?
            # TODO: pubkey upload
            # TODO: csrf
            info = {
                u"client_key": client_key,
                u"name": name,
                u"description": description,
                u"secret": secret,
                u"pubkey": pubkey
            }
            client = Client(**info)
            client['callbacks'].append(callback)
            client['user_id'] = current_user.get_id()
            client_id = Client.insert(client)
            current_user.client_ids.append(client_id)
            User.get_collection().save(current_user)
            return render_template(u"client.html", **info)
        else:
            clients = Client.get_collection().find({'_id': {'$in': 
                [ObjectId(oid) for oid in current_user.client_ids]}})
            return render_template(u"register.html", clients=clients)
            
    
    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        
        token = True
        req_token = True
        client = Client.find_one({'client_key':client_key})
        
        if client:
            nonce = Nonce.find_one({'nonce':nonce, 'timestamp':timestamp,
                'client_id':client['_id']})
            
            if nonce:
                if request_token:
                    req_token = RequestToken.find_one(
                        {'_id':nonce['request_token_id'], 'token':request_token})
                    
                if access_token:
                    token = RequestToken.find_one(
                        {'_id':nonce['request_token_id'], 'token':access_token})
                
        return token and req_token and nonce != None

    def validate_redirect_uri(self, client_key, redirect_uri=None):
        client = Client.find_one({'client_key':client_key})
        
        return client != None and (
            len(client['callbacks']) == 1 and redirect_uri is None
            or redirect_uri in (x for x in client['callbacks']))
        
        
    def validate_client_key(self, client_key):
        return (
            Client.find_one({'client_key':client_key}) != None)
        
    def check_realm(self, realm):
        """Check that the realm is one of a set allowed realms.
        """
        valid = True
        
        for r in realm.split(','):
            valid = valid and r in self.realms
        
        return valid

    def validate_requested_realm(self, client_key, realm):
        return True


    def validate_realm(self, client_key, access_token, uri=None, required_realm=None):

        if not required_realm:
            return True

        # insert other check, ie on uri here

        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = AccessToken.find_one(
                {'token':access_token, 'client_id': client['_id']})
            
            if token:
                return token['realm'] in required_realm
        
        return False

    @property
    def dummy_client(self):
        return u'dummy_client'

    @property
    def dummy_resource_owner(self):
        return u'dummy_resource_owner'

    def validate_request_token(self, client_key, resource_owner_key):
        # TODO: make client_key optional
        token = None
        
        if client_key:
            client = Client.find_one({'client_key':client_key})
        
            if client:
                token = RequestToken.find_one(
                    {'token':access_token, 'client_id': client['_id']})
            
        else:
            token = RequestToken.find_one(
                    {'token':resource_owner_key})
        
        return token != None


    def validate_access_token(self, client_key, resource_owner_key):

        token = None
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = AccessToken.find_one(
                {'token':resource_owner_key, 'client_id': client['_id']})
        
        return token != None
        

    def validate_verifier(self, client_key, resource_owner_key, verifier):
        token = None
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = RequestToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id'], 
                 'verifier':verifier})
        
        return token != None
        
        
    def get_callback(self, request_token):
        return RequestToken.find_one(
                {'token':request_token})['callback']


    def get_realm(self, client_key, request_token):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            return RequestToken.find_one(
                {'token':request_token, 'client_id': client['_id']})['realm']
        else:
            return None
        

    def get_client_secret(self, client_key):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            return client['secret']


    def get_rsa_key(self, client_key):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            return client['pubkey']

    def get_request_token_secret(self, client_key, resource_owner_key):
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = RequestToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id']})
                 
            if token:
                return token['secret']
                     
        return None
        

    def get_access_token_secret(self, client_key, resource_owner_key):
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = AccessToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id']})
                 
            if token:
                return token['secret']
                     
        return None

    def save_request_token(self, client_key, request_token, callback,
            realm=None, secret=None):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = RequestToken(
                request_token, callback, secret=secret, realm=realm,
                user_id = current_user.get_id())
            token.client_id = client['_id']
        
            RequestToken.insert(token)

    def save_access_token(self, client_key, access_token, request_token,
            realm=None, secret=None):
        client = Client.find_one({'client_key':client_key})
        
        token = AccessToken(access_token, secret=secret, realm=realm)
        if client:
            req_token = RequestToken.find_one({'token':request_token})
            
            if req_token:
                token['realm'] = req_token['realm']
                token['client_id'] = client['_id']
                
                if not req_token['user_id']:
                    req_token['user_id'] = current_user.get_id()
                    RequestToken.save(req_token)
                
                token['user_id'] = req_token['user_id']
                AccessToken.insert(token)

    def save_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        
        client = Client.find_one({'client_key':client_key})
        
        if client:
            nonce = Nonce(nonce, timestamp)
            nonce.client_id = client['_id']

            if request_token:
                req_token = RequestToken.find_one({'token':request_token})
                nonce.request_token_id = req_token['_id']

            if access_token:
                token = AccessToken.find_one({'token':access_token})
                nonce.access_token_id = token['_id']

            Nonce.insert(nonce)

    def save_verifier(self, request_token, verifier):
        token = RequestToken.find_one({'token':request_token})
        token['verifier'] = verifier
        token['user_id'] = current_user.get_id()
        RequestToken.get_collection().save(token)

    def authorized(self, request_token, request = None):
        """Create a verifier for an user authorized client"""
        verifier = generate_token(length=self.verifier_length[1])
        self.save_verifier(request_token, verifier)
        
        #if request:
        #    response = dict(request.args.items())
        #else:
        response = {}
            
        # Alright, now for the fun part!
        # We need to retrieve the user's unique ID for the service
        # the app just authenticated with them through us.
        service = session['realm']
        uid = APIS[service].get_uid(service, request)
        
        if uid:
            response.update({'uid': uid, 'service': service})
            
        # Are we logged in?
        if current_user.is_authenticated():
            response.update({'btid': current_user.get_id()})
        
        response.update(
            {u'oauth_token': request_token,
             u'oauth_verifier': verifier})
        callback = self.get_callback(request_token)
        
        return redirect(add_params_to_uri(callback, response.items()))
