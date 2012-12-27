from db.models import Model, mongodb_init, simple_init

class AsyncModel(Model):
    @classmethod
    def get_collection(cls, database = "async_tasks"):
        super(AsyncModel, cls).get_collection(database = database)

class PostsCount(AsyncModel):
    table = 'posts_count'
    
    @simple_init
    @mongodb_init
    def __init__(self, user_id = '', datastream = '', posts_count = 0):
        pass

    def get_count(self):
        raise NotImplementedError("Child classes must supply this method.")
        
    def update(self):
        self.posts_count = self.get_count()
        self.save()

