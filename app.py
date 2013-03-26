import flask
import settings

app = flask.Flask(__name__)

def setup_app(settings):
    app.secret_key = settings.APP_SECRET_KEY
    app.config['TRAP_BAD_REQUEST_ERRORS'] = settings.DEBUG
    app.config['DATABASES'] = settings.DATABASES

def main(settings = settings, use_reloader = False):
    setup_app(settings)    
    
    import auth
    import oauth_provider.signals
    import flask.ext.login
    
    with app.app_context():
        import oauth_provider.views
        import api.views

    # Register all our routes and blueprints.
    # OAuth services and endpoints (Twitter, Google, Foursquare, etc.)
    auth.register_auth_blueprints(app)
    
    # Platform API endpoints.
    app.register_blueprint(api.views.app)
    
    # Platform OAuth authentication, registration, and management endpoints.
    app.register_blueprint(oauth_provider.views.app)
    
    # Login and registration.
    login_manager = flask.ext.login.LoginManager()
    login_manager.setup_app(app)
    oauth_provider.signals.connect_signals(app)
    
    if settings.DEBUG:
        @app.route('/url_map')
        def url_map():
            return str(app.url_map)
    
    # Run the app!
    app.run(host = '0.0.0.0', port = settings.PORT, debug = settings.DEBUG,
        use_reloader = use_reloader)

if __name__ == "__main__":
    main()
