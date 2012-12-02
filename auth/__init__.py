from blinker import Namespace
from oauth_blueprint import (OAuthBlueprint, OAuth2Blueprint, FoursquareOAuth)
from settings import (TWITTER_KEY, TWITTER_SECRET, 
                      FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET, 
                      FITBIT_KEY, FITBIT_SECRET,
                      LASTFM_KEY, LASTFM_SECRET)
                      
from auth import signals

def get_blueprints():
    return [
        OAuthBlueprint(
            name = 'twitter',
            base_url = 'https://api.twitter.com/1/',
            request_token_url = 'https://api.twitter.com/oauth/request_token',
            access_token_url = 'https://api.twitter.com/oauth/access_token',
            authorize_url = 'https://api.twitter.com/oauth/authenticate',
            consumer_key = TWITTER_KEY,
            consumer_secret = TWITTER_SECRET,
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
        OAuth2Blueprint(
            name = 'foursquare',
            base_url = 'https://api.foursquare.com/v2/',
            access_token_url = 'https://foursquare.com/oauth2/access_token',
            authorize_url = 'https://foursquare.com/oauth2/authenticate',
            consumer_key = FOURSQUARE_CLIENT_ID, 
            consumer_secret = FOURSQUARE_CLIENT_SECRET,
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index',
            oauth_class = FoursquareOAuth
        ),
        OAuthBlueprint(
            name = 'fitbit',
            base_url = 'http://api.fitbit.com/',
            request_token_url = 'http://api.fitbit.com/oauth/request_token',
            access_token_url = 'http://api.fitbit.com/oauth/access_token',
            authorize_url = 'http://api.fitbit.com/oauth/authorize',
            consumer_key = FITBIT_KEY, 
            consumer_secret = FITBIT_SECRET,
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
        #LastfmBlueprint(
        #    name = 'last.fm',
        #    base_url = 'http://www.last.fm/api/',
        #    access_token_url = 'https://foursquare.com/oauth2/access_token',
        #    authorize_url = 'https://last.fm/api/auth/?api_key=%s' % LASTFM_KEY,
        #    consumer_key = LASTFM_KEY, 
        #    consumer_secret = LASTFM_SECRET,
        #    oauth_refused_view = 'home.index',
        #    oauth_completed_view = 'home.index'
        #)
    ]

def register_auth_blueprints(app):
    oauth_services = {}
    blueprints = get_blueprints()
    
    for blueprint in blueprints:
        app.register_blueprint(blueprint,
            url_prefix = '/auth/%s' % blueprint.name)
        oauth_services[blueprint.name] = blueprint.api
    
    signals.services_registered.send(oauth_services)
    
    return oauth_services
