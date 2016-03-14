# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from mechanize import Cookie

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.deprecated.browser.parsers.jsonparser import JsonParser
from weboob.tools.ordereddict import OrderedDict

from .pages import LoginPage, ErrorPage, AccountsPage, CardsPage, HistoryPage, CardHistoryPage, OrderPage


__all__ = ['SGProfessionalBrowser', 'SGEnterpriseBrowser']


class SGPEBrowser(Browser):
    PROTOCOL = 'https'
    ENCODING = 'ISO-8859-1'

    def __init__(self, *args, **kwargs):
        self.PAGES = OrderedDict((
            ('%s://%s/Pgn/.+PageID=SoldeV3&.+' % (self.PROTOCOL, self.DOMAIN), AccountsPage),
            ('%s://%s/Pgn/.+PageID=Cartes&.+' % (self.PROTOCOL, self.DOMAIN), CardsPage),
            ('%s://%s/Pgn/.+PageID=ReleveCompteV3&.+' % (self.PROTOCOL, self.DOMAIN), HistoryPage),
            ('%s://%s/Pgn/.+PageID=ReleveCarte&.+' % (self.PROTOCOL, self.DOMAIN), CardHistoryPage),
            ('%s://%s/ord-web/ord//ord-liste-compte-emetteur.json' % (self.PROTOCOL, self.DOMAIN), (OrderPage, JsonParser())),
            ('%s://%s/authent\.html' % (self.PROTOCOL, self.DOMAIN), ErrorPage),
            ('%s://%s/' % (self.PROTOCOL, self.DOMAIN), LoginPage),
        ))
        Browser.__init__(self, *args, **kwargs)

    def is_logged(self):
        if not self.page or self.is_on_page(LoginPage):
            return False

        error = self.page.get_error()
        if error is None:
            return True

        return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN + '/', no_login=True)

        c = Cookie(0, 'PILOTE_OOBA', 'true',
                   None, False,
                   '.' + self.DOMAIN, True, True,
                   '/', False, False, None, False, None, None, {})
        cookiejar = self._ua_handlers["_cookies"].cookiejar
        cookiejar.set_cookie(c)
        self.page.login(self.username, self.password)

        # force page change
        if not self.is_on_page(AccountsPage):
            self.accounts(no_login=True)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def accounts(self, no_login=False):
        self.location('/Pgn/NavigationServlet?PageID=SoldeV3&MenuID=%sCPT&Classeur=1&NumeroPage=1' % self.MENUID, no_login=no_login)

    def cards(self):
        doc = self.get_document(self.openurl('/Pgn/NavigationServlet?PageID=CartesFutures&MenuID=%sOPF&Classeur=1&NumeroPage=1&PageDetail=1' % self.MENUID))
        try:
            url = doc.xpath('//iframe[@name="cartes"]')[0].attrib['src']
        except IndexError:
            return False
        else:
            self.location(url)
            return True

    def history(self, _id, page=1):
        if page > 1:
            pgadd = '&page_numero_page_courante=%s' % page
        else:
            pgadd = ''
        self.location('/Pgn/NavigationServlet?PageID=ReleveCompteV3&MenuID=%sCPT&Classeur=1&Rib=%s&NumeroPage=1%s' % (self.MENUID, _id, pgadd))

    def card_history(self, rib, _id, date, currency, page=1):
        self.location('/Pgn/NavigationServlet?PageID=ReleveCarte&MenuID=%sOPF&Classeur=1&Rib=%s&Carte=%s&Date=%s&PageDetail=%s&Devise=%s' % (self.MENUID, rib, _id, date, page, currency))

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.accounts()

        assert self.is_on_page(AccountsPage)
        accounts = []
        for acc in self.page.get_list():
            accounts.append(acc)

        if self.cards():
            assert self.is_on_page(CardsPage)
            for acc in self.page.get_list():
                accounts.append(acc)

        self.location('/ord-web/ord//ord-liste-compte-emetteur.json')
        for acc in accounts:
            acc.iban = self.page.get_iban(acc.id)
            yield acc

    def get_account(self, _id):
        for a in self.get_accounts_list():
            if a.id == _id:
                yield a

    def iter_history(self, account):
        if account._is_card:
            for history_link in [account.id, account._link]:
                page = 1
                while page:
                    self.card_history(account._link_rib, history_link, account._link_date, account._link_currency, page)
                    assert self.is_on_page(CardHistoryPage)
                    for tr in self.page.iter_transactions():
                        yield tr
                    if self.page.has_next():
                        page += 1
                    else:
                        page = False
        else:
            page = 1
            basecount = 0
            while page:
                self.history(account.id, page)
                assert self.is_on_page(HistoryPage)
                for transaction in self.page.iter_transactions(account, basecount):
                    basecount = int(transaction._index) + 1
                    yield transaction
                if self.page.has_next():
                    page += 1
                else:
                    page = False

    def iter_investment(self, account):
        raise NotImplementedError()


class SGProfessionalBrowser(SGPEBrowser):
    DOMAIN = 'professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'


class SGEnterpriseBrowser(SGPEBrowser):
    DOMAIN = 'entreprises.secure.societegenerale.fr'
    LOGIN_FORM = 'auth'
    MENUID = 'BANREL'
    CERTHASH = '2231d5ddb97d2950d5e6fc4d986c23be4cd231c31ad530942343a8fdcc44bb99'
