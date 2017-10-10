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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, CaptchaQuestion, AuthMethodNotImplemented

from .pages import LoginPage, SubscriptionsPage, DocumentsPage, HomePage, PanelPage, SecurityPage, LanguagePage


class AmazonBrowser(LoginBrowser):
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

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['email'].get()
        kwargs['password'] = self.config['password'].get()
        super(AmazonBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.to_english(self.LANGUAGE)
        if not self.login.is_here():
            self.location(self.home.go().get_login_link())
            self.page.login(self.username, self.password)
        elif self.config['captcha_response'].get():
            self.page.login(self.username, self.password, self.config['captcha_response'].get())

        if self.security.is_here():
            raise AuthMethodNotImplemented("It looks like double authentication is activated for your account. Please desactivate it before retrying connection.")

        if not self.login.is_here():
            return

        captcha = self.page.has_captcha()
        if captcha and not self.config['captcha_response'].get():
            raise CaptchaQuestion('image_captcha', image_url=captcha[0])
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
