# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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

from urlparse import urlparse, parse_qs
import re

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

from weboob.tools.browser import  BrowserIncorrectPassword
from weboob.tools.browser2.page import HTMLPage, method, ListElement, ItemElement, SkipItem, LoggedPage, pagination
from weboob.tools.browser2.filters import Filter, Env, CleanText, CleanDecimal, Link, Field, DateGuesser, TableCell


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^CB (?P<text>.*)\s+(?P<dd>\d+)/(?P<mm>\d+)\s*(?P<loc>.*)'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile(r'^DAB (?P<dd>\d{2})/(?P<mm>\d{2}) ((?P<HH>\d{2})H(?P<MM>\d{2}) )?(?P<text>.*?)( CB N°.*)?$'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CHEQUE$'),                  FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^COTIS\.? (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile(r'^REMISE (?P<text>.*)'),      FrenchTransaction.TYPE_DEPOSIT),
               ]

class AccountsPage(LoggedPage, HTMLPage):
    def get_frame(self):
        try:
            a = self.doc.xpath(u'//frame["@name=FrameWork"]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['src']

    @method
    class iter_accounts(ListElement):
        item_xpath = '//tr'
        flush_at_end = True

        class item(ItemElement):
            klass = Account

            def condition(self):
                return len(self.el.xpath('./td')) > 2

            class Label(Filter):
                def filter(self, text):
                    return text.lstrip(' 0123456789').title()

            class Type(Filter):
                def filter(self, label):
                    return Account.TYPE_UNKNOWN

            obj_id = Env('id')
            obj_label = Label(CleanText('./td[1]/a'))
            obj_coming = Env('coming')
            obj_balance = Env('balance')
            obj_currency = FrenchTransaction.Currency('./td[2] | ./td[3]')
            obj__link_id = Link('./td[1]/a')
            obj_type = Type(Field('label'))

            def parse(self, el):
                link = el.xpath('./td[1]/a')[0].get('href', '')
                url = urlparse(link)
                p = parse_qs(url.query)

                if 'CPT_IdPrestation' in p:
                    id = p['CPT_IdPrestation'][0]
                elif 'Ass_IdPrestation' in p:
                    id = p['Ass_IdPrestation'][0]
                elif 'CB_IdPrestation' in p:
                    id = p['CB_IdPrestation'][0]
                else:
                    raise SkipItem()

                balance = CleanDecimal('./td[3]')(self)

                self.env['id'] = id
                self.env['balance'] = balance
                self.env['coming'] = NotAvailable


class Pagination(object):
    def next_page(self):
        links = self.page.doc.xpath('//a[@class="fleche"]')
        if len(links) == 0:
            return
        current_page_found= False
        for link in links:
            l = link.attrib.get('href')
            if current_page_found and "#op" not in l:
                #Adding CB_IdPrestation so browser2 use CBOperationPage
                return l + "&CB_IdPrestation"
            elif "#op" in l:
                current_page_found = True
        return


class CBOperationPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table//tr/th'
        item_xpath = '//table//tr'

        class item(Transaction.TransactionElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 4

            obj_date = DateGuesser(CleanText(TableCell("date")), Env("date_guesser"))
            obj_vdate = DateGuesser(CleanText(TableCell("date")), Env("date_guesser"))

class CPTOperationPage(LoggedPage, HTMLPage):
    def get_history(self):
        for script in self.doc.xpath('//script'):
            if script.text is None or script.text.find('\nCL(0') < 0:
                continue

            for m in re.finditer(r"CL\((\d+),'(.+)','(.+)','(.+)','([\d -\.,]+)',('([\d -\.,]+)',)?'\d+','\d+','[\w\s]+'\);", script.text, flags=re.MULTILINE):
                op = Transaction(m.group(1))
                op.parse(date=m.group(3), raw=re.sub(u'[ ]+', u' ', m.group(4).replace(u'\n', u' ')))
                op.set_amount(m.group(5))
                op._coming = (re.match(r'\d+/\d+/\d+', m.group(2)) is None)
                yield op

class LoginPage(HTMLPage):
    def on_load(self):
        for message in self.doc.getroot().cssselect('div.csPanelErrors, div.csPanelAlert'):
            raise BrowserIncorrectPassword(CleanText('.')(message))

    def login(self, login):
        form = self.get_form(nr=2)
        form['userid'] = login
        form.submit()

    def get_no_secure_key(self):
        try:
            a = self.doc.xpath(u'//a[contains(text(), "Without HSBC Secure Key")]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['href']

    def login_w_secure(self, password, secret):
        form = self.get_form(nr=0)
        form['memorableAnswer'] = secret
        inputs = self.doc.xpath(u'//input[starts-with(@id, "keyrcc_password_first")]')
        split_pass = u''
        if len(password) != len(inputs):
            raise BrowserIncorrectPassword('Your password must be %d chars long' % len(inputs))

        for i, inpu in enumerate(inputs):
            #The good field are 1,2,3 and the bad one are 11,12,21,23,24,31 and so one
            if int(inpu.attrib['id'].split('first')[1]) < 10:
                split_pass += password[i]
        form['password'] = split_pass
        form.submit()

    def useless_form(self):
        form = self.get_form(nr=0)
        form.submit()
