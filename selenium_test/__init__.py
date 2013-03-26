'''
Base class for all Selenium tests.
'''
class SeleniumTest(object):
    def __init__(self, browser, wait, app_url):
        self.browser = browser
        self.wait = wait
        self.app_url = app_url
