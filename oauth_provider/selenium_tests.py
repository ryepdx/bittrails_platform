'''
Runs Selenium tests.
'''
from . import pages
from selenium_test import SeleniumTest

class SignupTests(SeleniumTest):
    def __init__(self, *args, **kwargs):
        super(SignupTests, self).__init__(*args, **kwargs)
        self.nav_bar = pages.NavBar(self.browser)
        self.login_page = pages.LoginPage(self.browser)
        self.google_page = pages.GooglePage(self.browser)
        self.account_page = pages.AccountPage(self.browser)
        self.new_client_page = pages.NewClientPage(self.browser)
        self.clients_page = pages.ClientsPage(self.browser)
            
    def login(self):
        self.browser.get(self.app_url)
        self.nav_bar.login.click()
        self.login_page.fill_out_login_form().submit_login_form()
        self.google_page.fill_out_auth_form().submit()
        
        try:
            self.login_page.submit_new_profile_form()
        except:
            assert self.nav_bar.active.text == "Overview"
        
    def post_auth(self):
        self.nav_bar.account.click()
        self.test_change_name()
        self.test_change_email()
        
        self.nav_bar.clients.click()
        self.test_create_client()
        #self.test_update_client()
        #self.test_delete_client()
        self.test_logout()
        
    def test_change_name(self):
        name = "Gulag Orkestar"
        self.account_page.name_input.clear()
        self.account_page.name_input.send_keys(name)
        self.account_page.submit_button.click()
        assert self.account_page.name_input.get_attribute("value") == name
        
    def test_change_email(self):
        email = "winston@1984.com"
        self.account_page.email_input.clear()
        self.account_page.email_input.send_keys(email)
        self.account_page.submit_button.click()
        assert self.account_page.email_input.get_attribute("value") == email
        
    def test_create_client(self):
        name = "Some app"
        description = "That's some app!"
        callback = "http://callmeback/"
        
        # Create a client.
        self.new_client_page.name_input.send_keys(name)
        self.new_client_page.description_input.send_keys(description)
        self.new_client_page.callback_input.send_keys(callback)
        self.new_client_page.submit_button.click()
        
        # Check the "client created" page for our client's information.
        assert self.browser.find_element_by_xpath(
            '//td[contains(text(), "%s")]' % name)
        assert self.browser.find_element_by_xpath(
            '//td[contains(text(), "%s")]' % description)
        assert self.browser.find_element_by_xpath(
            '//td[contains(text(), "%s")]' % callback)
        
        # Load clients page and check.
        self.nav_bar.clients.click()
        assert self.clients_page.find_client_name(name)

    def test_logout(self):
        self.nav_bar.logout.click()
        assert self.nav_bar.active.text == "Overview"
        assert self.nav_bar.login
