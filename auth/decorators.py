import auth.signals

def APIs_route(app, *args, **kwargs):    
    '''
    Registers a view that takes a dictionary of all the OAuth API objects
    created in auth.__init__.
    '''
    def APIs_decorator(func):
        '''
        Takes a view function and waits until the dictionary of APIs is
        available before registering it with Flask's routing table.
        '''
        if 'endpoint' not in kwargs:
            kwargs['endpoint'] = func.__name__
            
        def register_route(apis):
            '''
            Receives the dictionary of APIs from the services_registered signal
            and binds it to the view function passed to the APIs_decorator
            function before registering the view function with Flask's routing
            table.
            '''
            @app.route(*args, **kwargs)
            def function():
                return func(apis)
        auth.signals.services_registered.connect(register_route)
        
        return register_route
        
    return APIs_decorator
