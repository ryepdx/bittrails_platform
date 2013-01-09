from flask import Flask
from flask.ext.login import LoginManager
from settings import PORT, DEBUG, APP_SECRET_KEY
from auth import register_auth_blueprints

import register.signals

def main():
    
    app = Flask(__name__)
    
    with app.app_context():
        import oauth_provider.views
        import api.views

    app.secret_key = APP_SECRET_KEY

    # Register all our routes and blueprints.
    register_auth_blueprints(app)
    app.register_blueprint(api.views.app, url_prefix = '/api')
    app.register_blueprint(oauth_provider.views.app)
    
    # Set up login and registration.
    login_manager = LoginManager()
    login_manager.setup_app(app)
    register.signals.connect_signals(app)
    
    if DEBUG:
        @app.route('/url_map')
        def url_map():
            return str(app.url_map)
    
    # Run the app!
    app.run(host = '0.0.0.0', port = PORT, debug = DEBUG)

if __name__ == '__main__':
    main()
