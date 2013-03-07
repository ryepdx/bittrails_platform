import auth
import hashlib
import logging
import json
import rauth.service
import requests

from functools import wraps
from flask_rauth import RauthOAuth1, RauthOAuth2
from flask import redirect, url_for, request, Blueprint, render_template, session, abort
from flask.ext.login import current_user
from flask.ext.rauth import ACCESS_DENIED, RauthException, RauthResponse
from blinker import Namespace
from auth_settings import TOKENS_KEY
from auth import signals
from oauthlib.common import add_params_to_uri
from oauth_provider.models import User

def oauth_completed(sender, response, access_token):
    if TOKENS_KEY not in session:
        session[TOKENS_KEY] = {}
    session[TOKENS_KEY][sender.name] = access_token
    
signals.oauth_completed.connect(oauth_completed)
