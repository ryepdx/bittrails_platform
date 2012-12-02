from datetime import timedelta
from wtforms import TextField, validators
from wtforms.ext.csrf.session import SessionSecureForm
from flask import session
from auth.auth_settings import TOKENS_KEY
    
def auth_tokens_check(form, field):
    if len(session[TOKENS_KEY]) == 0:
        raise validators.ValidationError(
            'Please authorize Bit Trails with a service from the list above.')
            
class CSRFProtectedForm(SessionSecureForm):
    SECRET_KEY = 'mkQi8WrIGnOGTDG3g1qwutf856R8NH3iHcIlXhCXiVXivBN84Acb4SGA0ZKRl'
    TIME_LIMIT = timedelta(minutes=20)

class RegistrationForm(CSRFProtectedForm):
    email = TextField('Email', [validators.email(), auth_tokens_check])

