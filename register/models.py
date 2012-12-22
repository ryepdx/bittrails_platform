from db.models import Model

#class User(Model):
#    table = "users"
    
#    def __init__(self, twitter_handle, access_keys, confirmed = False, **kwargs):
#        super(User, self).__init__(
#            twitter_handle = twitter_handle,
#            access_keys = access_keys,
#            confirmed = confirmed,
#            **kwargs
#        )
#        
#    def is_active(self):
#        return self.confirmed
#        
#    def is_authenticated(self):
#        return hasattr(self, '_id')
#        
#    def is_anonymous(self):
#        return not hasattr(self, '_id')
#        
#    def get_id(self):
#        return str(self._id)
