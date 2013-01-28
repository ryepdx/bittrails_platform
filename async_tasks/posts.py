import json
from oauthlib.common import add_params_to_uri
from auth import APIS
from email.utils import parsedate_tz, formatdate, mktime_tz

class Posts(object):
    def __init__(self, user, uid, latest_position = 1, api = None):
        self.uid = uid
        self.user = user
        self._latest_position = latest_position
        self.posts = []
        self.max_index = 0
        self.index = 0
        self.api = api
        
    def __iter__(self):
        return self
        
    def next(self):
        if not self.posts or self.index > self.max_index:
            self.index = 0
            self.posts = self.get_posts()
        
            if self.posts:
                self.max_index = len(self.posts) - 1
                curr_position = self.get_position(self.posts[0]);
                
                if self.position_gt(curr_position, self._latest_position):
                    self._latest_position = curr_position
            else:
                raise StopIteration      

        post = self.posts[self.index]
        self.index += 1
        return post
        
    def position_gt(self, a, b):
        return int(a) > int(b)
        
    def get_posts(self):
        all_posts = []
        
        if self._latest_position:
            self.set_min_position_param(self._latest_position)
        
        i = 0
        keep_requesting = True
        
        while keep_requesting:
            posts = self.get_posts_content(self.api.get(add_params_to_uri(
                self.request_uri, self.params.items()), user = self.user))
            
            if posts and not 'errors' in posts:
                self.set_max_position_param(self.get_position(posts[-1]))
                all_posts.extend(posts)
                
                i += 1
                keep_requesting = i < self.max_requests
            else:
                keep_requesting = self.keep_requesting_when_no_posts_returned()
                
        return all_posts
        
    def keep_requesting_when_no_posts_returned(self):
        return False
    
    @property
    def latest_position(self):
        return self._latest_position
    
    @property
    def request_uri(self):
        raise NotImplemented("Must be implemented by child classes.")
        
    @property
    def max_requests(self):
        raise NotImplemented("Must be implemented by child classes.")
    
    def get_posts_content(self, posts):
        raise NotImplemented("Must be implemented by child classes.")
        
    def get_position(self, post):
        raise NotImplemented("Must be implemented by child classes.")
        
    def set_min_position_param(self, position):
        raise NotImplemented("Must be implemented by child classes.")
        
    def set_max_position_param(self, position):
        raise NotImplemented("Must be implemented by child classes.")


class TwitterPosts(Posts):
    def __init__(self, *args, **kwargs):
        super(TwitterPosts, self).__init__(*args, **kwargs)
        
        if not self.api:
            self.api = APIS['lastfm']
            
        self.params = {'screen_name': self.uid, 'count': '200'}

    @property
    def request_uri(self):
        return 'statuses/user_timeline.json'
        
    @property
    def max_requests(self):
        return 1400
    
    def get_posts_content(self, posts):
        return posts.content
        
    def get_position(self, post):
        return post['id_str']
        
    def set_min_position_param(self, position):
        self.params['since_id'] = position
        
    def set_max_position_param(self, position):
        self.params['max_id'] = int(position) - 1


class LastfmScrobbles(Posts):
    def __init__(self, *args, **kwargs):
        super(LastfmScrobbles, self).__init__(*args, **kwargs)
        
        if not self.api:
            self.api = APIS['lastfm']
            
        self.params = {'user': self.uid, 'limit': '200', 'format': 'json'}

    @property
    def request_uri(self):
        return '?method=user.getrecenttracks'
        
    @property
    def max_requests(self):
        return 1400

    def get_position(self, post):
        return post['date']['uts']
        
    def set_min_position_param(self, position):
        self.params['from'] = position
        
    def set_max_position_param(self, position):
        self.params['to'] = position

    def get_posts_content(self, posts):
        content = json.loads(posts.content)
        if (content 
        and 'recenttracks' in content 
        and 'track' in content['recenttracks']):
            return content['recenttracks']['track']
        else:
            return None


class GoogleCompletedTasks(Posts):
    def __init__(self, *args, **kwargs):
        super(GoogleCompletedTasks, self).__init__(*args, **kwargs)

        if not self.api:
            self.api = APIS['google_tasks']
        
        self._latest_position = kwargs.get(
            'latest_position', '1900-01-01T00:00:00Z')
        self._tasklist_ids = self.get_tasklist_ids()
        self._tasklist_id = self._tasklist_ids.pop()
        self.params = {'show_hidden': True,
                       'completedMin': self._latest_position}

    @property
    def request_uri(self):
        return 'tasks/v1/lists/%s/tasks' % self._tasklist_id
        
    @property
    def max_requests(self):
        return 35

    def keep_requesting_when_no_posts_returned(self):
        if self._tasklist_ids:
            self._tasklist_id = self._tasklist_ids.pop()
            return True
        else:
            return False
            
    def get_tasklist_ids(self):
        result = self.api.get('tasks/v1/users/@me/lists?maxResults=1000000',
                user = self.user)
        return [task['id'] for task in result.content['items']]

    def position_gt(self, a, b):
        return parsedate_tz(a) > parsedate_tz(b)

    def get_position(self, post):
        return post['completed']
        
    def set_min_position_param(self, position):
        self.params['completedMin'] = position
        
    def set_max_position_param(self, position):
        self.params['completedMax'] = position

    def get_posts_content(self, posts):
        if 'items' in posts.content:
            return posts.content['items']
        else:
            return []
