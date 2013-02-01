import unittest
from api import INTERVALS
from bson import ObjectId
from tasks import CorrelationTask

class MockModel(object):
    @classmethod
    def get_collection(cls, *args, **kwargs):
        return MockCollection()
    
    @classmethod
    def get_data(cls, instance):
        return instance['data']
        
class MockModel2(MockModel):
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
                {'data': 1.0, 'interval_start': '2012-12-01'},
                {'data': 1.0, 'interval_start': '2012-12-08'},
                {'data': 1.0, 'interval_start': '2012-12-15'},
                {'data': 1.0, 'interval_start': '2012-12-22'},
                {'data': 1.0, 'interval_start': '2012-12-29'},
                {'data': 1.0, 'interval_start': '2013-01-05'},
            ]

class MockCollection2(MockCollection):
    def sort(self, *args, **kwargs):
        if hasattr(self, 'data'):
            return self.data
        else:
            return [
                {'data': 2.0, 'interval_start': '2012-12-01'},
                {'data': 1.0, 'interval_start': '2012-12-08'},
                {'data': 4.0, 'interval_start': '2012-12-15'},
                {'data': 1.0, 'interval_start': '2012-12-22'},
                {'data': 5.0, 'interval_start': '2012-12-29'},
                {'data': 3.0, 'interval_start': '2013-01-05'},
            ]

class TestCorrelationTask(CorrelationTask):
    @property
    def required_aspects(self):
        return {'google_tasks': ('completed_task', MockModel),
                 'lastfm': ('song_energy', MockModel)}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_and_google_tasks_negative'
        else:
            return 'lastfm_and_google_tasks_neutral'
            
    def save_buffs(self, buffs):
        self.buffs = buffs

class TestCorrelationTask2(TestCorrelationTask):
    @property
    def required_aspects(self):
        return {'google_tasks': ('completed_task', MockModel),
                 'lastfm': ('song_energy', MockModel)}

class TestCorrelationTaskClass(unittest.TestCase):        
    def given_a_default_test_task(self):
        return TestCorrelationTask(
            {'_id':ObjectId('50e3da15ab0ddcff7dd3c187')},
            ['google_tasks', 'lastfm'])
        
    def when_task_has_been_run(self, task):
        task.run()
        return task
        
    def should_have_a_positive_buff(self, task):
        self.assertEqual(len(task.buffs), len(INTERVALS))
        self.assertEqual(task.buffs[0].strength, 1)
            
    def test_counts(self):
        self.should_have_a_positive_buff(
            self.when_task_has_been_run(
                self.given_a_default_test_task()
            )
        )
        
class TestCorrelationTaskClass2(TestCorrelationTaskClass):        
    def given_a_default_test_task(self):
        return TestCorrelationTask2(
            {'_id':ObjectId('50e3da15ab0ddcff7dd3c187')},
            ['google_tasks', 'lastfm'])
