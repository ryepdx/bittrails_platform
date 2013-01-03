import datetime

from api import INTERVALS
from email.utils import parsedate_tz
from models import PostsCount
from oauth_provider.models import User

class PostCounter(object):
    def __init__(self, datastream_name):
        self.counts = {}
        self.datastream_name = datastream_name
        
    def get_timeslots(self, datetime_obj, intervals = INTERVALS):
        slots = {
            #'hour': self.get_hour(datetime_obj),
            'day': PostsCount.get_day_start(datetime_obj),
            'week': PostsCount.get_week_start(datetime_obj),
            'month': PostsCount.get_month_start(datetime_obj),
            'year': PostsCount.get_year_start(datetime_obj)
        }
        
        for key in slots.keys():
            if key not in intervals:
                del slots[key]
                
        return slots
        
    def get_count_key(self, interval, which_interval):
        return '%s:%s' % (interval, which_interval)
        
    def handle(self, user, post, intervals = INTERVALS):
        date_posted = self.get_datetime(post)
        slots = self.get_timeslots(date_posted, intervals = intervals)
        
        for interval in slots.keys():
            count_key = self.get_count_key(interval, str(slots[interval]))
            
            if count_key not in self.counts:
                self.counts[count_key] = PostsCount.find_or_create(
                    user_id = user['_id'],
                    interval = interval,
                    interval_start = slots[interval],
                    datastream = self.datastream_name
                )
            
            self.counts[count_key].posts_count += 1

    def finalize(self):
        for count in self.counts:
            self.counts[count].save()


class TwitterPostCounter(PostCounter):
    def __init__(self):
        super(TwitterPostCounter, self).__init__('twitter')
        
    @classmethod
    def get_datetime(cls, post):
        assert 'created_at' in post
        time_tuple = parsedate_tz(post['created_at'].strip())
        dt = datetime.datetime(*time_tuple[:6])
        return dt - datetime.timedelta(seconds=time_tuple[-1])

