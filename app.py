from flask import Flask, session, redirect
#from flask_mail import Mail
from flask.ext.login import LoginManager
from settings import PORT, DEBUG, APP_SECRET_KEY
from auth import register_auth_blueprints

import home.views
import twitter_demo.views
import api.views
import register.signals
import auth.signals
#import register.views

#mail = Mail()

#app = Flask(__name__)
APIS = {}

def main():
    app = Flask(__name__)
    app.secret_key = APP_SECRET_KEY
    
    # Register all our routes and blueprints.
    register_auth_blueprints(app)
    app.register_blueprint(home.views.app)
    #app.register_blueprint(register.views.app, url_prefix = '/register')
    app.register_blueprint(twitter_demo.views.app, url_prefix = '/twitter_demo')
    app.register_blueprint(api.views.app, url_prefix = '/api')
    
    # Set up login and registration.
    login_manager = LoginManager()
    login_manager.setup_app(app)
    register.signals.connect_signals(app)
    
    if DEBUG:
        @app.route('/clear_session')
        def clear_session():
            session.clear()
            return redirect('/')
    
    # Run the app!
    app.run(host = '0.0.0.0', port = PORT, debug = DEBUG)

if __name__ == '__main__':
    main()
