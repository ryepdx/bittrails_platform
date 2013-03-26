import page

class LoginPage(page.Page):
    def fill_out_login_form(self):
        self.browser.find_element_by_xpath(
            '//input[@type="text" and @name="openid"]').send_keys(
            'https://www.google.com/accounts/o8/id')
        return self
        
    def submit_login_form(self):
        self.browser.find_element_by_xpath(
            '//button[@type="submit"]').click()
            
    def submit_new_profile_form(self):
        self.browser.find_element_by_xpath(
            '//input[@type="submit"]').click()
            

class GooglePage(page.Page):
    def fill_out_auth_form(self):
        email = self.browser.find_element_by_id('Email')
        password = self.browser.find_element_by_id('Passwd')
        
        email.click()
        email.send_keys('bittrails.testuser')
        password.click()
        password.send_keys('b1ttr41ls!!1!')
        
        return self
        
    def submit(self):
        self.browser.find_element_by_id('signIn').click()
        try:
            self.browser.find_element_by_xpath(
                '//button[@id="approve_button" and not(@disabled)]').click()
        except:
            # Giving this one a pass since Google only asks for confirmation
            # the first time a test account signs in.
            pass
    
        
class NavBar(page.Page):
    @property
    def login(self):
        return self.browser.find_element_by_xpath('//a[@href="/login"]')
        
    @property
    def active(self):
        return self.browser.find_element_by_xpath(
            '//nav//li[@class="active"]//a')
    
    @property
    def login(self):
        return self.browser.find_element_by_xpath(
            '//nav//a[contains(text(), "sign in")]')
            
    @property
    def account(self):
        return self.browser.find_element_by_xpath(
            '//nav//a[contains(text(), "Account")]')
            
    @property
    def clients(self):
        return self.browser.find_element_by_xpath(
            '//nav//a[contains(text(), "Clients")]')
            
    @property
    def logout(self):
        return self.browser.find_element_by_xpath('//a[@href="/logout"]')

class AccountPage(page.Page):
    @property
    def name_input(self):
        return self.browser.find_element_by_xpath(
                '//input[@type="text" and @name="name"]')
                
    @property
    def email_input(self):
        return self.browser.find_element_by_xpath(
                '//input[@type="text" and @name="email"]')

    @property
    def submit_button(self):
        return self.browser.find_element_by_xpath('//button[@type="submit"]')


class NewClientPage(page.Page):
    @property
    def name_input(self):
        return self.browser.find_element_by_xpath(
                '//input[@type="text" and @name="name"]')
                
    @property
    def description_input(self):
        return self.browser.find_element_by_xpath(
                '//input[@type="text" and @name="description"]')            
    
    @property
    def callback_input(self):
        return self.browser.find_element_by_xpath(
                '//input[@type="text" and @name="callback"]')

    @property
    def submit_button(self):
        return self.browser.find_element_by_xpath('//button[@type="submit"]')


class ClientsPage(page.Page):
    def find_client_name(self, name):
        return self.browser.find_element_by_xpath(
            '//span[@class="name" and contains(text(), "%s")]' % name)
