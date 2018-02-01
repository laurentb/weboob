# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from datetime import date

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, CaptchaQuestion, BrowserQuestion
from weboob.tools.value import Value
from weboob.browser.browsers import ClientError

from .pages import LoginPage, SubscriptionsPage, DocumentsPage, HomePage, PanelPage, SecurityPage, LanguagePage, HistoryPage


class AmazonBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://www.amazon.fr'
    CURRENCY = 'EUR'
    LANGUAGE = 'fr-FR'

    L_SIGNIN = 'Identifiez-vous'
    L_LOGIN = 'Connexion'
    L_SUBSCRIBER = 'Nom : (.*) Modifier E-mail'

    login = URL(r'/ap/signin(.*)', LoginPage)
    home = URL(r'/$', HomePage)
    panel = URL('/gp/css/homepage.html/ref=nav_youraccount_ya', PanelPage)
    subscriptions = URL(r'/ap/cnep(.*)', SubscriptionsPage)
    documents = URL(r'/gp/your-account/order-history\?opt=ab&digitalOrders=1(.*)&orderFilter=year-(?P<year>.*)', DocumentsPage)
    security = URL('/ap/dcq',
                   '/ap/cvf/',
                   '/ap/mfa',
                   SecurityPage)
    language = URL(r'/gp/customer-preferences/save-settings/ref=icp_lop_(?P<language>.*)_tn', LanguagePage)
    history = URL('https://www.amazon.fr/gp/your-account/order-history\?ref_=ya_d_c_yo', HistoryPage)

    __states__ = ('otp_form', 'otp_url')

    STATE_DURATION = 10

    otp_form = None
    otp_url = None

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['email'].get()
        kwargs['password'] = self.config['password'].get()
        super(AmazonBrowser, self).__init__(*args, **kwargs)

    def locate_browser(self, state):
        pass

    def push_captcha_otp(self, captcha):
        res_form = self.otp_form
        res_form['email'] = self.username
        res_form['password'] = self.password
        res_form['guess'] = captcha

        self.location(self.otp_url, data=res_form)

    def push_security_otp(self, pin_code):
        res_form = self.otp_form
        res_form['code'] = pin_code
        res_form['otpCode'] = pin_code
        res_form['rememberDevice'] = ""

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://www.amazon.fr/ap/cvf/verify',
            'upgrade-insecure-requests': '1'
        }
        self.location(self.otp_url, data=res_form, headers=headers)

    def handle_security(self):
        if self.page.doc.xpath('//span[@class="a-button-text"]'):
            self.page.send_code()
            self.otp_form = self.page.get_response_form()
            self.otp_url = self.url

            raise BrowserQuestion(Value('pin_code', label=self.page.get_otp_message() if self.page.get_otp_message() else 'Please type the OTP you received'))

    def handle_captcha(self, captcha):
        self.otp_form = self.page.get_response_form()
        self.otp_url = self.url
        raise CaptchaQuestion('image_captcha', image_url=captcha[0])

    def do_login(self):
        if self.config['pin_code'].get():
            # Resolve pin_code
            self.push_security_otp(self.config['pin_code'].get())

            if self.security.is_here() or self.login.is_here():
                # Something went wrong, probably a wrong OTP code
                raise BrowserIncorrectPassword('OTP incorrect')
            else:
                # Means security was passed, we're logged
                return

        if self.config['captcha_response'].get():
            # Resolve captcha code
            self.page.login(self.username, self.password, self.config['captcha_response'].get())

            if self.security.is_here():
                # Raise security management
                self.handle_security()

            if self.login.is_here():
                raise BrowserIncorrectPassword()
            else:
                return

        # Change language so everything is handled the same way
        self.to_english(self.LANGUAGE)

        # To see if we're connected. If not, we land on LoginPage
        try:
            self.history.go()
        except ClientError:
            pass


        if not self.login.is_here():
            return

        self.page.login(self.username, self.password)

        if self.security.is_here():
            # Raise security management
            self.handle_security()

        if self.login.is_here():
            captcha = self.page.has_captcha()
            if captcha and not self.config['captcha_response'].get():
                self.handle_captcha(captcha)
            else:
                raise BrowserIncorrectPassword()

    def is_login(self):
        if self.login.is_here():
            self.do_login()
        else:
            raise BrowserUnavailable()

    def to_english(self, language):
        # We put language in english
        datas = {
            '_url': '/?language=' + language.replace('-', '_'),
            'LOP': language.replace('-', '_'),
        }
        self.language.go(method='POST', data=datas, language=language)

    @need_login
    def iter_subscription(self):
        self.location(self.panel.go().get_sub_link())

        if not self.subscriptions.is_here():
            self.is_login()

        yield self.page.get_item()

    @need_login
    def iter_documents(self, subscription):
        documents = []

        for y in range(date.today().year - 2, date.today().year + 1):
            for doc in self.documents.go(year=y).iter_documents(subid=subscription.id, currency=self.CURRENCY):
                documents.append(doc)
        return documents
