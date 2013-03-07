"""
Classes for connecting to Twitter
"""

import auth.oauth

class TwitterOAuth(auth.oauth.OAuth):
    """
    Provides Twitter's get_uid function.
    """
    def get_uid(self, request, **kwargs):
        if hasattr(request, 'args'):
            return request.args.get('screen_name')
        elif hasattr(request, 'content'):
            return request.content.get('screen_name')
        else:
            return None
