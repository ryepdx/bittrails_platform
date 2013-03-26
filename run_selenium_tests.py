'''
Runs Selenium tests against the specified host and port.
'''
import argparse
import collections
import inspect
import traceback
#import pyvirtualdisplay
import selenium.webdriver.support.ui

import oauth_provider.selenium_tests

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium_test import SeleniumTest

test_levels = ["pre_auth", "login", "auth", "post_auth"]
test_modules = [
    oauth_provider.selenium_tests
]

ENDC = '\033[0m'
PASS = '\033[92mPASS'+ENDC
FAIL = '\033[91mFAIL'+ENDC
Test = collections.namedtuple('Test', ['module', 'obj'])

def get_args():
    parser = argparse.ArgumentParser(description='Run Selenium tests.')
    parser.add_argument('--port', '-dp', action='store', dest='port', type=int,
        default=5000, help='the port the web app is running on')
    parser.add_argument('--host', '-dh', action='store', dest='host', type=str,
        default='localhost', help='the hostname the web app is running on')
    parser.add_argument('--web-driver', '-wd', action='store',
        dest='webdriver_url', type=str, default='',
        help='run tests using the remote WebDriver server at the given URL')
    parser.add_argument('--browser', '-b', action='store', dest='browser',
        type=str, default='chrome', help='run tests on the given browser')
    parser.add_argument('--browser-binary', '-bb', action='store',
        dest='browser_binary', type=str, default=None,
        help='specify the path to the browser executable you want to use')
    # Headless mode does not work at the moment. For some reason Selenium
    # throws an exception when trying to click nav bar elements.
    #parser.add_argument('--headless', '-hdls', action='store_const',
        #dest='headless', const=True, default=False,
        #help='run the tests without showing the browser')
    parser.add_argument('--timeout', '-t', action='store', dest='timeout',
        type=int, default=10, help='seconds to wait for browser before failing')

    return parser.parse_args()

args = get_args()

# Give me some whitespace.
print

# Start a hidden virtual display if the user decided to run the tests with
# a hidden browser.
#if args.headless:
#    display = pyvirtualdisplay.Display(visible=0, size=(800, 600))
#    display.start()

# Set up Selenium.
if args.webdriver_url == '':
    browser = getattr(webdriver, args.browser.lower().title())(
        args.browser_binary)
else:
    browser = webdriver.Remote(command_executor=args.webdriver_url,
        desired_capabilities=getattr(DesiredCapabilities, args.browser.upper()))

browser.implicitly_wait(args.timeout)        
wait = selenium.webdriver.support.ui.WebDriverWait(browser, args.timeout)

# Create list of tests
tests = []
for module in test_modules:
    tests += [Test(module, cls(browser, wait, args.host + ':' + str(args.port)
        )) for name, cls in inspect.getmembers(module) if inspect.isclass(cls
        ) and issubclass(cls, SeleniumTest) and cls != SeleniumTest ]

# Run all tests.
for level in test_levels:
    for test in tests:
        if hasattr(test.obj, level):
            try:
                getattr(test.obj, level)()
                result = PASS
                
            except Exception:
                traceback.print_exc()
                result = FAIL
            
            print "%s %s.%s.%s" % (result, test.module.__name__,
                test.obj.__class__.__name__, level)
            
browser.close()

# Stop the virtual display if the user decided to run the tests with
# a hidden browser.
#if args.headless:
#    display.stop()

# Give me some whitespace.
print

