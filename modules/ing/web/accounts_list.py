# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot, Romain Bignon
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

from __future__ import unicode_literals

from datetime import date, timedelta
import datetime
import re

from weboob.capabilities.bank import Account, Investment, Loan
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.profile import Person
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.browser.elements import ListElement, TableElement, ItemElement, method, DataError
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Eval, Filter, Field, MultiFilter, Date,
    Lower, Async, AsyncLoad, Format, Env,
    Regexp,
)
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                # Withdrawal in foreign currencies will look like "retrait 123 currency"
                (re.compile(u'^retrait (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_CARD),
                (re.compile(u'^virement (sepa )?(emis vers|recu|emis)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^remise cheque(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^cheque (?P<text>.*)'), FrenchTransaction.TYPE_CHECK),
                (re.compile(u'^prelevement (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^prlv sepa (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^prélèvement sepa en faveur de (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^commission sur (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
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
    types = {u'Courant': Account.TYPE_CHECKING,
             u'Livret A': Account.TYPE_SAVINGS,
             u'Orange': Account.TYPE_SAVINGS,
             u'Durable': Account.TYPE_SAVINGS,
             u'Titres': Account.TYPE_MARKET,
             u'PEA': Account.TYPE_PEA,
             u'Direct Vie': Account.TYPE_LIFE_INSURANCE,
             u'Assurance Vie': Account.TYPE_LIFE_INSURANCE,
             u'Crédit Immobilier': Account.TYPE_LOAN,
             u'Prêt Personnel': Account.TYPE_LOAN,
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

    def has_link(self):
        return len(self.doc.xpath('//a[contains(@href, "goTo")]'))

    def get_card_list(self):
        card_list = []
        card_elements = self.doc.xpath('//div[has-class("ccinc_cards")]/div[has-class("accordion")]')
        for card in card_elements:
            card_properties = {}

            # Regexp parse the text to extract the card number that may be in different formats
            card_properties['number'] = Regexp(CleanText('.'), '(\d+[\s|*]+\d+)', default=NotAvailable)(card)
            debit_info = (CleanText('.//div[@class="debit-info"]', default='')(card))

            is_deferred = u'Débit différé' in debit_info
            is_immediate = u'Débit immédiat' in debit_info

            if is_immediate:
                card_properties['kind'] = self.browser.IMMEDIATE_CB
            elif is_deferred:
                card_properties['kind'] = self.browser.DEFERRED_CB
            else:
                raise DataError("Cannot tell if the card {} is deferred or immediate".format(card_properties['number']))

            card_list.append(card_properties)

        return card_list

    @method
    class get_list(ListElement):
        item_xpath = '//div[@id="bloc-menu-comptes"]//a[@class="mainclic"]'

        class item(ItemElement):
            klass = Account

            obj_currency = u'EUR'
            obj_label = CleanText('./span[@class="title"]')
            obj_id = AddPref(Field('_id'), Field('label'))
            obj_type = AddType(Field('label'))
            obj__jid = Attr('//input[@name="javax.faces.ViewState"]', 'value')

            def obj_balance(self):
                balance = CleanDecimal('./span[@class="solde"]/label', replace_dots=True)(self)
                return -abs(balance) if Field('type')(self) == Account.TYPE_LOAN else balance

            def obj__id(self):
                return CleanText('./span[@class="account-number"]')(self) or CleanText('./span[@class="life-insurance-application"]')(self)

    @method
    class get_detailed_loans(ListElement):
        item_xpath = '//div[@class="mainclic"]'

        class item(ItemElement):
            klass = Loan

            obj_currency = u'EUR'
            obj_label = CleanText('.//span[@class="title"]')
            obj_id = AddPref(Field('_id'), Field('label'))
            obj_type = AddType(Field('label'))
            obj__jid = Attr('//input[@name="javax.faces.ViewState"]', 'value')
            obj__id = CleanText('.//span[@class="account-number"]')

            def obj_balance(self):
                balance = CleanDecimal('.//div/span[@class="solde"]/label', replace_dots=True)(self)
                return -abs(balance)

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
                date_field = self.el.find('.//td[@class="date"]')
                if date_field is None or 'À venir' in CleanText().filter(date_field):
                    return False
                if 'index' in self.env and self.env['index'] > 0 and self.page.i < self.env['index']:
                    self.page.i += 1
                    return False
                return True

    @method
    class iter_asv_investments(ListElement):
        item_xpath = '//div[@id="index:accountdetail"]//div[has-class("asv_fond")]'

        class item(ItemElement):
            klass = Investment

            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal('.//dl[@class="ligne-repartition"]/dd', replace_dots=True))
            obj_label = CleanText('.//span[@class="asv_cat_lbl"]')

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

    def get_asv_jid(self):
        return self.doc.xpath('//input[@id="javax.faces.ViewState"]/@value')[0]

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
    def asv_has_detail(self):
        ap = self.doc.xpath('//a[@id="index:asvInclude:goToAsvPartner"] | //p[contains(text(), "Gestion Libre")]')
        return len(ap) > 0

    @property
    def asv_is_other(self):
        a = self.doc.xpath('//a[@id="index:asvInclude:goToAsvPartner"]')
        return len(a) > 0

    def submit(self):
        form = self.get_form(name="follow_link")
        form['follow_link:j_idcl'] = "follow_link:goToAsvPartner"
        form.submit()

    def get_multispace(self):
        multispace = []

        for a in self.doc.xpath('//a[contains(@id, "mainMenu")]'):
            space = {}
            name = CleanText('.')(a)
            if 'Vos comptes' not in name:
                space['name'] = name
            else:
                space['name'] = CleanText('//div[@class="print-content"]/h1')(a)

            space['id'] = Regexp(Attr('.', 'id'), r'mainMenu:(.*)')(a)
            space['form'] = Attr('.', 'onclick')(a)
            space['is_active'] = 'active' in CleanText('./@class')(a)

            multispace.append(space)

        return multispace

    def fillup_form(self, form, regexp, string):
        # fill form depending on JS
        link = re.search(regexp, string).group(1)
        parts = link.split(',')
        for p in parts:
            f = p.split("':'")
            form[f[0].replace("'", '')] = f[1].replace("'", '')

    def change_space(self, space):
        form = self.get_form(id='mainMenu')
        self.fillup_form(form, r"':\{(.*)\}\s\}", space['form'])
        form['AJAXREQUEST'] = '_viewRoot'
        form.submit()

    def load_space_page(self):
        # The accounts page exists in two forms: with the spaces list and without
        # When having the spaceless page, a form must be submit to access the space page
        form = self.get_form(id='header-menu')
        on_click = Attr('//a[@class="home"]', 'onclick')(self.doc)
        self.fillup_form(form, r"\),\{(.*)\},'", on_click)
        form.submit()

    def is_multispace_page(self):
        return self.doc.xpath('//a[contains(@name, "mainMenu")]')


class IbanPage(LoggedPage, HTMLPage):
    def get_iban(self):
        iban = CleanText('//tr[td[1]//text()="IBAN"]/td[2]')(self.doc).strip().replace(' ', '')
        if not iban or 'null' in iban:
            return NotAvailable
        return iban


class LoanTokenPage(LoggedPage, HTMLPage):
    def on_load(self):
        form = self.get_form()
        form.submit()


class LoanDetailPage(LoggedPage, JsonPage):
    def getdetails(self, loan):
        loan.total_amount = CleanDecimal(Dict('amount'))(self.doc)
        loan.maturity_date = Date(Dict('loanEndDate'))(self.doc)
        loan.duration = Dict('loanDuration')(self.doc)
        loan.rate = CleanDecimal(Dict('variableInterestRate'))(self.doc) / 100
        loan.nb_payments_left = Dict('remainingMonth')(self.doc)
        loan.last_payment_date = Date(Dict('lastRefundDate'))(self.doc)
        loan.next_payment_date = Date(Dict('nextRefundDate'))(self.doc)
        loan.next_payment_amount = CleanDecimal(Dict('monthlyRefund'))(self.doc)


class TitreDetails(LoggedPage, HTMLPage):
    def submit(self):
        form = self.get_form()
        form.submit()


class ASVInvest(LoggedPage, HTMLPage):
    @method
    class iter_investments(TableElement):
        # Ignore the first line:
        # <tr>
        #     <td colspan="5" class="enteteTableau metaEnteteTableau enteteTableauFirstCol metaEnteteTableauFirstCol">R&eacute;partition de
        #         l'investissement
        #     </td>
        #     <td colspan="3" class="enteteTableau metaEnteteTableau enteteTableauFirstCol metaEnteteTableauFirstCol">
        #         Plus/moins-values&nbsp;(**)
        #     </td>
        # </tr>
        # Then, there is the line of column heads.
        # Ignore also information lines like that:
        # <tr>
        #       <td colspan="8" class="liTableau" align="left">Gestion Pilotée
        #       <td>
        # </tr>
        item_xpath = '//table[@class="Tableau"]//tr[position()>2 and count(./td) >= 8]'
        head_xpath = '//table[@class="Tableau"]//tr[position()=2]/td'

        col_label = u'Support(s)'
        col_vdate = re.compile('Date')
        col_unitvalue = u'Valeur de part'
        col_quantity = u'Nombre de parts'
        col_valuation = u'Contre-valeur'
        col_unitprice = [u'Prix revient', u'PAM']
        col_diff = u'Montant'
        col_diff_percent = u'%'

        class item(ItemElement):
            klass = Investment

            # Euro funds links are like that:
            # <td class="lpTableau lpTableauFirstCol"><a href="javascript:alert('Les performances de ce fond ne sont pas consultables.')" onclick="">Eurossima
            # </a></td>
            # So ignore them.
            load_details = Link('.//td[1]//a') & Regexp(pattern='^((?!javascript:).*)', default=NotAvailable) & AsyncLoad

            def obj_code(self):
                val = Async('details', CleanText('//td[@class="libelle-normal" and contains(.,"CodeISIN")]', default=NotAvailable))(self)
                if val:
                    return val.split('CodeISIN : ')[1] if val else val
                else:
                    return NotAvailable

            def obj_diff_percent(self):
                diff = CleanDecimal(TableCell('diff_percent'), replace_dots=True, default=NotAvailable)(self)
                if not diff:
                    return diff
                return diff / 100

            obj_label = CleanText(TableCell('label'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_unitprice = CleanDecimal(TableCell('unitprice', default=None), replace_dots=True, default=NotAvailable)
            obj_diff = CleanDecimal(TableCell('diff'), replace_dots=True, default=NotAvailable)


class DetailFondsPage(LoggedPage, HTMLPage):
    def get_isin_code(self):
        return CleanText('//td[contains(text(), "CodeISIN")]/b', default=NotAvailable)(self.doc)


def MyInput(*args, **kwargs):
    args = (u'//input[contains(@name, "%s")]' % args[0], 'value',)
    kwargs.update(default=NotAvailable)
    return Attr(*args, **kwargs)


def MySelect(*args, **kwargs):
    args = (u'//select[contains(@name, "%s")]/option[@selected]' % args[0],)
    kwargs.update(default=NotAvailable)
    return CleanText(*args, **kwargs)


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Person

        obj_name = CleanText('//a[has-class("hme-pm")]/span[@title]')
        obj_address = CleanText('//ul[@class="newPostAdress"]//dd[@class="withMessage"]')
        obj_country = CleanText('//dt[label[contains(text(), "Pays")]]/following-sibling::dd')
        obj_email = CleanText('//dt[contains(text(), "Email")]/following-sibling::dd/text()')
        obj_phone = Env('phone')
        obj_mobile = Env('mobile')

        def parse(self, el):
            pattern = '//dt[contains(text(), "%s")]/following-sibling::dd/label'
            phone = CleanText(pattern % "professionnel")(self)
            mobile = CleanText(pattern % "portable")(self)
            self.env['phone'] = phone or mobile
            self.env['mobile'] = mobile

    @method
    class update_profile(ItemElement):
        obj_job = MyInput('category_pro')
        obj_job_contract_type = MySelect('contractType')
        obj_company_name = MyInput('category_empl')
        obj_socioprofessional_category = MySelect('personal_form:csp')

        def obj_job_activity_area(self):
            return MySelect('business_sector')(self) or NotAvailable

        def obj_main_bank(self):
            return MySelect('present_bank')(self) or NotAvailable

        def obj_housing_status(self):
            return MySelect('housingType')(self) or NotAvailable

        def obj_job_start_date(self):
            month = MySelect('seniority_Month')(self)
            year = MySelect('seniority_Year')(self)
            return Date(default=NotAvailable).filter('01/%s/%s' % (month, year)) if month and year else NotAvailable

        def obj_birth_date(self):
            birth_date = self.page.browser.birthday
            return Date().filter("%s/%s/%s" % (birth_date[2:4], birth_date[:2], birth_date[-4:]))
