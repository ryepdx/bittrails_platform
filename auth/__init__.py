import auth.oauth
import auth.twitter
import auth.google
import auth.lastfm
import auth.foursquare

from flask.ext.login import current_user
from blinker import Namespace

from settings import (TWITTER_KEY, TWITTER_SECRET, 
                      FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET, 
                      FITBIT_KEY, FITBIT_SECRET,
                      LASTFM_KEY, LASTFM_SECRET,
                      GOOGLE_KEY, GOOGLE_SECRET)
                      
from auth import signals

APIS = {'twitter': auth.twitter.TwitterOAuth(
            name = 'twitter',
            base_url = 'https://api.twitter.com/1/',
            request_token_url = 'https://api.twitter.com/oauth/request_token',
            access_token_url = 'https://api.twitter.com/oauth/access_token',
            authorize_url = 'https://api.twitter.com/oauth/authenticate',
            consumer_key = TWITTER_KEY,
            consumer_secret = TWITTER_SECRET
        ),
        'foursquare': auth.foursquare.FoursquareOAuth(
            name = 'foursquare',
            base_url = 'https://api.foursquare.com/v2/',
            access_token_url = 'https://foursquare.com/oauth2/access_token',
            authorize_url = 'https://foursquare.com/oauth2/authorize',
            consumer_key = FOURSQUARE_CLIENT_ID, 
            consumer_secret = FOURSQUARE_CLIENT_SECRET
        ),
        'fitbit': auth.oauth.OAuth(
            name = 'fitbit',
            base_url = 'http://api.fitbit.com/',
            request_token_url = 'http://api.fitbit.com/oauth/request_token',
            access_token_url = 'http://api.fitbit.com/oauth/access_token',
            authorize_url = 'http://api.fitbit.com/oauth/authorize',
            consumer_key = FITBIT_KEY, 
            consumer_secret = FITBIT_SECRET
        ),
        'lastfm': auth.lastfm.LastFmAuth(
            name = 'lastfm',
            base_url = 'http://ws.audioscrobbler.com/2.0/',
            access_token_url = 'http://ws.audioscrobbler.com/2.0/?method=auth.getSession&format=json',
            authorize_url = 'http://www.last.fm/api/auth/',
            consumer_key = LASTFM_KEY,
            consumer_secret = LASTFM_SECRET
        ),
        'google': auth.google.GoogleOAuth(
            name = 'google',
            base_url = 'https://www.googleapis.com/',
            access_token_url = 'https://accounts.google.com/o/oauth2/token',
            authorize_url = 'https://accounts.google.com/o/oauth2/auth',
            consumer_key = GOOGLE_KEY, 
            consumer_secret = GOOGLE_SECRET,
            auth_params = {
                'access_type': 'offline',
                'response_type': 'code',
                'scope': 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/tasks.readonly',
                'approval_prompt': 'force'
            },
            request_params = {'key': GOOGLE_KEY}
        )
    }

BLUEPRINTS = {
    'twitter':
        auth.oauth.OAuthBlueprint(
            name = 'twitter',
            api = APIS['twitter'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
        
    'foursquare':
        auth.oauth.OAuthBlueprint(
            name = 'foursquare',
            api = APIS['foursquare'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index',
        ),
        
    'fitbit':
        auth.oauth.OAuthBlueprint(
            name = 'fitbit',
            api = APIS['fitbit'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
    'lastfm':
        auth.lastfm.LastFmAuthBlueprint(
            name = 'lastfm',
            api = APIS['lastfm'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
    'google':
        auth.oauth.OAuthBlueprint(
            name = 'google',
            api = APIS['google'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        )
    }
    
    
def register_auth_blueprints(app):
    oauth_services = {}
    
    for key in BLUEPRINTS:
        app.register_blueprint(BLUEPRINTS[key],
            url_prefix = '/auth/%s' % key)
        oauth_services[key] = BLUEPRINTS[key].api
    
    signals.services_registered.send(oauth_services)
    
    return oauth_services
