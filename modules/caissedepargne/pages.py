# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


import re

from decimal import Decimal

from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage
from weboob.tools.ordereddict import OrderedDict
from weboob.browser.filters.standard import Date, CleanDecimal, Regexp, CleanText
from weboob.browser.filters.html import Link
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_rib_valid, rib2iban
from weboob.exceptions import NoAccountsException
from weboob.deprecated.browser import BrokenPageError, BrowserUnavailable


class LoginPage(JsonPage):
    def get_response(self):
        return self.doc


class CenetLoginPage(HTMLPage):
    def login(self, username, password, nuser, codeCaisse):
        form = self.get_form(id='aspnetForm')

        form['__EVENTTARGET'] = "btn_authentifier"
        form['__EVENTARGUMENT'] = '{"CodeCaisse":"%s","NumeroBad":"%s","NumeroUsager":"%s",\
                                    "MotDePasse":"%s"}' % (codeCaisse, username, nuser, password)

        form.submit()


class GarbagePage(LoggedPage, HTMLPage):
    def on_load(self):
        go_back_link = Link('//a[@class="btn"]/@href')(self.doc)

        if go_back_link:
            assert len(go_back_link) == 1
            go_back_link = re.search('\(~deibaseurl\)(.*)$', go_back_link).group(1)
        self.page.browser.location(go_back_link)


class MessagePage(GarbagePage):
    def submit(self):
        form = self.get_form(name='leForm')

        form['signatur1'] = ['on']

        form.submit()


class _LogoutPage(HTMLPage):
    def on_load(self):
        try:
            raise BrowserUnavailable(CleanText('//*[@class="messErreur"]')(self.doc))
        except BrokenPageError:
            pass


class ErrorPage(_LogoutPage):
    pass


class UnavailablePage(HTMLPage):
    def on_load(self):
        try:
            raise BrowserUnavailable(CleanText('//div[@id="message_error_hs"]')(self.doc))
        except BrokenPageError:
            raise BrowserUnavailable()


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^CB (?P<text>.*?) FACT (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^RET(RAIT)? DAB (?P<dd>\d+)-(?P<mm>\d+)-.*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET(RAIT)? DAB (?P<text>.*?) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<HH>\d{2})H(?P<MM>\d{2})', re.IGNORECASE),
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
               ]


class IndexPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'Epargne liquide':            Account.TYPE_SAVINGS,
                     u'Compte Courant':             Account.TYPE_CHECKING,
                     u'Mes comptes':                Account.TYPE_CHECKING,
                     u'Mon épargne':                Account.TYPE_SAVINGS,
                     u'Mes autres comptes':         Account.TYPE_SAVINGS,
                     u'Compte Epargne et DAT':      Account.TYPE_SAVINGS,
                     u'Plan et Contrat d\'Epargne': Account.TYPE_SAVINGS,
                     u'Titres':                     Account.TYPE_MARKET,
                     u'Compte titres':              Account.TYPE_MARKET,
                     u'Mes crédits immobiliers':    Account.TYPE_LOAN,
                     u'Mes crédits renouvelables':  Account.TYPE_LOAN,
                     u'Mes crédits consommation':   Account.TYPE_LOAN,
                    }

    def on_load(self):
        # This page is sometimes an useless step to the market website.

        bourse_link = Link(u'//div[@id="MM_COMPTE_TITRE_pnlbourseoic"]//a[contains(text(), "Accédez à la consultation")]', default=None)(self.doc)

        if bourse_link:
            self.page.browser.location(bourse_link)

    def check_no_accounts(self):
        no_account_message = CleanText(u'//span[@id="MM_LblMessagePopinError"]/p[contains(text(), "Aucun compte disponible")]')(self.doc)

        if no_account_message:
            raise NoAccountsException(no_account_message)

    def _get_account_info(self, a):
        m = re.search("PostBack(Options)?\([\"'][^\"']+[\"'],\s*['\"]([HISTORIQUE_\w|SYNTHESE_ASSURANCE_CNP|BOURSE|COMPTE_TITRE][\d\w&]+)?['\"]", a.attrib.get('href', ''))
        if m is None:
            return None
        else:
            # it is in form CB&12345[&2]. the last part is only for new website
            # and is necessary for navigation.
            link = m.group(2)
            parts = link.split('&')
            info = {}
            if len(parts) > 1:
                info['type'] = parts[0]
                info['id'] = parts[1]
            else:
                id = re.search("([\d]+)", a.attrib.get('title'))
                info['type'] = link
                info['id'] = id.group(1)
            if info['type'] in ('SYNTHESE_ASSURANCE_CNP','SYNTHESE_EPARGNE'):
                info['acc_type'] = Account.TYPE_LIFE_INSURANCE
            if info['type'] in ('BOURSE', 'COMPTE_TITRE'):
                info['acc_type'] = Account.TYPE_MARKET
            info['link'] = link
            return info


    def _add_account(self, accounts, link, label, account_type, balance):
        info = self._get_account_info(link)
        if info is None:
            self.logger.warning('Unable to parse account %r: %r' % (label, link))
            return

        account = Account()
        account.id = info['id']
        if is_rib_valid(info['id']):
            account.iban = rib2iban(info['id'])
        account._info = info
        account.label = label
        account.type = info['acc_type'] if 'acc_type' in info else account_type
        account.balance = Decimal(FrenchTransaction.clean_amount(balance)) if balance else self.get_balance(account)
        account.currency = account.get_currency(balance)
        account._card_links = []

        if account._info['type'] == 'HISTORIQUE_CB' and account.id in accounts:
            a = accounts[account.id]
            if not a.coming:
                a.coming = Decimal('0.0')
            a.coming += account.balance
            a._card_links.append(account._info)
            return

        accounts[account.id] = account

    def get_balance(self, account):
        if not account.type == Account.TYPE_LIFE_INSURANCE:
            return NotAvailable
        self.go_history(account._info)
        balance = self.doc.xpath('.//tr[td[contains(., ' + account.id + ')]]/td[contains(@class, "somme")]')
        if len(balance) > 0:
            balance = CleanText('.')(balance[0])
            balance = Decimal(FrenchTransaction.clean_amount(balance)) if balance != u'' else NotAvailable
        else:
            balance = NotAvailable
        self.go_list()
        return balance

    def get_list(self):
        accounts = OrderedDict()

        # Old website
        for table in self.doc.xpath('//table[@cellpadding="1"]'):
            account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tr'):
                tds = tr.findall('td')
                if tr.attrib.get('class', '') == 'DataGridHeader':
                    account_type = self.ACCOUNT_TYPES.get(tds[1].text.strip()) or\
                                   self.ACCOUNT_TYPES.get(CleanText('.')(tds[2])) or\
                                   self.ACCOUNT_TYPES.get(CleanText('.')(tds[3]), Account.TYPE_UNKNOWN)
                else:
                    # On the same row, there are many accounts (for example a
                    # check accound and a card one).
                    if len(tds) > 4:
                        for i, a in enumerate(tds[2].xpath('./a')):
                            label = CleanText('.')(a)
                            balance = CleanText('.')(tds[-2].xpath('./a')[i])
                            self._add_account(accounts, a, label, account_type, balance)
                    # Only 4 tds on banque de la reunion website.
                    elif len(tds) == 4:
                        for i, a in enumerate(tds[1].xpath('./a')):
                            label = CleanText('.')(a)
                            balance = CleanText('.')(tds[-1].xpath('./a')[i])
                            self._add_account(accounts, a, label, account_type, balance)

        if len(accounts) == 0:
            # New website
            for table in self.doc.xpath('//div[@class="panel"]'):
                title = table.getprevious()
                if title is None:
                    continue
                account_type = self.ACCOUNT_TYPES.get(CleanText('.')(title), Account.TYPE_UNKNOWN)
                for tr in table.xpath('.//tr'):
                    tds = tr.findall('td')
                    for i in xrange(len(tds)):
                        a = tds[i].find('a')
                        if a is not None:
                            break

                    if a is None:
                        continue

                    label = CleanText('.')(tds[0])
                    balance = CleanText('.')(tds[-1])

                    self._add_account(accounts, a, label, account_type, balance)

        return accounts.itervalues()

    def get_loan_list(self):
        accounts = OrderedDict()
        # New website
        for table in self.doc.xpath('//div[@class="panel"]'):
            title = table.getprevious()
            if title is None:
                continue
            account_type = self.ACCOUNT_TYPES.get(CleanText('.')(title), Account.TYPE_UNKNOWN)
            for tr in table.xpath('./table/tbody/tr[contains(@id,"MM_SYNTHESE_CREDITS") and contains(@id,"IdTrGlobal")]'):
                tds = tr.findall('td')
                if len(tds) == 0 :
                    continue
                for i in tds[0].xpath('.//a/strong'):
                    label = i.text.strip()
                    break
                balance = Decimal(FrenchTransaction.clean_amount(CleanText('.')(tds[-1])))
                account = Account()
                account.id = label.split(' ')[-1]
                account.label = unicode(label)
                account.type = account_type
                account.balance = -abs(balance)
                account.currency = account.get_currency(CleanText('.')(tds[-1]))
                account._card_links = []
                accounts[account.id] = account
        return accounts.itervalues()

    def go_list(self):
        form = self.get_form(name='main')

        form['__EVENTARGUMENT'] = "CPTSYNT0"

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            form['__EVENTTARGET'] = "Menu_AJAX"
            form['m_ScriptManager'] = "m_ScriptManager|Menu_AJAX"
        else:
            # New website
            form['__EVENTTARGET'] = "MM$m_PostBack"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$m_PostBack"

        for name in ['MM$HISTORIQUE_COMPTE$btnCumul','Cartridge$imgbtnMessagerie','MM$m_CH$ButtonImageFondMessagerie',\
                     'MM$m_CH$ButtonImageMessagerie']:
            try:
                del form[name]
            except KeyError:
                pass

        form.submit()

    def go_loan_list(self):
        form = self.get_form(name='main')

        form['__EVENTARGUMENT'] = "CRESYNT0"

        if "MM$m_CH$IsMsgInit" in form:
            # Old website
            pass
        else:
            # New website
            form['__EVENTTARGET'] = "MM$m_PostBack"
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$m_PostBack"

        for name in ['MM$HISTORIQUE_COMPTE$btnCumul','Cartridge$imgbtnMessagerie','MM$m_CH$ButtonImageFondMessagerie',\
                     'MM$m_CH$ButtonImageMessagerie']:
            try:
                del form[name]
            except KeyError:
                pass

        form.submit()

    def go_history(self, info, is_cbtab=False):
        form = self.get_form(name='main')

        form['__EVENTTARGET'] = 'MM$%s' % (info['type'] if is_cbtab else 'SYNTHESE')
        form['__EVENTARGUMENT'] = info['link']

        if "MM$m_CH$IsMsgInit" in form and form['MM$m_CH$IsMsgInit'] == "0":
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$SYNTHESE"

        for name in ['MM$HISTORIQUE_COMPTE$btnCumul','Cartridge$imgbtnMessagerie','MM$m_CH$ButtonImageFondMessagerie',\
                     'MM$m_CH$ButtonImageMessagerie']:
            try:
                del form[name]
            except KeyError:
                pass

        form.submit()

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
                m = re.search('(\d{2}\/\d{2}\/\d{4})', card_debit_date[0].text)
                assert m
                t.date = Date(dayfirst=True).filter(m.group(1))
            if t.date is NotAvailable:
                continue
            if 'tot dif' in t.raw.lower():
                t.deleted = True
            t.set_amount(credit, debit)
            yield t

            i += 1

    def get_cbtabs(self):
        cbtabs = []
        for href in self.doc.xpath('//ul[@class="onglets"]/li/a[contains(text(), "CB")]/@href'):
            m = re.search('(DETAIL[^"]+)', href)
            if m:
                cbtabs.append(m.group(1))
        return cbtabs

    def go_next(self):
        # <a id="MM_HISTORIQUE_CB_lnkSuivante" class="next" href="javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions(&quot;MM$HISTORIQUE_CB$lnkSuivante&quot;, &quot;&quot;, true, &quot;&quot;, &quot;&quot;, false, true))">Suivant<span class="arrow">></span></a>

        link = self.doc.xpath('//a[contains(@id, "lnkSuivante")]')
        if len(link) == 0 or 'disabled' in link[0].attrib:
            return False

        account_type = 'COMPTE'
        m = re.search('HISTORIQUE_(\w+)', link[0].attrib['href'])
        if m:
            account_type = m.group(1)

        form = self.get_form(name='main')

        form['__EVENTTARGET'] = "MM$HISTORIQUE_%s$lnkSuivante" % account_type
        form['__EVENTARGUMENT'] = ''

        if "MM$m_CH$IsMsgInit" in form and form['MM$m_CH$IsMsgInit'] == "N":
            form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$HISTORIQUE_COMPTE$lnkSuivante"

        for name in ['MM$HISTORIQUE_COMPTE$btnCumul','Cartridge$imgbtnMessagerie','MM$m_CH$ButtonImageFondMessagerie',\
                     'MM$m_CH$ButtonImageMessagerie']:
            try:
                del form[name]
            except KeyError:
                pass

        form.submit()

        return True

    def go_life_insurance(self, account):
        link = self.doc.xpath('//tr[td[contains(., ' + account.id + ') ]]//a')[0]
        m = re.search("PostBackOptions?\([\"']([^\"']+)[\"'],\s*['\"](REDIR_ASS_VIE[\d\w&]+)?['\"]", link.attrib.get('href', ''))
        if m is not None:
            form = self.get_form(name='main')

            form['__EVENTTARGET'] = m.group(1)
            form['__EVENTARGUMENT'] = m.group(2)

            if "MM$m_CH$IsMsgInit" in form and form['MM$m_CH$IsMsgInit'] == "0":
                form['m_ScriptManager'] = "MM$m_UpdatePanel|MM$SYNTHESE"

            for name in ['MM$HISTORIQUE_COMPTE$btnCumul','Cartridge$imgbtnMessagerie','MM$m_CH$ButtonImageFondMessagerie',\
                         'MM$m_CH$ButtonImageMessagerie']:
                try:
                    del form[name]
                except KeyError:
                    pass

            form.submit()


class MarketPage(LoggedPage, HTMLPage):
    def is_error(self):
        try:
            return self.doc.xpath('//caption')[0].text == "Erreur"
        except IndexError:
            return False
        except AssertionError:
            return True

    def parse_decimal(self, td):
        value = CleanText('.')(td)
        if value and value != '-':
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
        return len(self.doc.xpath('//form[@class="choixCompte"]//option[@selected and contains(text(), "%s")]' % account._info['id']))

    def get_compte(self, account):
        return self.doc.xpath('//option[contains(text(), "%s")]/@value' % account._info['id'])[0]

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
            diff = self.parse_decimal(tr.xpath('./td[6]')[0])
            inv.quantity = self.parse_decimal(tr.xpath('./td[2]')[0])
            inv.unitvalue = self.parse_decimal(tr.xpath('./td[3]')[0])
            date = CleanText('.')(tr.xpath('./td[4]')[0])
            inv.vdate = Date(dayfirst=True).filter(date) if date and date != '-' else NotAvailable
            inv.unitprice = self.calc(inv.unitvalue, diff)
            inv.valuation = self.parse_decimal(tr.xpath('./td[5]')[0])
            inv.diff = self.get_diff(inv.valuation, self.calc(inv.valuation, diff))

            yield inv

    def calc(self, value, diff):
        if value is NotAvailable or diff is NotAvailable:
            return NotAvailable
        return Decimal(value) / (1 + Decimal(diff)/100)

    def get_diff(self, valuation, calc):
        if valuation is NotAvailable or calc is NotAvailable:
            return NotAvailable
        return valuation - calc

    def split_label_code(self, libelle):
        m = re.search('FR\d+', libelle[-1])
        if m:
            return ' '.join(libelle[:-1]), libelle[-1]
        else:
            return ' '.join(libelle), NotAvailable
