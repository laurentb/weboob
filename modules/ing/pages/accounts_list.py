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
                                            Date, Lower, Regexp, Async, AsyncLoad, Slugify
from weboob.browser.filters.html import Attr
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
             u'Direct Vie': Account.TYPE_LIFE_INSURANCE}

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
            return (date.today() - timedelta(days=1))
        elif txt == "aujourd'hui":
            return date.today()
        elif txt == 'demain':
            return (date.today() + timedelta(days=1))
        else:
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
            obj__id = CleanText('span[@class="account-number"]')
            obj_label = CleanText('span[@class="title"]')
            obj_id = AddPref(Field('_id'), Field('label'))
            obj_type = AddType(Field('label'))
            obj_balance = CleanDecimal('span[@class="solde"]/label', replace_dots=True)
            obj_coming = NotAvailable
            obj__jid = Attr('//input[@name="javax.faces.ViewState"]', 'value')

    class generic_transactions(ListElement):
        class item(ItemElement):
            klass = Transaction

            obj_id = None  # will be overwrited by the browser
            # we use lower for compatibility with the old website
            obj_raw = Transaction.Raw(Lower('.//td[@class="lbl"]'))
            obj_amount = CleanDecimal('.//td[starts-with(@class, "amount")]', replace_dots=True)
            obj_date = INGDate(CleanText('.//td[@class="date"]'), dayfirst=True)
            obj_rdate = Field('date')
            obj__hash = PreHashmd5(Field('date'), Field('raw'), Field('amount'))
            obj_category = INGCategory(Attr('.//td[@class="picto"]/span', 'class'))

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
        span = Attr('//span[starts-with(@id, "index:j_id")]', 'id')(self.doc)
        jid = span.split(':')[1]
        return jid

    def islast(self):
        havemore = self.doc.getroot().cssselect('.show-more-transactions')
        if len(havemore) == 0:
            return True

        nomore = self.doc.getroot().cssselect('.no-more-transactions')
        return (len(nomore) > 0)

    @property
    def is_asv(self):
        span = self.doc.xpath('//span[@id="index:panelASV"]')
        return len(span) > 0

    @method
    class iter_investments(ListElement):
        item_xpath = '//div[has-class("asv_fond")]'

        class item(ItemElement):
            klass = Investment

            # ASV.popup('/general?command=displayAVEuroEpargne')
            load_details = Attr('.//div[has-class("asv_fond_view")]//a', 'onclick') & Regexp(pattern="'(.*)'") & AsyncLoad

            obj_label = CleanText('.//span[has-class("asv_cat_lbl")]')
            # XXX I would like to do that... but 1. CleanText doesn't deal with default 2. default values can't be filters yet
            #obj_code = Async('details') & CleanText('//li[contains(text(), "Code ISIN")]/span') | (Field('label') & Format('XX%s', Slugify))
            obj_code = Async('details') & CleanText('//li[contains(text(), "Code ISIN")]/span')
            obj_id = obj_code
            obj_description = Async('details') & CleanText('//h5')
            obj_quantity = CleanDecimal('.//dl[contains(dt/text(), "Nombre de parts")]/dd', replace_dots=True)
            obj_unitvalue = CleanDecimal('.//dl[contains(dt/text(), "Valeur de part")]/dd', replace_dots=True)

            # There are two kind of lists:
            # - Header contains percent and valuation is in a specific row ("ligne-montant")
            # - Header contains valuation, there is no "ligne-montant" row, and percent is in a specific row
            obj_valuation = CleanDecimal('.//dl[has-class("ligne-montant")]/dd | .//dd[@data-show="header" and not(contains(text(), "%"))]', replace_dots=True)

            def obj_unitprice(self):
                if 'eurossima' in self.el.get('class'):
                    return self.obj.unitvalue

                percent = CleanDecimal('.//span[has-class("pmvalue")]', replace_dots=True)(self)
                return (self.obj.unitvalue / (1 + percent/Decimal('100.0'))).quantize(Decimal('1.00'))

            def obj_diff(self):
                return (self.obj.valuation - (self.obj.quantity * self.obj.unitprice)).quantize(Decimal('1.00'))

            def validate(self, obj):
                if not obj.id:
                    obj.id = obj.code = 'XX' + Slugify(self.obj_label)(self)

                return True


class TitreDetails(LoggedPage, HTMLPage):
    pass
