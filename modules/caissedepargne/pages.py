# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from __future__ import division
from __future__ import unicode_literals

from base64 import b64decode
from collections import OrderedDict
import re
from io import BytesIO

from decimal import Decimal
from datetime import datetime

from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage, pagination, FormNotFound
from weboob.browser.elements import ItemElement, method, ListElement, TableElement, SkipItem, DictElement
from weboob.browser.filters.standard import (
    Date, CleanDecimal, Regexp, CleanText, Env, Upper,
    Field, Eval, Format, Currency, Coalesce,
)
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import (
    Account, Investment, Recipient, TransferBankError, Transfer,
    AddRecipientBankError, Loan, RecipientInvalidOTP,
)
from weboob.capabilities.bill import DocumentTypes, Subscription, Document
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_rib_valid, rib2iban, is_iban_valid
from weboob.tools.captcha.virtkeyboard import GridVirtKeyboard
from weboob.tools.compat import unicode
from weboob.exceptions import NoAccountsException, BrowserUnavailable, ActionNeeded
from weboob.browser.filters.json import Dict

def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True)
    return CleanDecimal(*args, **kwargs)

class MyTableCell(TableCell):
    def __init__(self, *names, **kwargs):
        super(MyTableCell, self).__init__(*names, **kwargs)
        self.td = './tr[%s]/td'

def fix_form(form):
    keys = ['MM$HISTORIQUE_COMPTE$btnCumul', 'Cartridge$imgbtnMessagerie', 'MM$m_CH$ButtonImageFondMessagerie',
            'MM$m_CH$ButtonImageMessagerie']
    for name in keys:
        form.pop(name, None)


def float_to_decimal(f):
    return Decimal(str(f))


class LoginPage(JsonPage):
    def on_load(self):
        error_msg = self.doc.get('error')
        if error_msg and 'Le service est momentanément indisponible' in error_msg:
            raise BrowserUnavailable(error_msg)

    def get_response(self):
        return self.doc


class CaissedepargneKeyboard(GridVirtKeyboard):
    color = (255, 255, 255)
    margin = 3, 3
    symbols = {'0': 'ef8d775a73b751c5fbee06e2d537785c',
               '1': 'bf51842846c3045f76355de32e4689c7',
               '2': 'e4c057317b7ceb17241a0ae4c26844c4',
               '3': 'c28c0c109a63f034d0f7c0f7ffdb364c',
               '4': '6ea6a5152efb1d12c33f9cbf9476caec',
               '5': '7ec4b424b5db7e7b2a54e6300fdb7515',
               '6': 'a1fa95fc856804f978f20ad42c60f6d7',
               '7': '64646adaa5a0b2506880970d8e928156',
               '8': '4abcc6b24fa77f3756b96257962615eb',
               '9': '3f41daf8ca5f250be5df91fe24079735'}

    def __init__(self, image, symbols):
        image = BytesIO(b64decode(image.encode('ascii')))
        super(CaissedepargneKeyboard, self).__init__(symbols, 5, 3, image, self.color, convert='RGB')

    def check_color(self, pixel):
        for c in pixel:
            if c < 250:
                return True


class GarbagePage(LoggedPage, HTMLPage):
    def on_load(self):
        go_back_link = Link('//a[@class="btn"]', default=NotAvailable)(self.doc)

        if go_back_link is not NotAvailable:
            assert len(go_back_link) != 1
            go_back_link = re.search('\(~deibaseurl\)(.*)$', go_back_link).group(1)

            self.browser.location('%s%s' % (self.browser.BASEURL, go_back_link))


class MessagePage(GarbagePage):
    def get_message(self):
        return CleanText('//form[contains(@name, "leForm")]//span')(self.doc)

    def submit(self):
        form = self.get_form(name='leForm')

        form['signatur1'] = ['on']

        form.submit()


class _LogoutPage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable(CleanText('//*[@class="messErreur"]')(self.doc))


class ErrorPage(_LogoutPage):
    pass


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CB (?P<text>.*?) FACT (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})\b', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^RET(RAIT)? DAB (?P<dd>\d+)-(?P<mm>\d+)-.*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^RET(RAIT)? DAB (?P<text>.*?) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<HH>\d{2})H(?P<MM>\d{2})\b', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR(EMENT)?(\.PERIODIQUE)? (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*', re.IGNORECASE),    FrenchTransaction.TYPE_CHECK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile(r'^\* (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CB [\d\*]+ TOT DIF .*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile('^CB [\d\*]+ (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^CB (?P<text>.*?) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})\b', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'\*CB (?P<text>.*?) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})\b', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^FAC CB (?P<text>.*?) (?P<dd>\d{2})/(?P<mm>\d{2})\b', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^\*?CB (?P<text>.*)', re.IGNORECASE), FrenchTransaction.TYPE_CARD),
               ]


class IndexPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'Epargne liquide':            Account.TYPE_SAVINGS,
                     u'Compte Courant':             Account.TYPE_CHECKING,
                     u'COMPTE A VUE':               Account.TYPE_CHECKING,
                     u'COMPTE CHEQUE':              Account.TYPE_CHECKING,
                     u'Mes comptes':                Account.TYPE_CHECKING,
                     u'CPT DEPOT PART.':            Account.TYPE_CHECKING,
                     u'CPT DEPOT PROF.':            Account.TYPE_CHECKING,
                     u'Mon épargne':                Account.TYPE_SAVINGS,
                     u'Mes autres comptes':         Account.TYPE_SAVINGS,
                     u'Compte Epargne et DAT':      Account.TYPE_SAVINGS,
                     u'Plan et Contrat d\'Epargne': Account.TYPE_SAVINGS,
                     u'COMPTE SUR LIVRET':          Account.TYPE_SAVINGS,
                     u'LIVRET DEV.DURABLE':         Account.TYPE_SAVINGS,
                     u'LDD Solidaire':              Account.TYPE_SAVINGS,
                     u'LIVRET A':                   Account.TYPE_SAVINGS,
                     u'LIVRET JEUNE':               Account.TYPE_SAVINGS,
                     u'LIVRET GRAND PRIX':          Account.TYPE_SAVINGS,
                     u'LEP':                        Account.TYPE_SAVINGS,
                     u'LEL':                        Account.TYPE_SAVINGS,
                     u'CPT PARTS SOCIALES':         Account.TYPE_SAVINGS,
                     u'PEL 16 2013':                Account.TYPE_SAVINGS,
                     u'Titres':                     Account.TYPE_MARKET,
                     u'Compte titres':              Account.TYPE_MARKET,
                     u'Mes crédits immobiliers':    Account.TYPE_LOAN,
                     u'Mes crédits renouvelables':  Account.TYPE_LOAN,
                     u'Mes crédits consommation':   Account.TYPE_LOAN,
                     u'PEA NUMERAIRE':              Account.TYPE_PEA,
                     u'PEA':                        Account.TYPE_PEA,
                    }

    def build_doc(self, content):
        content = content.strip(b'\x00')
        return super(IndexPage, self).build_doc(content)

    def on_load(self):

        # For now, we have to handle this because after this warning message,
        # the user is disconnected (even if all others account are reachable)
        if 'OIC_QCF' in self.browser.url:
            # QCF is a mandatory test to make sure you know the basics about financials products
            # however, you can still choose to postpone it. hence the continue link
            link = Link('//span[@id="lea-prdvel-lien"]//b/a[contains(text(), "Continuer")]')(self.doc)
            if link:
                self.logger.warning("By-passing QCF")
                self.browser.location(link)
            else:
                message = CleanText(self.doc.xpath('//span[contains(@id, "OIC_QCF")]/p'))(self)
                if message and "investissement financier (QCF) n’est plus valide à ce jour ou que vous avez refusé d’y répondre" in message:
                    raise ActionNeeded(message)

        mess = CleanText('//body/div[@class="content"]//p[contains(text(), "indisponible pour cause de maintenance")]')(self.doc)
        if mess:
            raise BrowserUnavailable(mess)

        # This page is sometimes an useless step to the market website.
        bourse_link = Link(u'//div[@id="MM_COMPTE_TITRE_pnlbourseoic"]//a[contains(text(), "Accédez à la consultation")]', default=None)(self.doc)

        if bourse_link:
            self.browser.location(bourse_link)

    def need_auth(self):
        return bool(CleanText(u'//span[contains(text(), "Authentification non rejouable")]')(self.doc))

    def check_no_loans(self):
        return not bool(CleanText(u'//table[@class="menu"]//div[contains(., "Crédits")]')(self.doc)) and \
               not bool(CleanText(u'//table[@class="header-navigation_main"]//a[contains(., "Crédits")]')(self.doc))

    def check_measure_accounts(self):
        return not CleanText(u'//div[@class="MessageErreur"]/ul/li[contains(text(), "Aucun compte disponible")]')(self.doc)

    def check_no_accounts(self):
        no_account_message = CleanText(u'//span[@id="MM_LblMessagePopinError"]/p[contains(text(), "Aucun compte disponible")]')(self.doc)

        if no_account_message:
            raise NoAccountsException(no_account_message)

    def find_and_replace(self, info, acc_id):
        # The site might be broken: id in js: 4097800039137N418S00197, id in title: 1379418S001 (N instead of 9)
        # So we seek for a 1 letter difference and replace if found .... (so sad)
        for i in range(len(info['id']) - len(acc_id) + 1):
            sub_part = info['id'][i:i+len(acc_id)]
            z = zip(sub_part, acc_id)
            if len([tuple_letter for tuple_letter in z if len(set(tuple_letter)) > 1]) == 1:
                info['link'] = info['link'].replace(sub_part, acc_id)
                info['id'] = info['id'].replace(sub_part, acc_id)
                return

    def _get_account_info(self, a, accounts):
        m = re.search("PostBack(Options)?\([\"'][^\"']+[\"'],\s*['\"]([HISTORIQUE_\w|SYNTHESE_ASSURANCE_CNP|BOURSE|COMPTE_TITRE][\d\w&]+)?['\"]", a.attrib.get('href', ''))
        if m is None:
            return None
        else:
            # it is in form CB&12345[&2]. the last part is only for new website
            # and is necessary for navigation.
            link = m.group(2)
            parts = link.split('&')
            info = {}
            info['link'] = link
            id = re.search("([\d]+)", a.attrib.get('title', ''))
            if len(parts) > 1:
                info['type'] = parts[0]
                info['id'] = info['_id'] = parts[1]
                if id or info['id'] in [acc._info['_id'] for acc in accounts.values()]:
                    _id = id.group(1) if id else next(iter({k for k, v in accounts.items() if info['id'] == v._info['_id']}))
                    self.find_and_replace(info, _id)
            else:
                info['type'] = link
                info['id'] = info['_id'] = id.group(1)
            if info['type'] in ('SYNTHESE_ASSURANCE_CNP', 'SYNTHESE_EPARGNE', 'ASSURANCE_VIE'):
                info['acc_type'] = Account.TYPE_LIFE_INSURANCE
            if info['type'] in ('BOURSE', 'COMPTE_TITRE'):
                info['acc_type'] = Account.TYPE_MARKET
            return info

    def is_account_inactive(self, account_id):
        return self.doc.xpath('//tr[td[contains(text(), $id)]][@class="Inactive"]', id=account_id)

    def _add_account(self, accounts, link, label, account_type, balance, number=None):
        info = self._get_account_info(link, accounts)
        if info is None:
            self.logger.warning('Unable to parse account %r: %r' % (label, link))
            return

        account = Account()
        account._card_links = None
        account.id = info['id']
        if is_rib_valid(info['id']):
            account.iban = rib2iban(info['id'])
        account._info = info
        account.number = number
        account.label = label
        account.type = self.ACCOUNT_TYPES.get(label, info['acc_type'] if 'acc_type' in info else account_type)
        if 'PERP' in account.label:
            account.type = Account.TYPE_PERP
        if 'NUANCES CAPITALISATI' in account.label:
            account.type = Account.TYPE_CAPITALISATION

        balance = balance or self.get_balance(account)

        account.balance = Decimal(FrenchTransaction.clean_amount(balance)) if balance and balance is not NotAvailable else NotAvailable

        account.currency = account.get_currency(balance) if balance and balance is not NotAvailable else NotAvailable
        account._card_links = []

        # Set coming history link to the parent account. At this point, we don't have card account yet.
        if account._info['type'] == 'HISTORIQUE_CB' and account.id in accounts:
            a = accounts[account.id]
            a.coming = Decimal('0.0')
            a._card_links = account._info
            return

        accounts[account.id] = account
        return account

    def get_balance(self, account):
        if account.type not in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_PERP, Account.TYPE_CAPITALISATION):
            return NotAvailable
        page = self.go_history(account._info).page
        balance = page.doc.xpath('.//tr[td[contains(@id,"NumContrat")]]/td[@class="somme"]/a[contains(@href, $id)]', id=account.id)
        if len(balance) > 0:
            balance = CleanText('.')(balance[0])
            balance = balance if balance != u'' else NotAvailable
        else:
            # Specific xpath for some Life Insurances:
            balance = page.doc.xpath('//tr[td[contains(text(), $id)]]/td/div[contains(@id, "Solde")]', id=account.id)
            if len(balance) > 0:
                balance = CleanText('.')(balance[0])
                balance = balance if balance != u'' else NotAvailable
            else:
                # sometimes the accounts are attached but no info is available
                balance = NotAvailable
        self.go_list()
        return balance

    def get_measure_balance(self, account):
        for tr in self.doc.xpath('//table[@cellpadding="1"]/tr[not(@class)]'):
            account_number = CleanText('./td/a[contains(@class, "NumeroDeCompte")]')(tr)
            if re.search(r'[A-Z]*\d{3,}', account_number).group() in account.id:
                # The regex '\s\d{1,3}(?:[\s.,]\d{3})*(?:[\s.,]\d{2})' matches for example '106 100,64'
                return re.search(r'\s\d{1,3}(?:[\s.,]\d{3})*(?:[\s.,]\d{2})', account_number).group()
        return NotAvailable

    def get_measure_ids(self):
        accounts_id = []
        for a in self.doc.xpath('//table[@cellpadding="1"]/tr/td[2]/a'):
            accounts_id.append(re.search("(\d{6,})", Attr('.', 'href')(a)).group(1))
        return accounts_id

    def get_list(self):
        accounts = OrderedDict()

        # Old website
        self.browser.new_website = False
        for table in self.doc.xpath('//table[@cellpadding="1"]'):
            account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tr'):
                tds = tr.findall('td')
                if tr.attrib.get('class', '') == 'DataGridHeader':
                    account_type = self.ACCOUNT_TYPES.get(tds[1].text.strip()) or\
                                   self.ACCOUNT_TYPES.get(CleanText('.')(tds[2])) or\
                                   self.ACCOUNT_TYPES.get(CleanText('.')(tds[3]), Account.TYPE_UNKNOWN)
                else:
                    # On the same row, there could have many accounts (check account and a card one).
                    # For the card line, the number will be the same than the checking account, so we skip it.
                    if len(tds) > 4:
                        for i, a in enumerate(tds[2].xpath('./a')):
                            label = CleanText('.')(a)
                            balance = CleanText('.')(tds[-2].xpath('./a')[i])
                            number = None
                            # if i > 0, that mean it's a card account. The number will be the same than it's
                            # checking parent account, we have to skip it.
                            if i == 0:
                                number = CleanText('.')(tds[-4].xpath('./a')[0])
                            self._add_account(accounts, a, label, account_type, balance, number)
                    # Only 4 tds on "banque de la reunion" website.
                    elif len(tds) == 4:
                        for i, a in enumerate(tds[1].xpath('./a')):
                            label = CleanText('.')(a)
                            balance = CleanText('.')(tds[-1].xpath('./a')[i])
                            self._add_account(accounts, a, label, account_type, balance)

        self.logger.debug('we are on the %s website', 'old' if accounts else 'new')

        if len(accounts) == 0:
            # New website
            self.browser.new_website = True
            for table in self.doc.xpath('//div[@class="panel"]'):
                title = table.getprevious()
                if title is None:
                    continue
                account_type = self.ACCOUNT_TYPES.get(CleanText('.')(title), Account.TYPE_UNKNOWN)
                for tr in table.xpath('.//tr'):
                    tds = tr.findall('td')
                    for i in range(len(tds)):
                        a = tds[i].find('a')
                        if a is not None:
                            break

                    if a is None:
                        continue

                    # sometimes there's a tooltip span to ignore next to <strong>
                    # (perhaps only on creditcooperatif)
                    label = CleanText('./strong')(tds[0])
                    balance = CleanText('.')(tds[-1])

                    account = self._add_account(accounts, a, label, account_type, balance)
                    if account:
                        account.number = CleanText('.')(tds[1])

        return accounts.values()

    def is_access_error(self):
        error_message = u"Vous n'êtes pas autorisé à accéder à cette fonction"
        if error_message in CleanText('//div[@class="MessageErreur"]')(self.doc):
            return True

        return False

    def go_loans_conso(self, tr):

        link = tr.xpath('./td/a[contains(@id, "IdaCreditPerm")]')
        m = re.search('CREDITCONSO&(\w+)', link[0].attrib['href'])
        if m:
            account = m.group(1)

        form = self.get_form(id="main")
        form['__EVENTTARGET'] = 'MM$SYNTHESE_CREDITS'
        form['__EVENTARGUMENT'] = 'ACTIVDESACT_CREDITCONSO&%s' % account
        form['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$SYNTHESE_CREDITS'
        form.submit()

    def get_loan_list(self):
        accounts = OrderedDict()

        # Old website
        for tr in self.doc.xpath('//table[@cellpadding="1"]/tr[not(@class) and td[a]]'):
            tds = tr.findall('td')

            account = Account()
            account._card_links = None
            account.id = CleanText('./a')(tds[2]).split('-')[0].strip()
            account.label = CleanText('./a')(tds[2]).split('-')[-1].strip()
            account.type = Account.TYPE_LOAN
            account.balance = -CleanDecimal('./a', replace_dots=True)(tds[4])
            account.currency = account.get_currency(CleanText('./a')(tds[4]))
            accounts[account.id] = account

        self.logger.debug('we are on the %s website', 'old' if accounts else 'new')

        if len(accounts) == 0:
            # New website
            for table in self.doc.xpath('//div[@class="panel"]'):
                title = table.getprevious()
                if title is None:
                    continue
                if "immobiliers" not in CleanText('.')(title):
                    account_type = self.ACCOUNT_TYPES.get(CleanText('.')(title), Account.TYPE_UNKNOWN)
                    for tr in table.xpath('./table/tbody/tr[contains(@id,"MM_SYNTHESE_CREDITS") and contains(@id,"IdTrGlobal")]'):
                        tds = tr.findall('td')
                        if len(tds) == 0 :
                            continue
                        for i in tds[0].xpath('.//a/strong'):
                            label = i.text.strip()
                            break
                        if len(tds) == 3 and Decimal(FrenchTransaction.clean_amount(CleanText('.')(tds[-2]))) and any(cls in Attr('.', 'id')(tr) for cls in ['dgImmo', 'dgConso']) == False:
                            # in case of Consumer credit or revolving credit, we substract avalaible amount with max amout
                            # to get what was spend
                            balance = Decimal(FrenchTransaction.clean_amount(CleanText('.')(tds[-2]))) - Decimal(FrenchTransaction.clean_amount(CleanText('.')(tds[-1])))
                        else:
                            balance = Decimal(FrenchTransaction.clean_amount(CleanText('.')(tds[-1])))
                        account = Loan()
                        account.id = label.split(' ')[-1]
                        account.label = unicode(label)
                        account.type = account_type
                        account.balance = -abs(balance)
                        account.currency = account.get_currency(CleanText('.')(tds[-1]))
                        account._card_links = []

                        if "renouvelables" in CleanText('.')(title):
                            if 'JSESSIONID' in self.browser.session.cookies:
                                # Need to delete this to access the consumer loans space (a new one will be created)
                                del self.browser.session.cookies['JSESSIONID']
                            self.go_loans_conso(tr)
                            d = self.browser.loans_conso()
                            if d:
                                account.total_amount = float_to_decimal(d['contrat']['creditMaxAutorise'])
                                account.available_amount = float_to_decimal(d['situationCredit']['disponible'])
                                account.next_payment_amount = float_to_decimal(d['situationCredit']['mensualiteEnCours'])
                        accounts[account.id] = account
        return accounts.values()

    @method
    class get_real_estate_loans(ListElement):
        # beware the html response is slightly different from what can be seen with the browser
        # because of some JS most likely: use the native HTML response to build the xpath
        item_xpath = '//h3[contains(text(), "immobiliers")]//following-sibling::div[@class="panel"][1]//div[@id[starts-with(.,"MM_SYNTHESE_CREDITS")] and contains(@id, "IdDivDetail")]'

        class iter_account(TableElement):
            item_xpath = './table[@class="static"][1]/tbody'
            head_xpath = './table[@class="static"][1]/tbody/tr/th'

            col_total_amount = u'Capital Emprunté'
            col_rate = u'Taux d’intérêt nominal'
            col_balance = u'Capital Restant Dû'
            col_last_payment_date = u'Dernière échéance'
            col_next_payment_amount = u'Montant prochaine échéance'
            col_next_payment_date = u'Prochaine échéance'

            def parse(self, el):
                self.env['id'] = CleanText("./h2")(el).split()[-1]
                self.env['label'] = CleanText("./h2")(el)

            class item(ItemElement):

                klass = Loan

                obj_id = Env('id')
                obj_label = Env('label')
                obj_type = Loan.TYPE_LOAN
                obj_total_amount = MyDecimal(MyTableCell("total_amount"))
                obj_rate = Eval(lambda x: x / 100, MyDecimal(MyTableCell("rate", default=NotAvailable), default=NotAvailable))
                obj_balance = MyDecimal(MyTableCell("balance"), sign=lambda x: -1)
                obj_currency = Currency(MyTableCell("balance"))
                obj_last_payment_date = Date(CleanText(MyTableCell("last_payment_date")))
                obj_next_payment_amount = MyDecimal(MyTableCell("next_payment_amount"))
                obj_next_payment_date = Date(CleanText(MyTableCell("next_payment_date", default=''), default=NotAvailable), default=NotAvailable)

    def submit_form(self, form, eventargument, eventtarget, scriptmanager):
        form['__EVENTARGUMENT'] = eventargument
        form['__EVENTTARGET'] = eventtarget
        form['m_ScriptManager'] = scriptmanager
        fix_form(form)
        form.submit()

    def go_list(self):

        form = self.get_form(id='main')
        eventargument = "CPTSYNT0"

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            eventtarget = "Menu_AJAX"
            scriptmanager = "m_ScriptManager|Menu_AJAX"
        else:
            # New website
            eventtarget = "MM$m_PostBack"
            scriptmanager = "MM$m_UpdatePanel|MM$m_PostBack"

        self.submit_form(form, eventargument, eventtarget, scriptmanager)

    def go_cards(self):
        # Do not try to go the card summary if we have no card, it breaks the session
        if self.browser.new_website and not CleanText('//form[@id="main"]//a/span[text()="Mes cartes bancaires"]')(self.doc):
            self.logger.info("Do not try to go the CardsPage, there is not link on the main page")
            return

        form = self.get_form(id='main')

        eventargument = ""

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            eventtarget = "Menu_AJAX"
            eventargument = "HISENCB0"
            scriptmanager = "m_ScriptManager|Menu_AJAX"
        else:
            # New website
            eventtarget = "MM$SYNTHESE$btnSyntheseCarte"
            scriptmanager = "MM$m_UpdatePanel|MM$SYNTHESE$btnSyntheseCarte"

        self.submit_form(form, eventargument, eventtarget, scriptmanager)

    # only for old website
    def go_card_coming(self, eventargument):
        form = self.get_form(id='main')
        eventtarget = "MM$HISTORIQUE_CB"
        scriptmanager = "m_ScriptManager|Menu_AJAX"
        self.submit_form(form, eventargument, eventtarget, scriptmanager)

    # only for new website
    def go_coming(self, eventargument):
        form = self.get_form(id='main')
        eventtarget = "MM$HISTORIQUE_CB"
        scriptmanager = "MM$m_UpdatePanel|MM$HISTORIQUE_CB"
        self.submit_form(form, eventargument, eventtarget, scriptmanager)

    # On some pages, navigate to indexPage does not lead to the list of measures, so we need this form ...
    def go_measure_list(self):
        form = self.get_form(id='main')

        form['__EVENTARGUMENT'] = "MESLIST0"
        form['__EVENTTARGET'] = 'Menu_AJAX'
        form['m_ScriptManager'] = 'm_ScriptManager|Menu_AJAX'

        fix_form(form)

        form.submit()

    # This function goes to the accounts page of one measure giving its id
    def go_measure_accounts_list(self, measure_id):
        form = self.get_form(id='main')

        form['__EVENTARGUMENT'] = "CPTSYNT0"

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            form['__EVENTTARGET'] = "MM$SYNTHESE_MESURES"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$SYNTHESE_MESURES"
            form['__EVENTARGUMENT'] = measure_id
        else:
            # New website
            form['__EVENTTARGET'] = "MM$m_PostBack"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$m_PostBack"

        fix_form(form)

        form.submit()

    def go_loan_list(self):
        form = self.get_form(id='main')

        form['__EVENTARGUMENT'] = "CRESYNT0"

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            pass
        else:
            # New website
            form['__EVENTTARGET'] = "MM$m_PostBack"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$m_PostBack"

        fix_form(form)

        form.submit()

    def is_history_of(self, account_id):
        """
        Check whether the displayed history is for the correct account.
        If we do not find the select box we consider we are on the expected account (like it was before this check)
        """
        if self.doc.xpath('//select[@id="MM_HISTORIQUE_COMPTE_m_ExDropDownList"]'):
            return bool(self.doc.xpath('//option[@value="%s" and @selected]' % account_id))
        return True

    def go_history(self, info, is_cbtab=False):
        form = self.get_form(id='main')

        form['__EVENTTARGET'] = 'MM$%s' % (info['type'] if is_cbtab else 'SYNTHESE')
        form['__EVENTARGUMENT'] = info['link']

        if "MM$m_CH$IsMsgInit" in form and (form['MM$m_CH$IsMsgInit'] == "0" or info['type'] == 'ASSURANCE_VIE'):
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$SYNTHESE"

        fix_form(form)
        return form.submit()

    def go_history_netpro(self, info, ):
        """
        On the netpro website the go_history() does not work.
        Even from a web browser the site does not work, and display the history of the first account
        We use a different post to go through and display the history we need
        """
        form = self.get_form(id='main')
        form['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$HISTORIQUE_COMPTE$m_ExDropDownList'
        form['MM$HISTORIQUE_COMPTE$m_ExDropDownList'] = info['id']
        form['__EVENTTARGET'] = 'MM$HISTORIQUE_COMPTE$m_ExDropDownList'

        fix_form(form)
        return form.submit()

    def get_form_to_detail(self, transaction):
        m = re.match('.*\("(.*)", "(DETAIL_OP&[\d]+).*\)\)', transaction._link)
        # go to detailcard page
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = m.group(1)
        form['__EVENTARGUMENT'] = m.group(2)
        fix_form(form)
        return form

    def get_history(self):
        i = 0
        ignore = False
        for tr in self.doc.xpath('//table[@cellpadding="1"]/tr') + self.doc.xpath('//tr[@class="rowClick" or @class="rowHover"]'):
            tds = tr.findall('td')

            if len(tds) < 4:
                continue

            # if there are more than 4 columns, ignore the first one.
            i = min(len(tds) - 4, 1)

            if tr.attrib.get('class', '') == 'DataGridHeader':
                if tds[2].text == u'Titulaire':
                    ignore = True
                else:
                    ignore = False
                continue

            if ignore:
                continue

            # Remove useless details
            detail = tr.cssselect('div.detail')
            if len(detail) > 0:
                detail[0].drop_tree()

            t = Transaction()

            date = u''.join([txt.strip() for txt in tds[i+0].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[i+1].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-1].itertext()])

            t.parse(date, re.sub(r'[ ]+', ' ', raw))

            card_debit_date = self.doc.xpath(u'//span[@id="MM_HISTORIQUE_CB_m_TableTitle3_lblTitle"] | //label[contains(text(), "débiter le")]')
            if card_debit_date:
                t.rdate = Date(dayfirst=True).filter(date)
                m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', card_debit_date[0].text)
                assert m
                t.date = Date(dayfirst=True).filter(m.group(1))
            if t.date is NotAvailable:
                continue
            if 'tot dif' in t.raw.lower():
                t._link = Link(tr.xpath('./td/a'))(self.doc)

            # "Cb" for new site, "CB" for old one
            mtc = re.match(r'(Cb|CB) (\d{4}\*+\d{6}) ', raw)
            if mtc is not None:
                t.card = mtc.group(2)

            t.set_amount(credit, debit)
            yield t

            i += 1

    def go_next(self):
        # <a id="MM_HISTORIQUE_CB_lnkSuivante" class="next" href="javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions(&quot;MM$HISTORIQUE_CB$lnkSuivante&quot;, &quot;&quot;, true, &quot;&quot;, &quot;&quot;, false, true))">Suivant<span class="arrow">></span></a>

        link = self.doc.xpath('//a[contains(@id, "lnkSuivante")]')
        if len(link) == 0 or 'disabled' in link[0].attrib or link[0].attrib.get('class') == 'aspNetDisabled':
            return False

        account_type = 'COMPTE'
        m = re.search('HISTORIQUE_(\w+)', link[0].attrib['href'])
        if m:
            account_type = m.group(1)

        form = self.get_form(id='main')

        form['__EVENTTARGET'] = "MM$HISTORIQUE_%s$lnkSuivante" % account_type
        form['__EVENTARGUMENT'] = ''

        if "MM$m_CH$IsMsgInit" in form and form['MM$m_CH$IsMsgInit'] == "N":
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$HISTORIQUE_COMPTE$lnkSuivante"

        fix_form(form)
        form.submit()

        return True

    def go_life_insurance(self, account):
        # The site shows nothing about life insurance accounts except balance, links are disabled
        if 'measure_id' in account._info:
            return

        link = self.doc.xpath('//tr[td[contains(., ' + account.id + ') ]]//a')[0]
        m = re.search("PostBackOptions?\([\"']([^\"']+)[\"'],\s*['\"]((REDIR_ASS_VIE)?[\d\w&]+)?['\"]", link.attrib.get('href', ''))
        if m is not None:
            form = self.get_form(id='main')

            form['__EVENTTARGET'] = m.group(1)
            form['__EVENTARGUMENT'] = m.group(2)

            if "MM$m_CH$IsMsgInit" not in form:
                # Not available on new website
                pass

            form['MM$m_CH$IsMsgInit'] = "0"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$SYNTHESE"

            fix_form(form)
            form.submit()

    def transfer_link(self):
        return self.doc.xpath(u'//a[span[contains(text(), "Effectuer un virement")]] | //a[contains(text(), "Réaliser un virement")]')

    def go_transfer_via_history(self, account):
        self.go_history(account._info)

        # check that transfer is available for the connection before try to go on transfer page
        # otherwise website will continually crash
        if self.transfer_link():
            self.browser.page.go_transfer(account)

    def go_transfer(self, account):
        link = self.transfer_link()
        if len(link) == 0:
            return self.go_transfer_via_history(account)
        else:
            link = link[0]
        m = re.search("PostBackOptions?\([\"']([^\"']+)[\"'],\s*['\"]([^\"']+)?['\"]", link.attrib.get('href', ''))
        form = self.get_form(id='main')
        if 'MM$HISTORIQUE_COMPTE$btnCumul' in form:
            del form['MM$HISTORIQUE_COMPTE$btnCumul']
        form['__EVENTTARGET'] = m.group(1)
        form['__EVENTARGUMENT'] = m.group(2)
        form.submit()

    def transfer_unavailable(self):
        return CleanText(u'//li[contains(text(), "Pour accéder à cette fonctionnalité, vous devez disposer d’un moyen d’authentification renforcée")]')(self.doc)

    def loan_unavailable_msg(self):
        msg = CleanText('//span[@id="MM_LblMessagePopinError"] | //p[@id="MM_ERREUR_PAGE_BLANCHE_pAlert"]')(self.doc)
        if msg:
            return msg

    def go_subscription(self):
        form = self.get_form(id='main')
        form['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$Menu_Ajax'
        form['__EVENTTARGET'] = 'MM$Menu_Ajax'
        link = Link('//a[contains(@title, "e-Documents") or contains(@title, "Relevés en ligne")]')(self.doc)
        form['__EVENTARGUMENT'] = re.search(r'Ajax", "(.*)", true', link).group(1)
        form.submit()

    def is_subscription_unauthorized(self):
        return 'non autorisée' in CleanText('//div[@id="MM_ContentMain"]')(self.doc)

    def go_pro_transfer_availability(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'Menu_AJAX'
        form['__EVENTARGUMENT'] = 'VIRLSRM0'
        form['m_ScriptManager'] = 'm_ScriptManager|Menu_AJAX'
        form.submit()

    def is_transfer_allowed(self):
        return not self.doc.xpath('//ul/li[contains(text(), "Aucun compte tiers n\'est disponible")]')


class CardsPage(IndexPage):
    def is_here(self):
        return CleanText('//h3[normalize-space(text())="Mes cartes (cartes dont je suis le titulaire)"]')(self.doc)

    @method
    class iter_cards(TableElement):
        head_xpath = '//table[@class="cartes"]/tbody/tr/th'

        col_label = 'Carte'
        col_number = 'N°'
        col_parent = 'Compte dépot associé'
        col_coming = 'Encours'

        item_xpath = '//table[@class="cartes"]/tbody/tr[not(th)]'

        class item(ItemElement):
            klass = Account

            obj_type = Account.TYPE_CARD
            obj_label = Format('%s %s', CleanText(TableCell('label')), Field('id'))
            obj_number = CleanText(TableCell('number'))
            obj_id = CleanText(TableCell('number'), replace=[('*', 'X')])
            obj__parent_id = CleanText(TableCell('parent'))
            obj_balance = 0
            obj_currency = Currency(TableCell('coming'))
            obj__card_links = None

            def obj_coming(self):
                if CleanText(TableCell('coming'))(self) == '-':
                    raise SkipItem('immediate debit card?')
                return CleanDecimal.French(TableCell('coming'), sign=lambda x: -1)(self)

            def condition(self):
                immediate_str = ''
                # There are some card without any information. To exclude them, we keep only account
                # with extra "option" (ex: coming transaction link, block bank card...)
                if 'Faire opposition' in CleanText("./td[5]")(self):
                    # Only deferred card have this option to see coming transaction, even when
                    # there is 0 coming (Table element have no thead for the 5th column).
                    if 'Consulter mon encours carte' in CleanText("./td[5]")(self):
                        return True

                    # Card without 'Consulter mon encours carte' are immediate card. There are logged
                    # for now to make the debug easier
                    immediate_str = '[Immediate card]'

                self.logger.warning('Skip card %s (no history/coming information) %s', Field('number')(self), immediate_str)
                return False


class CardsComingPage(IndexPage):
    def is_here(self):
        return CleanText('//h2[text()="Encours de carte à débit différé"]')(self.doc)

    @method
    class iter_cards(ListElement):
        item_xpath = '//table[contains(@class, "compte") and position() = 1]//tr[contains(@id, "MM_HISTORIQUE_CB") and position() < last()]'

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                # We must handle two kinds of Regexp because the 'X' are not
                # located at the same level for sub-modules such as palatine
                return Coalesce(
                    Regexp(CleanText(Field('label'), replace=[('*', 'X')]), r'(\d{6}\X{6}\d{4})', default=NotAvailable),
                    Regexp(CleanText(Field('label'), replace=[('*', 'X')]), r'(\d{4}\X{6}\d{6})', default=NotAvailable),
                )(self)

            def obj_number(self):
                return Coalesce(
                    Regexp(CleanText(Field('label')), r'(\d{6}\*{6}\d{4})', default=NotAvailable),
                    Regexp(CleanText(Field('label')), r'(\d{4}\*{6}\d{6})', default=NotAvailable),
                )(self)

            obj_type = Account.TYPE_CARD
            obj_label = CleanText('./td[1]')
            obj_balance = Decimal(0)
            obj_coming = CleanDecimal.French('./td[2]')
            obj_currency = Currency('./td[2]')
            obj__card_links = None

    def get_card_coming_info(self, number, info):
        # If the xpath match, that mean there are only one card
        # We have enough information in `info` to get its coming transaction
        if CleanText('//tr[@id="MM_HISTORIQUE_CB_rptMois0_ctl01_trItem"]')(self.doc):
            return info

        # If the xpath match, that mean there are at least 2 cards
        xpath = '//tr[@id="MM_HISTORIQUE_CB_rptMois0_trItem_0"]'

        # In case of multiple card, first card coming's transactions are reachable
        # with information in `info`.
        if Regexp(CleanText(xpath), r'(\d{6}\*{6}\d{4})')(self.doc) == number:
            return info

        # Some cards redirect to a checking account where we cannot found them. Since we have no details or history,
        # we return None and skip them in the browser.
        if CleanText('//a[contains(text(),"%s")]' % number)(self.doc):
            # For all cards except the first one for the same check account, we have to get info through their href info
            link = CleanText(Link('//a[contains(text(),"%s")]' % number))(self.doc)
            infos = re.match(r'.*(DETAIL_OP_M0&[^\"]+).*', link)
            info['link'] = infos.group(1)

            return info
        return None


class CardsOldWebsitePage(IndexPage):
    def is_here(self):
        return CleanText('//span[@id="MM_m_CH_lblTitle" and contains(text(), "Historique de vos encours CB")]')(self.doc)

    def get_account(self):
        infos = CleanText('.//span[@id="MM_HISTORIQUE_CB"]/table[position()=1]//td')(self.doc)
        result = re.search(r'.*(\d{11}).*', infos)
        return result.group(1)

    def get_date(self):
        title = CleanText('//span[@id="MM_HISTORIQUE_CB_m_TableTitle3_lblTitle"]')(self.doc)
        title_date = re.match('.*le (.*) sur .*', title)
        return Date(dayfirst=True).filter(title_date.group(1))

    @method
    class iter_cards(TableElement):
        head_xpath = '//table[@id="MM_HISTORIQUE_CB_m_ExDGOpeM0"]//tr[@class="DataGridHeader"]/td'
        item_xpath = '//table[@id="MM_HISTORIQUE_CB_m_ExDGOpeM0"]//tr[not(contains(@class, "DataGridHeader")) and position() < last()]'

        col_label = 'Libellé'
        col_coming = 'Solde'

        class item(ItemElement):
            klass = Account

            obj_type = Account.TYPE_CARD
            obj_label = Format('%s %s', CleanText(TableCell('label')), CleanText(Field('number')))
            obj_balance = 0
            obj_coming = CleanDecimal.French(TableCell('coming'))
            obj_currency = Currency(TableCell('coming'))
            obj__card_links = None

            def obj__parent_id(self):
                return self.page.get_account()

            def obj_number(self):
                return CleanText(TableCell('number'))(self).replace('*', 'X')

            def obj_id(self):
                number = Field('number')(self).replace('X', '')
                account_id = '%s-%s' % (self.obj__parent_id(), number)
                return account_id

            def obj__coming_eventargument(self):
                url = Attr('.//a', 'href')(self)
                res = re.match(r'.*(DETAIL_OP_M0\&.*;\d{8})", .*', url)
                return res.group(1)

        def parse(self, obj):
            # There are no thead name for this column.
            self._cols['number'] = 3

    @method
    class iter_coming(TableElement):
        head_xpath = '//table[@id="MM_HISTORIQUE_CB_m_ExDGDetailOpe"]//tr[@class="DataGridHeader"]/td'
        item_xpath = '//table[@id="MM_HISTORIQUE_CB_m_ExDGDetailOpe"]//tr[not(contains(@class, "DataGridHeader"))]'

        col_label = 'Libellé'
        col_coming = 'Débit'
        col_date = 'Date'

        class item(ItemElement):
            klass = Transaction

            obj_type = Transaction.TYPE_DEFERRED_CARD
            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal.French(TableCell('coming'), sign=lambda x: -1)
            obj_rdate = Date(CleanText(TableCell('date')), dayfirst=True)

            def obj_date(self):
                return self.page.get_date()


class ConsLoanPage(JsonPage):
    def get_conso(self):
        return self.doc


class LoadingPage(HTMLPage):
    def on_load(self):
        # CTX cookie seems to corrupt the request fetching info about "credit
        # renouvelable" and to lead to a 409 error
        if 'CTX' in self.browser.session.cookies.keys():
            del self.browser.session.cookies['CTX']

        form = self.get_form(id="REROUTAGE")
        form.submit()


class NatixisRedirectPage(LoggedPage, HTMLPage):
    def on_load(self):
        try:
            form = self.get_form(id="NaAssurance")
        except FormNotFound:
            form = self.get_form(id="formRoutage")
        form.submit()


class MarketPage(LoggedPage, HTMLPage):
    def is_error(self):
        return CleanText('//caption[contains(text(),"Erreur")]')(self.doc)

    def parse_decimal(self, td, percentage=False):
        value = CleanText('.')(td)
        if value and value != '-':
            if percentage:
                return Decimal(FrenchTransaction.clean_amount(value)) / 100
            return Decimal(FrenchTransaction.clean_amount(value))
        else:
            return NotAvailable

    def submit(self):
        form = self.get_form(nr=0)

        form.submit()

    def iter_investment(self):
        for tbody in self.doc.xpath(u'//table[@summary="Contenu du portefeuille valorisé"]/tbody'):
            inv = Investment()
            inv.label = CleanText('.')(tbody.xpath('./tr[1]/td[1]/a/span')[0])
            inv.code = CleanText('.')(tbody.xpath('./tr[1]/td[1]/a')[0]).split(' - ')[1]
            inv.code_type = Investment.CODE_TYPE_ISIN if is_isin_valid(inv.code) else NotAvailable
            inv.quantity = self.parse_decimal(tbody.xpath('./tr[2]/td[2]')[0])
            inv.unitvalue = self.parse_decimal(tbody.xpath('./tr[2]/td[3]')[0])
            inv.unitprice = self.parse_decimal(tbody.xpath('./tr[2]/td[5]')[0])
            inv.valuation = self.parse_decimal(tbody.xpath('./tr[2]/td[4]')[0])
            inv.diff = self.parse_decimal(tbody.xpath('./tr[2]/td[7]')[0])

            yield inv

    def get_valuation_diff(self, account):
        val = CleanText(self.doc.xpath(u'//td[contains(text(), "values latentes")]/following-sibling::*[1]'))
        account.valuation_diff = CleanDecimal(Regexp(val, '([^\(\)]+)'), replace_dots=True)(self)

    def is_on_right_portfolio(self, account):
        return len(self.doc.xpath('//form[@class="choixCompte"]//option[@selected and contains(text(), $id)]', id=account._info['id']))

    def get_compte(self, account):
        return self.doc.xpath('//option[contains(text(), $id)]/@value', id=account._info['id'])[0]

    def come_back(self):
        link = Link(u'//div/a[contains(text(), "Accueil accès client")]', default=NotAvailable)(self.doc)
        if link:
            self.browser.location(link)


class LifeInsurance(MarketPage):
    def get_cons_repart(self):
        return self.doc.xpath('//tr[@id="sousMenuConsultation3"]/td/div/a')[0].attrib['href']

    def get_cons_histo(self):
        return self.doc.xpath('//tr[@id="sousMenuConsultation4"]/td/div/a')[0].attrib['href']

    def iter_history(self):
        for tr in self.doc.xpath(u'//table[@class="boursedetail"]/tbody/tr[td]'):
            t = Transaction()

            t.label = CleanText('.')(tr.xpath('./td[2]')[0])
            t.date = Date(dayfirst=True).filter(CleanText('.')(tr.xpath('./td[1]')[0]))
            t.amount = self.parse_decimal(tr.xpath('./td[3]')[0])

            yield t

    def iter_investment(self):
        for tr in self.doc.xpath(u'//table[@class="boursedetail"]/tr[@class and not(@class="total")]'):

            inv = Investment()
            libelle = CleanText('.')(tr.xpath('./td[1]')[0]).split(' ')
            inv.label, inv.code = self.split_label_code(libelle)
            inv.code_type = Investment.CODE_TYPE_ISIN if is_isin_valid(inv.code) else NotAvailable
            inv.quantity = self.parse_decimal(tr.xpath('./td[2]')[0])
            inv.unitvalue = self.parse_decimal(tr.xpath('./td[3]')[0])
            date = CleanText('.')(tr.xpath('./td[4]')[0])
            inv.vdate = Date(dayfirst=True).filter(date) if date and date != '-' else NotAvailable
            inv.valuation = self.parse_decimal(tr.xpath('./td[5]')[0])
            inv.diff_percent = self.parse_decimal(tr.xpath('./td[6]')[0], percentage=True)

            yield inv

    def split_label_code(self, libelle):
        if is_isin_valid(libelle[-1]):
            return ' '.join(libelle[:-1]), libelle[-1]
        return ' '.join(libelle), NotAvailable


class NatixisLIHis(LoggedPage, JsonPage):
    @method
    class get_history(DictElement):
        item_xpath = None

        class item(ItemElement):
            klass = Transaction

            obj_amount = Eval(float_to_decimal, Dict('montantNet'))
            obj_raw = CleanText(Dict('libelle', default=''))
            obj_vdate = Date(Dict('dateValeur', default=NotAvailable), default=NotAvailable)
            obj_date = Date(Dict('dateEffet', default=NotAvailable), default=NotAvailable)
            obj_investments = NotAvailable
            obj_type = Transaction.TYPE_BANK

            def validate(self, obj):
                return obj.raw and obj.date


class NatixisLIInv(LoggedPage, JsonPage):
    @method
    class get_investments(DictElement):
        item_xpath = 'detailContratVie/valorisation/supports'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(Dict('nom'))
            obj_code = CleanText(Dict('codeIsin'))

            def obj_vdate(self):
                dt = Dict('dateValeurUniteCompte', default=None)(self)
                if dt is None:
                    dt = self.page.doc['detailContratVie']['valorisation']['date']
                return Date().filter(dt)

            obj_valuation = Eval(float_to_decimal, Dict('montant'))
            obj_quantity = Eval(float_to_decimal, Dict('nombreUnitesCompte'))
            obj_unitvalue = Eval(float_to_decimal, Dict('valeurUniteCompte'))
            obj_portfolio_share = Eval(lambda x: float_to_decimal(x) / 100, Dict('repartition'))


class MyRecipient(ItemElement):
    klass = Recipient

    # Assume all recipients currency is euros.
    obj_currency = u'EUR'

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)


class TransferErrorPage(object):
    def on_load(self):
        errors_xpaths = ['//div[h2[text()="Information"]]/p[contains(text(), "Il ne pourra pas être crédité avant")]',
                         '//span[@id="MM_LblMessagePopinError"]/p | //div[h2[contains(text(), "Erreur de saisie")]]/p[1] | //span[@class="error"]/strong',
                         '//div[@id="MM_m_CH_ValidationSummary" and @class="MessageErreur"]',
        ]

        for error_xpath in errors_xpaths:
            error = CleanText(error_xpath)(self.doc)
            if error:
                raise TransferBankError(message=error)


class MeasurePage(IndexPage):
    def is_here(self):
        return self.doc.xpath('//span[contains(text(), "Liste de vos mesures")]')


class MyRecipients(ListElement):
    def parse(self, obj):
        self.item_xpath = self.page.RECIPIENT_XPATH

    class Item(MyRecipient):
        def validate(self, obj):
            return self.obj_id(self) != self.env['account_id']

        obj_id = Env('id')
        obj_iban = Env('iban')
        obj_bank_name = Env('bank_name')
        obj_category = Env('category')
        obj_label = Env('label')

        def parse(self, el):
            value = Attr('.', 'value')(self)
            # Autres comptes
            if value == 'AC':
                raise SkipItem()
            self.env['category'] = u'Interne' if value[0] == 'I' else u'Externe'
            if self.env['category'] == u'Interne':
                # TODO use after 'I'?
                _id = Regexp(CleanText('.'), r'- (\w+\d\w+)')(self) # at least one digit
                accounts = list(self.page.browser.get_accounts_list()) + list(self.page.browser.get_loans_list())
                # If it's an internal account, we should always find only one account with _id in it's id.
                # Type card account contains their parent account id, and should not be listed in recipient account.
                match = [acc for acc in accounts if _id in acc.id and acc.type != Account.TYPE_CARD]
                assert len(match) == 1
                match = match[0]
                self.env['id'] = match.id
                self.env['iban'] = match.iban
                self.env['bank_name'] = u"Caisse d'Épargne"
                self.env['label'] = match.label
            # Usual case `E-` or `UE-`
            elif value[1] == '-' or value[2] == '-':
                full = CleanText('.')(self)
                if full.startswith('- '):
                    self.logger.warning('skipping recipient without a label: %r', full)
                    raise SkipItem()

                # <recipient name> - <account number or iban> - <bank name (optional)> <optional last dash>
                mtc = re.match('(?P<label>.+) - (?P<id>[^-]+) -(?P<bank> [^-]*)?-?$', full)
                assert mtc
                self.env['id'] = self.env['iban'] = mtc.group('id')
                self.env['bank_name'] = (mtc.group('bank') and mtc.group('bank').strip()) or NotAvailable
                self.env['label'] = mtc.group('label')
            # Fcking corner case
            else:
                # former regex: '(?P<id>.+) - (?P<label>[^-]+) -( [^-]*)?-?$'
                # the strip is in case the string ends by ' -'
                mtc = CleanText('.')(self).strip(' -').split(' - ')
                # it needs to contain, at least, the id and the label
                assert len(mtc) >= 2
                self.env['id'] = mtc[0]
                self.env['iban'] = NotAvailable
                self.env['bank_name'] = NotAvailable
                self.env['label'] = mtc[1]


class TransferPage(TransferErrorPage, IndexPage):
    RECIPIENT_XPATH = '//select[@id="MM_VIREMENT_SAISIE_VIREMENT_ddlCompteCrediter"]/option'

    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Effectuer un virement")]')(self.doc))

    def can_transfer(self, account):
        for o in self.doc.xpath('//select[@id="MM_VIREMENT_SAISIE_VIREMENT_ddlCompteDebiter"]/option'):
            if Regexp(CleanText('.'), '- (\d+)')(o) in account.id:
                return True

    def get_origin_account_value(self, account):
        origin_value = [Attr('.', 'value')(o) for o in self.doc.xpath('//select[@id="MM_VIREMENT_SAISIE_VIREMENT_ddlCompteDebiter"]/option') if
                        Regexp(CleanText('.'), '- (\d+)')(o) in account.id]
        assert len(origin_value) == 1, 'error during origin account matching'
        return origin_value[0]

    def get_recipient_value(self, recipient):
        if recipient.category == u'Externe':
            recipient_value = [Attr('.', 'value')(o) for o in self.doc.xpath(self.RECIPIENT_XPATH) if
                               Regexp(CleanText('.'), '.* - ([A-Za-z0-9]*) -', default=NotAvailable)(o) == recipient.iban]
        elif recipient.category == u'Interne':
            recipient_value = [Attr('.', 'value')(o) for o in self.doc.xpath(self.RECIPIENT_XPATH) if
                               Regexp(CleanText('.'), '- (\d+)', default=NotAvailable)(o) and Regexp(CleanText('.'), '- (\d+)', default=NotAvailable)(o) in recipient.id]
        assert len(recipient_value) == 1, 'error during recipient matching'
        return recipient_value[0]

    def init_transfer(self, account, recipient, transfer):
        form = self.get_form(id='main')
        form['MM$VIREMENT$SAISIE_VIREMENT$ddlCompteDebiter'] = self.get_origin_account_value(account)
        form['MM$VIREMENT$SAISIE_VIREMENT$ddlCompteCrediter'] = self.get_recipient_value(recipient)
        form['MM$VIREMENT$SAISIE_VIREMENT$txtLibelleVirement'] = transfer.label
        form['MM$VIREMENT$SAISIE_VIREMENT$txtMontant$m_txtMontant'] = unicode(transfer.amount)
        form['__EVENTTARGET'] = 'MM$VIREMENT$m_WizardBar$m_lnkNext$m_lnkButton'
        if transfer.exec_date != datetime.today().date():
            form['MM$VIREMENT$SAISIE_VIREMENT$radioVirement'] = 'differe'
            form['MM$VIREMENT$SAISIE_VIREMENT$m_DateDiffere$txtDate'] = transfer.exec_date.strftime('%d/%m/%Y')
        form.submit()

    @method
    class iter_recipients(MyRecipients):
        pass

    def get_transfer_type(self):
        sepa_inputs = self.doc.xpath('//input[contains(@id, "MM_VIREMENT_SAISIE_VIREMENT_SEPA")]')
        intra_inputs = self.doc.xpath('//input[contains(@id, "MM_VIREMENT_SAISIE_VIREMENT_INTRA")]')

        assert not (len(sepa_inputs) and len(intra_inputs)), 'There are sepa and intra transfer forms'

        transfer_type = None
        if len(sepa_inputs):
            transfer_type = 'sepa'
        elif len(intra_inputs):
            transfer_type = 'intra'
        assert transfer_type, 'Sepa nor intra transfer form was found'
        return transfer_type

    def continue_transfer(self, origin_label, recipient_label, label):
        form = self.get_form(id='main')

        transfer_type = self.get_transfer_type()
        fill = lambda s, t: s % (t.upper(), t.capitalize())
        form['__EVENTTARGET'] = 'MM$VIREMENT$m_WizardBar$m_lnkNext$m_lnkButton'
        form[fill('MM$VIREMENT$SAISIE_VIREMENT_%s$m_Virement%s$txtIdentBenef', transfer_type)] = recipient_label
        form[fill('MM$VIREMENT$SAISIE_VIREMENT_%s$m_Virement%s$txtIdent', transfer_type)] = origin_label
        form[fill('MM$VIREMENT$SAISIE_VIREMENT_%s$m_Virement%s$txtRef', transfer_type)] = label
        form[fill('MM$VIREMENT$SAISIE_VIREMENT_%s$m_Virement%s$txtMotif', transfer_type)] = label
        form.submit()

    def go_add_recipient(self):
        form = self.get_form(id='main')
        link = self.doc.xpath(u'//a[span[contains(text(), "Ajouter un compte bénéficiaire")]]')[0]
        m = re.search("PostBackOptions?\([\"']([^\"']+)[\"'],\s*['\"]([^\"']+)?['\"]", link.attrib.get('href', ''))
        form['__EVENTTARGET'] = m.group(1)
        form['__EVENTARGUMENT'] = m.group(2)
        form.submit()


class TransferConfirmPage(TransferErrorPage, IndexPage):
    def build_doc(self, content):
        # The page have some <wbr> tags in the label content (spaces added each 40 characters if the character is not a space).
        # Consequently the label can't be matched with the original one. We delete these tags.
        content = content.replace(b'<wbr>', b'')
        return super(TransferErrorPage, self).build_doc(content)

    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Confirmer mon virement")]')(self.doc))

    def confirm(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'MM$VIREMENT$m_WizardBar$m_lnkNext$m_lnkButton'
        form.submit()

    def update_transfer(self, transfer, account=None, recipient=None):
        """update `Transfer` object with web information to use transfer check"""

        # transfer informations
        transfer.label = (
            CleanText(u'.//tr[td[contains(text(), "Motif de l\'opération")]]/td[not(@class)]')(self.doc) or
            CleanText(u'.//tr[td[contains(text(), "Libellé")]]/td[not(@class)]')(self.doc) or
            CleanText(u'.//tr[th[contains(text(), "Libellé")]]/td[not(@class)]')(self.doc)
        )
        transfer.exec_date = Date(CleanText('.//tr[th[contains(text(), "En date du")]]/td[not(@class)]'), dayfirst=True)(self.doc)
        transfer.amount = CleanDecimal('.//tr[td[contains(text(), "Montant")]]/td[not(@class)] | \
                                        .//tr[th[contains(text(), "Montant")]]/td[not(@class)]', replace_dots=True)(self.doc)
        transfer.currency = FrenchTransaction.Currency('.//tr[td[contains(text(), "Montant")]]/td[not(@class)] | \
                                                        .//tr[th[contains(text(), "Montant")]]/td[not(@class)]')(self.doc)

        # recipient transfer informations, update information if there is no OTP SMS validation
        if recipient:
            transfer.recipient_label = recipient.label
            transfer.recipient_id = recipient.id

            if recipient.category == u'Externe':
                for word in Upper(CleanText(u'.//tr[th[contains(text(), "Compte à créditer")]]/td[not(@class)]'))(self.doc).split():
                    if is_iban_valid(word):
                        transfer.recipient_iban = word
                        break
                else:
                    assert False, 'Unable to find IBAN (original was %s)' % recipient.iban
            else:
                transfer.recipient_iban = recipient.iban

        # origin account transfer informations, update information if there is no OTP SMS validation
        if account:
            transfer.account_id = account.id
            transfer.account_iban = account.iban
            transfer.account_label = account.label
            transfer.account_balance = account.balance

        return transfer


class ProTransferConfirmPage(TransferConfirmPage):
    def is_here(self):
        return bool(CleanText(u'//span[@id="MM_m_CH_lblTitle" and contains(text(), "Confirmez votre virement")]')(self.doc))

    def continue_transfer(self, origin_label, recipient, label):
        # Pro internal transfer initiation doesn't need a second step.
        pass

    def create_transfer(self, account, recipient, transfer):
        t = Transfer()
        t.currency = FrenchTransaction.Currency('//span[@id="MM_VIREMENT_CONF_VIREMENT_MontantVir"] | \
                                                 //span[@id="MM_VIREMENT_CONF_VIREMENT_lblMontantSelect"]')(self.doc)
        t.amount = CleanDecimal('//span[@id="MM_VIREMENT_CONF_VIREMENT_MontantVir"] | \
                                 //span[@id="MM_VIREMENT_CONF_VIREMENT_lblMontantSelect"]', replace_dots=True)(self.doc)
        t.account_iban = account.iban
        if recipient.category == u'Externe':
            for word in Upper(CleanText('//span[@id="MM_VIREMENT_CONF_VIREMENT_lblCptCrediterResult"]'))(self.doc).split():
                if is_iban_valid(word):
                    t.recipient_iban = word
                    break
            else:
                assert False, 'Unable to find IBAN (original was %s)' % recipient.iban
        else:
            t.recipient_iban = recipient.iban
        t.recipient_iban = recipient.iban
        t.account_id = unicode(account.id)
        t.recipient_id = unicode(recipient.id)
        t.account_label = account.label
        t.recipient_label = recipient.label
        t._account = account
        t._recipient = recipient
        t.label = CleanText('//span[@id="MM_VIREMENT_CONF_VIREMENT_Libelle"] | \
                             //span[@id="MM_VIREMENT_CONF_VIREMENT_lblMotifSelect"]')(self.doc)
        t.exec_date = Date(CleanText('//span[@id="MM_VIREMENT_CONF_VIREMENT_DateVir"]'), dayfirst=True)(self.doc)
        t.account_balance = account.balance
        return t


class TransferSummaryPage(TransferErrorPage, IndexPage):
    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Accusé de réception")]')(self.doc))

    def populate_reference(self, transfer):
        transfer.id = Regexp(CleanText(u'//p[contains(text(), "a bien été enregistré")]'), '(\d+)')(self.doc)
        return transfer


class ProTransferSummaryPage(TransferErrorPage, IndexPage):
    def is_here(self):
        return bool(CleanText('//span[@id="MM_m_CH_lblTitle" and contains(text(), "Accusé de réception")]')(self.doc))

    def populate_reference(self, transfer):
        transfer.id = Regexp(CleanText('//span[@id="MM_VIREMENT_AR_VIREMENT_lblVirementEnregistre"]'), '(\d+( - \d+)?)')(self.doc)
        return transfer


class ProTransferPage(TransferPage):
    RECIPIENT_XPATH = '//select[@id="MM_VIREMENT_SAISIE_VIREMENT_ddlCompteCrediterPro"]/option'

    def is_here(self):
        return CleanText(u'//span[contains(text(), "Créer une liste de virements")] | //span[contains(text(), "Réalisez un virement")]')(self.doc)

    @method
    class iter_recipients(MyRecipients):
        pass

    def init_transfer(self, account, recipient, transfer):
        form = self.get_form(id='main')
        form['MM$VIREMENT$SAISIE_VIREMENT$ddlCompteDebiter'] = self.get_origin_account_value(account)
        form['MM$VIREMENT$SAISIE_VIREMENT$ddlCompteCrediterPro'] = self.get_recipient_value(recipient)
        form['MM$VIREMENT$SAISIE_VIREMENT$Libelle'] = transfer.label
        form['MM$VIREMENT$SAISIE_VIREMENT$m_oDEI_Montant$m_txtMontant'] = unicode(transfer.amount)
        form['__EVENTTARGET'] = 'MM$VIREMENT$m_WizardBar$m_lnkNext$m_lnkButton'
        if transfer.exec_date != datetime.today().date():
            form['MM$VIREMENT$SAISIE_VIREMENT$virement'] = 'rbDiffere'
            form['MM$VIREMENT$SAISIE_VIREMENT$m_DateDiffere$JJ'] = transfer.exec_date.strftime('%d')
            form['MM$VIREMENT$SAISIE_VIREMENT$m_DateDiffere$MM'] = transfer.exec_date.strftime('%m')
            form['MM$VIREMENT$SAISIE_VIREMENT$m_DateDiffere$AA'] = transfer.exec_date.strftime('%y')
        form.submit()

    def go_add_recipient(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'MM$VIREMENT$SAISIE_VIREMENT$ddlCompteCrediterPro'
        form['MM$VIREMENT$SAISIE_VIREMENT$ddlCompteCrediterPro'] = 'AC'
        form.submit()


class CanceledAuth(Exception):
    pass


class SmsPageOption(LoggedPage, HTMLPage):
    pass


class SmsRequestStep(LoggedPage, JsonPage):
    pass


class SmsRequest(LoggedPage, JsonPage):
    def validate_key(self):
        return self.doc['step']['validationUnits'][0].keys()[0]

    def validation_id(self, key):
        return self.doc['step']['validationUnits'][0][key][0]['id']

    def get_saml(self):
        if not 'response' in self.doc:
            error = self.doc['phase']['previousResult']

            if error == 'FAILED_AUTHENTICATION':
                raise RecipientInvalidOTP()
            assert not error, 'Error during recipient validation: %s' % error

        return self.doc['response']['saml2_post']['samlResponse']

    def get_action(self):
        return self.doc['response']['saml2_post']['action']


class SmsPage(LoggedPage, HTMLPage):
    def on_load(self):
        error = CleanText('//p[@class="warning_trials_before"]')(self.doc)
        if error:
            raise AddRecipientBankError(message='Wrongcode, ' + error)

    def get_prompt_text(self):
        return CleanText(u'//td[@class="auth_info_prompt"]')(self.doc)

    def post_form(self):
        form = self.get_form(name='downloadAuthForm')
        form.submit()

    def check_canceled_auth(self):
        form = self.doc.xpath('//form[@name="downloadAuthForm"]')
        if form:
            self.location('/Pages/Logout.aspx')
            raise CanceledAuth()

    def set_browser_form(self):
        form = self.get_form(name='formAuth')
        self.browser.recipient_form = dict((k, v) for k, v in form.items() if v)
        self.browser.recipient_form['url'] = form.url


class AuthentPage(LoggedPage, HTMLPage):
    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Authentification réussie")]')(self.doc))

    def go_on(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'MM$RETOUR_OK_SOL$m_ChoiceBar$lnkRight'
        form.submit()


class RecipientPage(LoggedPage, HTMLPage):
    EVENTTARGET = 'MM$WIZARD_AJOUT_COMPTE_EXTERNE'
    FORM_FIELD_ADD = 'MM$WIZARD_AJOUT_COMPTE_EXTERNE$COMPTE_EXTERNE_ADD'

    def on_load(self):
        error = CleanText('//span[@id="MM_LblMessagePopinError"]')(self.doc)
        if error:
            raise AddRecipientBankError(message=error)

    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Ajouter un compte bénéficiaire")] |\
                                //h2[contains(text(), "Confirmer l\'ajout d\'un compte bénéficiaire")]')(self.doc))

    def post_recipient(self, recipient):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = '%s$m_WizardBar$m_lnkNext$m_lnkButton' % self.EVENTTARGET
        form['%s$m_RibIban$txtTitulaireCompte' % self.FORM_FIELD_ADD] = recipient.label
        for i in range(len(recipient.iban) // 4 + 1):
            form['%s$m_RibIban$txtIban%s' % (self.FORM_FIELD_ADD, str(i + 1))] = recipient.iban[4*i:4*i+4]
        form.submit()

    def confirm_recipient(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'MM$WIZARD_AJOUT_COMPTE_EXTERNE$m_WizardBar$m_lnkNext$m_lnkButton'
        form.submit()


class ProAddRecipientOtpPage(IndexPage):
    def on_load(self):
        error = CleanText('//div[@id="MM_m_CH_ValidationSummary" and @class="MessageErreur"]')(self.doc)
        if error:
            raise AddRecipientBankError(message='Wrongcode, ' + error)

    def is_here(self):
        return self.need_auth() and self.doc.xpath('//span[@id="MM_ANR_WS_AUTHENT_ANR_WS_AUTHENT_SAISIE_lblProcedure1"]')

    def set_browser_form(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = 'MM$ANR_WS_AUTHENT$m_WizardBar$m_lnkNext$m_lnkButton'
        self.browser.recipient_form = dict((k, v) for k, v in form.items())
        self.browser.recipient_form['url'] = form.url

    def get_prompt_text(self):
        return CleanText(u'////span[@id="MM_ANR_WS_AUTHENT_ANR_WS_AUTHENT_SAISIE_lblProcedure1"]')(self.doc)


class ProAddRecipientPage(RecipientPage):
    EVENTTARGET = 'MM$WIZARD_AJOUT_COMPTE_TIERS'
    FORM_FIELD_ADD = 'MM$WIZARD_AJOUT_COMPTE_TIERS$COMPTES_TIERS_ADD'

    def is_here(self):
        return CleanText('//span[@id="MM_m_CH_lblTitle" and contains(text(), "Ajoutez un compte tiers")] |\
                          //span[@id="MM_m_CH_lblTitle" and contains(text(), "Confirmez votre ajout")]')(self.doc)


class TransactionsDetailsPage(LoggedPage, HTMLPage):

    def is_here(self):
        return bool(CleanText(u'//h2[contains(text(), "Débits différés imputés")] | //span[@id="MM_m_CH_lblTitle" and contains(text(), "Débit différé imputé")]')(self.doc))

    @pagination
    @method
    class get_detail(TableElement):
        item_xpath = '//table[@id="MM_ECRITURE_GLOBALE_m_ExDGEcriture"]/tr[not(@class)] | //table[has-class("small special")]//tbody/tr[@class="rowClick"]'
        head_xpath = '//table[@id="MM_ECRITURE_GLOBALE_m_ExDGEcriture"]/tr[@class="DataGridHeader"]/td | //table[has-class("small special")]//thead/tr/th'

        col_date = u'Date'
        col_label = [u'Opération', u'Libellé']
        col_debit = u'Débit'
        col_credit = u'Crédit'

        def next_page(self):
            # only for new website, don't have any accounts with enough deferred card transactions on old webiste
            if self.page.doc.xpath('//a[contains(@id, "lnkSuivante") and not(contains(@disabled,"disabled")) \
                                    and not(contains(@class, "aspNetDisabled"))]'):
                form = self.page.get_form(id='main')
                form['__EVENTTARGET'] = "MM$ECRITURE_GLOBALE$lnkSuivante"
                form['__EVENTARGUMENT'] = ''
                fix_form(form)
                return form.request
            return

        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(TableCell('label'))
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj__debit = CleanDecimal(TableCell('debit'), replace_dots=True, default=0)
            obj__credit = CleanDecimal(TableCell('credit'), replace_dots=True, default=0)

            def obj_amount(self):
                return abs(Field('_credit')(self)) - abs(Field('_debit')(self))

    def go_form_to_summary(self):
        # return to first page
        to_history = Link(self.doc.xpath(u'//a[contains(text(), "Retour à l\'historique")]'))(self.doc)
        n = re.match('.*\([\'\"](MM\$.*?)[\'\"],.*\)$', to_history)
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = n.group(1)
        form.submit()

    def go_newsite_back_to_summary(self):
        form = self.get_form(id='main')
        form['__EVENTTARGET'] = "MM$ECRITURE_GLOBALE$lnkRetourHisto"
        form.submit()


class SubscriptionPage(LoggedPage, HTMLPage):
    def is_here(self):
        return self.doc.xpath('//h2[text()="e-Documents"]') or self.doc.xpath('//h2[text()="Relevés en ligne"]')

    def has_subscriptions(self):
        # This message appears if the customer has not activated the e-Documents yet
        return not bool(self.doc.xpath('//a[contains(text(), "Je souscris au service e-Documents")]'))

    @method
    class iter_subscription(ListElement):
        item_xpath = '//select[contains(@id, "ClientsBancaires")]/option'

        class item(ItemElement):
            klass = Subscription

            obj_id = Attr('.', 'value')
            obj_label = CleanText('.')
            obj_subscriber = CleanText('.')

            def condition(self):
                return 'Clos' not in Field('label')(self)

    def go_document_list(self, sub_id):
        target = Attr('//select[contains(@id, "ClientsBancaires")]', 'id')(self.doc)
        form = self.get_form(id='main')
        form['m_ScriptManager'] = target
        if 'palatine' in self.browser.BASEURL:
            form['MM$CONSULTATION_NUMERISATION_PALATINE$cboClientsBancaires'] = sub_id
        else:
            form['MM$COMPTE_EDOCUMENTS$ctrlEDocumentsConsultationDocument$cboClientsBancaires'] = sub_id

        form['__EVENTTARGET'] = target
        form.submit()

    def get_years(self):
        return self.doc.xpath('//select[contains(@id, "Annee")]/option')

    @method
    class iter_documents(ListElement):
        item_xpath = '//ul[@class="telecharger"]/li/a'

        class item(ItemElement):
            klass = Document

            obj_type = DocumentTypes.OTHER
            obj_format = 'pdf'
            obj_url = Regexp(Link('.'), r'WebForm_PostBackOptions\("(\S*)"')
            obj_id = Format('%s_%s_%s', Env('sub_id'), CleanText('./span', symbols='/',  replace=[(' ', '_')]), Regexp(Field('url'), r'ctl(.*)'))
            obj__event_id = Regexp(Attr('.', 'onclick'), r"val\('(.*)'\);", default=None)

            def obj_label(self):
                if 'Récapitulatif de frais bancaires' in CleanText('./span')(self.el):
                    return CleanText('./span')(self.el)
                return Format('%s %s', CleanText('./preceding::h3[1]'), CleanText('./span'))(self.el)

            def obj_date(self):
                if 'Récapitulatif de frais bancaires' in CleanText('./span')(self.el):
                    year = Regexp(CleanText('./span'), r'(\d{4})')(self.el)
                    return Date(dayfirst=True).filter('31/12/%s' %year)
                return Date(CleanText('./span'), dayfirst=True)(self.el)

    def download_document(self, document):
        form = self.get_form(id='main')
        form['m_ScriptManager'] = document.url
        form['__EVENTTARGET'] = document.url
        form['MM$COMPTE_EDOCUMENTS$ctrlEDocumentsConsultationDocument$eventId'] = document._event_id
        return form.submit()


class UnavailablePage(LoggedPage, HTMLPage):
    # This page seems to not be a 'LoggedPage'
    # but it also is a redirection page from a 'LoggedPage'
    # when the required page is not unavailable
    # so it can also redirect to a 'LoggedPage' page
    pass


class CreditCooperatifMarketPage(LoggedPage, HTMLPage):
    # Stay logged when landing on the new Linebourse
    # (which is used by Credit Cooperatif's connections)
    # The parsing is done in linebourse.api.pages
    def is_error(self):
        return CleanText('//caption[contains(text(),"Erreur")]')(self.doc)
