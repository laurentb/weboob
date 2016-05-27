# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot, Romain Bignon
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


from datetime import date, timedelta
import datetime
from decimal import Decimal
import re

from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Filter, Field, MultiFilter, \
                                            Date, Lower, Regexp, Async, AsyncLoad, Format
from weboob.browser.filters.html import Attr, Link
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_CARD),
                (re.compile(u'^virement (sepa )?(emis vers|recu|emis)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^cheque (?P<text>.*)'), FrenchTransaction.TYPE_CHECK),
                (re.compile(u'^prelevement (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^prlv sepa (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^prélèvement sepa en faveur de (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                ]


class AddPref(MultiFilter):
    prefixes = {u'Courant': u'CC-', u'Livret A': 'LA-', u'Orange': 'LEO-',
                u'Durable': u'LDD-', u"Titres": 'TITRE-', u'PEA': u'PEA-'}

    def filter(self, values):
        el, label = values
        for key, pref in self.prefixes.items():
            if key in label:
                return pref + el
        return el


class AddType(Filter):
    types = {u'Courant': Account.TYPE_CHECKING, u'Livret A': Account.TYPE_SAVINGS,
             u'Orange': Account.TYPE_SAVINGS, u'Durable': Account.TYPE_SAVINGS,
             u'Titres': Account.TYPE_MARKET, u'PEA': Account.TYPE_MARKET,
             u'Direct Vie': Account.TYPE_LIFE_INSURANCE,
             u'Assurance Vie': Account.TYPE_LIFE_INSURANCE
            }

    def filter(self, label):
        for key, acc_type in self.types.items():
            if key in label:
                return acc_type
        return Account.TYPE_UNKNOWN


class PreHashmd5(MultiFilter):
    def filter(self, values):
        concat = ''
        for value in values:
            if type(value) is datetime.date:
                concat += value.strftime('%d/%m/%Y')
            else:
                concat += u'%s' % value
        return concat.encode('utf-8')


class INGDate(Date):
    monthvalue = {u'janv.': '01', u'févr.': '02', u'mars': '03', u'avr.': '04',
                  u'mai': '05', u'juin': '06', u'juil.': '07', u'août': '08',
                  u'sept.': '09', u'oct.': '10', u'nov.': '11', u'déc.': '12'}

    def filter(self, txt):
        if txt == 'hier':
            return date.today() - timedelta(days=1)
        elif txt == "aujourd'hui":
            return date.today()
        elif txt == 'demain':
            return date.today() + timedelta(days=1)

        frenchmonth = txt.split(' ')[1]
        month = self.monthvalue[frenchmonth]
        txt = txt.replace(' ', '')
        txt = txt.replace(frenchmonth, '/%s/' % month)
        return super(INGDate, self).filter(txt)


class INGCategory(Filter):
    catvalue = {u'virt': u"Virement", u'autre': u"Autre",
                u'plvt': u'Prélèvement', u'cb_ret': u"Carte retrait",
                u'cb_ach': u'Carte achat', u'chq': u'Chèque',
                u'frais': u'Frais bancaire', u'sepaplvt': u'Prélèvement'}

    def filter(self, txt):
        txt = txt.split('-')[0].lower()
        try:
            return self.catvalue[txt]
        except:
            return txt


class AccountsList(LoggedPage, HTMLPage):
    i = 0

    def has_error(self):
        return len(self.doc.xpath('//div[has-class("alert-warning")]')) > 0

    @method
    class get_list(ListElement):
        item_xpath = '//a[@class="mainclic"]'

        class item(ItemElement):
            klass = Account

            obj_currency = u'EUR'
            obj_label = CleanText('span[@class="title"]')
            obj_id = AddPref(Field('_id'), Field('label'))
            obj_type = AddType(Field('label'))
            obj_balance = CleanDecimal('span[@class="solde"]/label', replace_dots=True)
            obj_coming = NotAvailable
            obj__jid = Attr('//input[@name="javax.faces.ViewState"]', 'value')

            def obj__id(self):
                return CleanText('span[@class="account-number"]')(self) or CleanText('span[@class="life-insurance-application"]')(self)

    class generic_transactions(ListElement):
        class item(ItemElement):
            klass = Transaction

            obj_id = None  # will be overwrited by the browser
            # we use lower for compatibility with the old website
            obj_amount = CleanDecimal('.//td[starts-with(@class, "amount")]', replace_dots=True)
            obj_date = INGDate(CleanText('.//td[@class="date"]'), dayfirst=True)
            obj_rdate = Field('date')
            obj__hash = PreHashmd5(Field('date'), Field('raw'), Field('amount'))
            obj_category = INGCategory(Attr('.//td[@class="picto"]/span', 'class'))

            def obj_raw(self):
                return Transaction.Raw(Lower('.//td[@class="lbl"]'))(self) or Format('%s %s', Field('date'), Field('amount'))(self)

            def condition(self):
                if self.el.find('.//td[@class="date"]') is None:
                    return False
                if 'index' in self.env and self.env['index'] > 0 and self.page.i < self.env['index']:
                    self.page.i += 1
                    return False
                return True

    @method
    class get_coming(generic_transactions):
        item_xpath = '//div[@class="transactions cc future"]//table'

    @method
    class get_transactions_cc(generic_transactions):
        item_xpath = '//div[@class="temporaryTransactionList"]//table'

    @method
    class get_transactions_others(generic_transactions):
        item_xpath = '//table'

    def get_history_jid(self):
        span = Attr('//*[starts-with(@id, "index:j_id")]', 'id')(self.doc)
        jid = span.split(':')[1]
        return jid

    def islast(self):
        havemore = self.doc.getroot().cssselect('.show-more-transactions')
        if len(havemore) == 0:
            return True

        nomore = self.doc.getroot().cssselect('.no-more-transactions')
        return len(nomore) > 0

    @property
    def is_asv(self):
        span = self.doc.xpath('//span[@id="index:panelASV"]')
        return len(span) > 0

    @property
    def asv_has_transactions(self):
        span = self.doc.xpath('//a[@id="index:asvInclude:goToAsvPartner"]')
        return len(span) > 0

    def go_on_asv_history(self):
        data = {}
        data['index:j_idcl'] = 'index:asvInclude:goToAsvPartner'
        data['index'] = 'index'
        self.browser.open('https://secure.ingdirect.fr/protected/pages/index.jsf', data=data, headers={'Content-Type':'application/x-www-form-urlencoded'})

    def submit(self):
        form = self.get_form()
        form.submit()


class TitreDetails(LoggedPage, HTMLPage):
    def submit(self):
        form = self.get_form()
        form.submit()


class LifeInsurancePage(LoggedPage,HTMLPage):
    @method
    class iter_investments(ListElement):
        item_xpath = '//table[@class="Tableau"]//tr[position()>2]'

        class item(ItemElement):
            klass = Investment
            load_details = Link('.//td[1]//a')  & AsyncLoad

            def obj_code(self):
                val=(Async('details') & CleanText('//td[@class="libelle-normal" and contains(.,"CodeISIN")]'))(self)
                if val:
                    return val.split('CodeISIN : ')[1]
                return NotAvailable

            obj_label = CleanText('.//td[1]')
            obj_vdate = Date(CleanText('.//td[2]'),dayfirst=True)
            obj_unitvalue = CleanDecimal('.//td[3]',replace_dots=True,default=NotAvailable)
            obj_quantity = CleanDecimal('.//td[4]',replace_dots=True,default=NotAvailable)
            obj_valuation = CleanDecimal('.//td[5]',replace_dots=True)
            obj_unitprice = CleanDecimal('.//td[6]',replace_dots=True,default=NotAvailable)
            obj_diff = CleanDecimal('.//td[7]',replace_dots=True,default=NotAvailable)
    @property
    def asv_has_transactions(self):
        span = self.doc.xpath('//a[contains(.,"Liste des mouvement")]')
        return len(span) > 0



class DetailFondsPage(LoggedPage,HTMLPage):
    pass
