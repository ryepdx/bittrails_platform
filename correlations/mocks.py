class Mockmodel(object):
    @classmethod
    def get_collection(cls, *args, **kwargs):
        return MockCollection()
    
    @classmethod
    def get_data(cls, instance):
        return instance['data']
        
class Mockmodel2(Mockmodel):
    @classmethod
    def get_collection(cls, *args, **kwargs):
        return MockCollection2()

class MockCollection(object):
    def set_data(self, data):
        self.data = data
    
    def find(self, *args, **kwargs):
        return self
    
    def sort(self, *args, **kwargs):
        if hasattr(self, 'data'):
            return self.data
        else:
            return [
                {'data': 1.0, 'start': '2012-12-01'},
                {'data': 1.0, 'start': '2012-12-08'},
                {'data': 1.0, 'start': '2012-12-15'},
                {'data': 1.0, 'start': '2012-12-22'},
                {'data': 1.0, 'start': '2012-12-29'},
                {'data': 1.0, 'start': '2013-01-05'},
            ]

class MockCollection2(MockCollection):
    def sort(self, *args, **kwargs):
        if hasattr(self, 'data'):
            return self.data
        else:
            return [
                {'data': 2.0, 'start': '2012-12-01'},
                {'data': 1.0, 'start': '2012-12-08'},
                {'data': 4.0, 'start': '2012-12-15'},
                {'data': 1.0, 'start': '2012-12-22'},
                {'data': 5.0, 'start': '2012-12-29'},
                {'data': 3.0, 'start': '2013-01-05'},
            ]
