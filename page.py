'''
Base class for PageObject approach to Selenium testing.
'''
class Page(object):
    def __init__(self, browser):
        self.browser = browser
