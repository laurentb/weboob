# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import Bill, Subscription
from weboob.capabilities.profile import Profile
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import parse_french_date


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(id='log_form')
        form['login'] = login
        form['pass'] = password

        form.submit()


class HomePage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = Env('subscriber')
            obj_id = Env('subid')
            obj_label = obj_id

            def parse(self, el):
                username = self.page.browser.username
                try:
                    subscriber = CleanText(u'//div[@class="infos_abonne"]/ul/li[1]')(self)
                except UnicodeDecodeError:
                    subscriber = username
                self.env['subscriber'] = subscriber
                self.env['subid'] = username


class DocumentsPage(LoggedPage, HTMLPage):
    ENCODING = "latin1"

    def get_list(self):
        sub = Subscription()

        sub.subscriber = self.browser.username
        sub.id = sub.subscriber
        sub.label = sub.subscriber

        yield sub

    @method
    class get_documents(ListElement):
        item_xpath = "//ul[@class='pane']/li"

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Regexp(Attr('./span[1]/a', 'href'), '(?<=.facture=)([^*]+)'))
            obj_url = Attr('./span[1]/a', 'href', default=NotAvailable)
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_label = Format('Facture %s', CleanText('./span[1]/strong'))
            obj_type = u"bill"
            obj_price = CleanDecimal(CleanText('./span[has-class("last")]'), replace_dots=True)
            obj_currency = u"EUR"

            def parse(self, el):
                self.env['date'] = parse_french_date(u"01 %s" % CleanText('./span[2]')(self)).date()


class ProfilePage(LoggedPage, HTMLPage):
    def get_profile(self, subscriber):
        p = Profile()
        p.name = subscriber
        p.email = CleanText('//input[@name="email"]/@value')(self.doc) or NotAvailable
        p.phone = CleanText('//input[@name="portable"]/@value')(self.doc) or NotAvailable

        return p

    def set_address(self, profile):
        assert len(self.doc.xpath('//p/strong[contains(text(), " ")]')) == 1, 'There are several addresses.'
        profile.address = CleanText('//p/strong[contains(text(), " ")]')(self.doc) or NotAvailable
