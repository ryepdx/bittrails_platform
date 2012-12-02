from blinker import Namespace

signals = Namespace()
services_registered = signals.signal('auth.services_registered')
oauth_completed = signals.signal('auth.oauth_completed')
