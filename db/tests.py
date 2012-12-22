import unittest
import bson.objectid
from oauth_provider import models

SIMPLE_TEST_OBJECT_ID = u'50d280f9fb5d1b1541ef2c24'

class TestUserModel(unittest.TestCase):
    
    def setUp(self):
        pass

    def test_get_id(self):
        self.should_get_objectid_type_object_id(
        self.when_referencing__id(
        self.with_simple_user()))
        
    def test_id_object_id_conversion(self):
        self.should_get_unicode_object_id(
        self.when_calling_get_id(
        self.with_simple_user()))
        
    def should_get_unicode_object_id(self, obj_id):
        return self.assertEqual(SIMPLE_TEST_OBJECT_ID, obj_id)
        
    def should_get_objectid_type_object_id(self, obj_id):
        return self.assertEqual(
            bson.objectid.ObjectId(SIMPLE_TEST_OBJECT_ID), obj_id)
    
    def when_calling_get_id(self, obj):
        return obj.get_id()
        
    def when_referencing__id(self, obj):
        return obj._id
        
    def with_simple_user(self):
        return models.User(
            _id=SIMPLE_TEST_OBJECT_ID, name='Someone')
