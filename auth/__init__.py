from flask.ext.login import current_user
from blinker import Namespace
from oauth_blueprint import (
    OAuthBlueprint, FoursquareOAuth, TwitterOAuth, OAuth, OAuth2,
    LastFmAuth, LastFmAuthBlueprint, GoogleOAuth)
from settings import (TWITTER_KEY, TWITTER_SECRET, 
                      FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET, 
                      FITBIT_KEY, FITBIT_SECRET,
                      LASTFM_KEY, LASTFM_SECRET,
                      GOOGLE_KEY, GOOGLE_SECRET)
                      
from auth import signals

APIS = {'twitter': TwitterOAuth(
            name = 'twitter',
            base_url = 'https://api.twitter.com/1/',
            request_token_url = 'https://api.twitter.com/oauth/request_token',
            access_token_url = 'https://api.twitter.com/oauth/access_token',
            authorize_url = 'https://api.twitter.com/oauth/authenticate',
            consumer_key = TWITTER_KEY,
            consumer_secret = TWITTER_SECRET,
            aspects = ['tweet_counts']
        ),
        'foursquare': FoursquareOAuth(
            name = 'foursquare',
            base_url = 'https://api.foursquare.com/v2/',
            access_token_url = 'https://foursquare.com/oauth2/access_token',
            authorize_url = 'https://foursquare.com/oauth2/authorize',
            consumer_key = FOURSQUARE_CLIENT_ID, 
            consumer_secret = FOURSQUARE_CLIENT_SECRET,
            aspects = ['checkin_counts']
        ),
        'fitbit': OAuth(
            name = 'fitbit',
            base_url = 'http://api.fitbit.com/',
            request_token_url = 'http://api.fitbit.com/oauth/request_token',
            access_token_url = 'http://api.fitbit.com/oauth/access_token',
            authorize_url = 'http://api.fitbit.com/oauth/authorize',
            consumer_key = FITBIT_KEY, 
            consumer_secret = FITBIT_SECRET,
            aspects = ['post_counts']
        ),
        'lastfm': LastFmAuth(
            name = 'lastfm',
            base_url = 'http://ws.audioscrobbler.com/2.0/',
            access_token_url = 'http://ws.audioscrobbler.com/2.0/?method=auth.getSession&format=json',
            authorize_url = 'http://www.last.fm/api/auth/',
            consumer_key = LASTFM_KEY,
            consumer_secret = LASTFM_SECRET,
            aspects = ['scrobble_counts', 'song_energy_averages']
        ),
        'google_tasks': GoogleOAuth(
            name = 'google_tasks',
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
            request_params = {'key': GOOGLE_KEY},
            aspects = ['completed_task_counts']
        )
    }

BLUEPRINTS = {
    'twitter':
        OAuthBlueprint(
            name = 'twitter',
            api = APIS['twitter'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
        
    'foursquare':
        OAuthBlueprint(
            name = 'foursquare',
            api = APIS['foursquare'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index',
        ),
        
    'fitbit':
        OAuthBlueprint(
            name = 'fitbit',
            api = APIS['fitbit'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
    'lastfm':
        LastFmAuthBlueprint(
            name = 'lastfm',
            api = APIS['lastfm'],
            oauth_refused_view = 'home.index',
            oauth_completed_view = 'home.index'
        ),
    'google_tasks':
        OAuthBlueprint(
            name = 'google_tasks',
            api = APIS['google_tasks'],
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
