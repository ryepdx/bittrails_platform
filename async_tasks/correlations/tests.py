import unittest
from api.constants import INTERVALS
from bson import ObjectId
from tasks import CorrelationTask
from correlations.mocks import Mockmodel, Mockmodel2

class TestCorrelationTask(CorrelationTask):
    def __init__(self, *args, **kwargs):
        kwargs['use_cache'] = False
        super(TestCorrelationTask, self).__init__(*args, **kwargs)
        
    @property
    def required_aspects(self):
        return {'google_tasks': [('completed_task', Mockmodel)],
                 'lastfm': [('song_energy', Mockmodel)]}
            
    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5', '> -0.5']
            
    def save_buffs(self, buffs):
        self.buffs = buffs

class TestCorrelationTask2(TestCorrelationTask):
    @property
    def required_aspects(self):
        return {'google_tasks': [('completed_task', Mockmodel)],
                 'lastfm': [('song_energy', Mockmodel)]}

class TestCorrelationTaskClass(unittest.TestCase):        
    def given_a_default_test_task(self):
        return TestCorrelationTask(
            {'_id':ObjectId('50e3da15ab0ddcff7dd3c187')},
            ['google_tasks', 'lastfm'],
            window_size = 3)
        
    def when_task_has_been_run(self, task):
        task.run()
        return task
        
    def should_have_a_correlation_of_one(self, task):
        self.assertEqual(len(task.correlations), len(INTERVALS))
        for interval, correlation in task.correlations.items():
            self.assertEqual(correlation[0].correlation, 1)
            
    def test_counts(self):
        self.should_have_a_correlation_of_one(
            self.when_task_has_been_run(
                self.given_a_default_test_task()
            )
        )
        
class TestCorrelationTaskClass2(TestCorrelationTaskClass):        
    def given_a_default_test_task(self):
        return TestCorrelationTask2(
            {'_id':ObjectId('50e3da15ab0ddcff7dd3c187')},
            ['google_tasks', 'lastfm'],
            window_size = 3)
