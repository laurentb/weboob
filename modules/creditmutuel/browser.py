# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from datetime import datetime
from dateutil.relativedelta import relativedelta
from random import randint

from weboob.tools.compat import basestring
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.profiles import Wget
from weboob.browser.url import URL
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Transfer, TransferError, Account

from .pages import LoginPage, LoginErrorPage, AccountsPage, UserSpacePage, \
                   OperationsPage, CardPage, ComingPage, NoOperationsPage, \
                   TransfertPage, ChangePasswordPage, VerifCodePage,       \
                   EmptyPage, PorPage, IbanPage, NewHomePage, RedirectPage, \
                   LIAccountsPage


__all__ = ['CreditMutuelBrowser']


class CreditMutuelBrowser(LoginBrowser):
    PROFILE = Wget()
    TIMEOUT = 30
    BASEURL = 'https://www.creditmutuel.fr'

    login =       URL('/groupe/fr/index.html',
                      '/(?P<subbank>.*)/fr/$',
                      '/(?P<subbank>.*)/fr/banques/accueil.html',
                      '/(?P<subbank>.*)/fr/banques/particuliers/index.html',
                      LoginPage)
    login_error = URL('/(?P<subbank>.*)/fr/identification/default.cgi',      LoginErrorPage)
    accounts =    URL('/(?P<subbank>.*)/fr/banque/situation_financiere.cgi',
                      '/(?P<subbank>.*)/fr/banque/situation_financiere.html',
                      AccountsPage)
    user_space =  URL('/(?P<subbank>.*)/fr/banque/espace_personnel.aspx',    UserSpacePage)
    operations =  URL('/(?P<subbank>.*)/fr/banque/mouvements.cgi.*',
                      '/(?P<subbank>.*)/fr/banque/mouvements.html.*',
                      '/(?P<subbank>.*)/fr/banque/nr/nr_devbooster.aspx.*',
                      OperationsPage)
    coming =      URL('/(?P<subbank>.*)/fr/banque/mvts_instance.cgi.*',      ComingPage)
    card =        URL('/(?P<subbank>.*)/fr/banque/operations_carte.cgi.*',   CardPage)
    noop =        URL('/(?P<subbank>.*)/fr/banque/CR/arrivee.asp.*',         NoOperationsPage)
    info =        URL('/(?P<subbank>.*)/fr/banque/BAD.*',                    EmptyPage)
    transfert =   URL('/(?P<subbank>.*)/fr/banque/virements/vplw_vi.html',   EmptyPage)
    transfert_2 = URL('/(?P<subbank>.*)/fr/banque/virements/vplw_cmweb.aspx.*', TransfertPage)
    change_pass = URL('/(?P<subbank>.*)/fr/validation/change_password.cgi',  ChangePasswordPage)
    verify_pass = URL('/(?P<subbank>.*)/fr/validation/verif_code.cgi.*',     VerifCodePage)
    empty =       URL('/(?P<subbank>.*)/fr/banques/index.html',
                      '/(?P<subbank>.*)/fr/banque/paci_beware_of_phishing.*',
                      '/(?P<subbank>.*)/fr/validation/(?!change_password|verif_code).*',
                      '/(?P<subbank>.*)/fr/banque/paci_engine/static_content_manager.aspx',
                      '/(?P<subbank>.*)/fr/banque/DELG_Gestion.*',
                      EmptyPage)
    por =         URL('/(?P<subbank>.*)/fr/banque/POR_ValoToute.aspx',
                      '/(?P<subbank>.*)/fr/banque/POR_SyntheseLst.aspx',
                      PorPage)
    li =          URL('/(?P<subbank>.*)/fr/assurances/profilass.aspx\?domaine=epargne',
                      '/(?P<subbank>.*)/fr/assurances/consultation/WI_ASSAVI', LIAccountsPage)
    iban =        URL('/(?P<subbank>.*)/fr/banque/rib.cgi', IbanPage)

    new_home =    URL('/fr/banque/pageaccueil.html',
                      '/fr/banque/welcome_pack.html', NewHomePage)
    new_accounts = URL('/fr/banque/comptes-et-contrats.html', AccountsPage)
    new_operations = URL('/fr/banque/mouvements.cgi',
                         '/fr/banque/mouvements.html', OperationsPage)
    new_por = URL('/fr/banque/POR_ValoToute.aspx',
                  '/fr/banque/POR_SyntheseLst.aspx', PorPage)
    new_iban = URL('/fr/banque/rib.cgi', IbanPage)

    redirect = URL('/fr/banque/paci_engine/static_content_manager.aspx', RedirectPage)

    currentSubBank = None
    is_new_website = False

    __states__ = ['currentSubBank']

    def do_login(self):
        # Clear cookies.
        self.do_logout()

        self.login.go()

        if not self.page.logged:
            self.page.login(self.username, self.password)

            if not self.page.logged or self.login_error.is_here():
                raise BrowserIncorrectPassword()

        if not self.is_new_website:
            self.getCurrentSubBank()

    @need_login
    def get_accounts_list(self):
        if self.currentSubBank is None and not self.is_new_website:
            self.getCurrentSubBank()
        accounts = []
        if not self.is_new_website:
            for a in self.accounts.stay_or_go(subbank=self.currentSubBank).iter_accounts():
                accounts.append(a)
            self.iban.go(subbank=self.currentSubBank).fill_iban(accounts)
            self.por.go(subbank=self.currentSubBank).add_por_accounts(accounts)
            for acc in self.li.go(subbank=self.currentSubBank).iter_li_accounts():
                accounts.append(acc)
        else:
            for a in self.new_accounts.stay_or_go().iter_accounts():
                accounts.append(a)
            self.new_iban.go().fill_iban(accounts)
            self.new_por.go().add_por_accounts(accounts)
        return accounts

    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a

    def getCurrentSubBank(self):
        # the account list and history urls depend on the sub bank of the user
        url = urlparse(self.url)
        self.currentSubBank = url.path.lstrip('/').split('/')[0]

    def list_operations(self, page_url):
        if page_url.startswith('/') or page_url.startswith('https'):
            self.location(page_url)
        elif not self.is_new_website:
            self.location('%s/%s/fr/banque/%s' % (self.BASEURL, self.currentSubBank, page_url))
        else:
            self.location('%s/fr/banque/%s' % (self.BASEURL, page_url))

        if self.li.is_here():
            return self.page.iter_history()

        if not self.operations.is_here():
            return iter([])

        return self.pagination(lambda: self.page.get_history())

    def get_history(self, account):
        transactions = []
        last_debit = None
        if not account._link_id:
            return iter([])
        for tr in self.list_operations(account._link_id):
            # to prevent redundancy with card transactions, we do not
            # store 'RELEVE CARTE' transaction.
            if not tr.raw.startswith('RELEVE CARTE'):
                transactions.append(tr)
            elif last_debit is None:
                # we set the debit date to last day of month so we need to do the same form last_debit
                last_debit = (tr.date + relativedelta(day=31))

        coming_link = self.page.get_coming_link() if self.operations.is_here() else None
        if coming_link is not None:
            for tr in self.list_operations(coming_link):
                transactions.append(tr)

        for card_link in account._card_links:
            for tr in self.list_operations(card_link):
                if last_debit is None or tr.date > last_debit:
                    tr._is_coming = True
                transactions.append(tr)

        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        return transactions

    def get_investment(self, account):
        if account._is_inv:
            if account.type == Account.TYPE_MARKET:
                if not self.is_new_website:
                    self.por.go(subbank=self.currentSubBank)
                else:
                    self.new_por.go()
                self.page.send_form(account)
            elif account.type == Account.TYPE_LIFE_INSURANCE:
                if not account._link_inv:
                    return iter([])
                self.location(account._link_inv)
            return self.page.iter_investment()
        return iter([])

    def transfer(self, account, to, amount, reason=None):
        if self.is_new_website:
            raise NotImplementedError()
        # access the transfer page
        self.transfert.go(subbank=self.currentSubBank)

        # fill the form
        form = self.page.get_form(xpath="//form[@id='P:F']")
        try:
            form['data_input_indiceCompteADebiter'] = self.page.get_from_account_index(account)
            form['data_input_indiceCompteACrediter'] = self.page.get_to_account_index(to)
        except ValueError as e:
            raise TransferError(e.message)
        form['[t:dbt%3adouble;]data_input_montant_value_0_'] = '%s' % str(amount).replace('.', ',')
        if reason is not None:
            form['[t:dbt%3astring;x(27)]data_input_libelleCompteDebite'] = reason
            form['[t:dbt%3astring;x(31)]data_input_motifCompteCredite'] = reason
        del form['_FID_GoCancel']
        del form['_FID_DoValidate']
        form['_FID_DoValidate.x'] = str(randint(3, 125))
        form['_FID_DoValidate.y'] = str(randint(3, 22))
        form.submit()

        # look for known errors
        content = self.page.get_unicode_content()
        insufficient_amount_message =     u'Le montant du virement doit être positif, veuillez le modifier'
        maximum_allowed_balance_message = u'Montant maximum autorisé au débit pour ce compte'

        if insufficient_amount_message in content:
            raise TransferError('The amount you tried to transfer is too low.')

        if maximum_allowed_balance_message in content:
            raise TransferError('The maximum allowed balance for the target account has been / would be reached.')

        # look for the known "all right" message
        ready_for_transfer_message = u'Confirmer un virement entre vos comptes'
        if ready_for_transfer_message not in content:
            raise TransferError('The expected message "%s" was not found.' % ready_for_transfer_message)

        # submit the confirmation form
        form = self.page.get_form(xpath="//form[@id='P:F']")
        del form['_FID_DoConfirm']
        form['_FID_DoConfirm.x'] = str(randint(3, 125))
        form['_FID_DoConfirm.y'] = str(randint(3, 22))
        submit_date = datetime.now()
        form.submit()

        # look for the known "everything went well" message
        content = self.page.get_unicode_content()
        transfer_ok_message = u'Votre virement a &#233;t&#233; ex&#233;cut&#233;'
        if transfer_ok_message not in content:
            raise TransferError('The expected message "%s" was not found.' % transfer_ok_message)

        # We now have to return a Transfer object
        transfer = Transfer(submit_date.strftime('%Y%m%d%H%M%S'))
        transfer.amount = amount
        transfer.origin = account
        transfer.recipient = to
        transfer.date = submit_date
        return transfer
