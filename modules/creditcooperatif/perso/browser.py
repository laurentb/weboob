# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from datetime import datetime

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import TransferInvalidDate, AddRecipientStep
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.date import new_date
from weboob.tools.value import Value
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    LoginPage, CreditLoggedPage, AccountsPage, TransactionsPage,
    TransactionsJSONPage, ComingTransactionsPage, IbanPage,
    RecipientsPage, TransferPage, EmittersPage, TransferDatesPage,
    TransferValidatePage, TransferPostPage, TransferFinishPage,
    ProfilePage,
    RecipientStartPage, RecipientIbanPage, RecipientChallengePage,
    RecipientFinishedPage, RecipientValidatePage,
)


__all__ = ['CreditCooperatif']


class CreditCooperatif(StatesMixin, LoginBrowser):
    BASEURL = "https://www.credit-cooperatif.coop"
    STATE_DURATION = 5

    loginpage = URL('/portail//particuliers/login.do', LoginPage)
    loggedpage = URL('/portail/particuliers/authentification.do', CreditLoggedPage)
    accountspage = URL('/portail/particuliers/mescomptes/synthese.do', AccountsPage)
    transactionpage = URL('/portail/particuliers/mescomptes/relevedesoperations.do', TransactionsPage)
    transactjsonpage = URL('/portail/particuliers/mescomptes/relevedesoperationsjson.do', TransactionsJSONPage)
    pre_comingpage = URL('/portail/particuliers/mescomptes/synthese/operationsencourslien.do', ComingTransactionsPage)
    comingpage = URL('/portail/particuliers/mescomptes/operationsavenir/avenir.do', ComingTransactionsPage)
    deffered_transactionpage = URL('/portail/particuliers/mescomptes/synthese/encourscblien.do', ComingTransactionsPage)
    iban = URL('/portail/particuliers/mesoperations/ribiban/telechargementribajax.do\?accountExternalNumber=(?P<account_id>.*)', IbanPage)

    transfer_start = URL(r'/portail/particuliers/mesoperations/virement/creer.do', TransferPage)
    emitters = URL(r'/portail/particuliers/mesoperations/virement/singledebitaccountsajax.do', EmittersPage)
    recipients = URL(r'/portail/particuliers/mesoperations/virement/singlecreditaccountsajax.do', RecipientsPage)

    transfer_date = URL(r'/portail/particuliers/mesoperations/virement/formvirponctajax.do', TransferDatesPage)
    transfer_validate = URL(r'/portail/particuliers/mesoperations/virement/creer/validerajax.do', TransferValidatePage)
    transfer_post = URL(r'/portail/particuliers/mesoperations/virement/creer/challenge.do', TransferPostPage)
    transfer_finish = URL(r'/portail/particuliers/mesoperations/virement/creer/executerajax.do', TransferFinishPage)

    profile = URL(r'/portail/particuliers/profil/monprofil.do', ProfilePage)

    recipient_start = URL(r'/portail/particuliers/mesoperations/beneficiaire/creeretape1.do', RecipientStartPage)
    recipient_iban = URL(r'/portail/particuliers/mesoperations/beneficiaire/creer.do', RecipientIbanPage)
    recipient_challenge = URL(r'/portail/particuliers/mesoperations/beneficiaire/creer/challenge.do', RecipientChallengePage)
    recipient_finished = URL(r'/portail/particuliers/mesoperations/beneficiaire/creer/validationetexecutionajax.do', RecipientFinishedPage)
    recipient_validate_country = URL(r'/portail/particuliers/mesoperations/beneficiaire/creer/validerbanqueajax.do', RecipientValidatePage)
    recipient_validate_iban = URL(r'/portail/particuliers/mesoperations/beneficiaire/creer/validerajax.do', RecipientValidatePage)

    def do_login(self):
        self.loginpage.stay_or_go()
        self.page.login(self.username, self.password)

        if self.loggedpage.is_here():
            error = self.page.get_error()
            if error is None:
                return
        else:
            raise BrowserUnavailable("not on the login page")

        raise BrowserIncorrectPassword(error)

    @need_login
    def get_profile(self):
        self.profile.go()
        return self.page.get_profile()

    @need_login
    def get_accounts_list(self):
        self.accountspage.go()

        return self.page.get_list()

    @need_login
    def get_history(self, account):
        data = {'accountExternalNumber': account.id}
        self.transactionpage.go(data=data)

        data = {'iDisplayLength':  400,
                'iDisplayStart':   0,
                'iSortCol_0':      0,
                'iSortingCols':    1,
                'sColumns':        '',
                'sEcho':           1,
                'sSortDir_0':      'asc',
                }
        self.transactjsonpage.go(data=data)

        return self.page.get_transactions()

    @need_login
    def get_coming(self, account):
        transactions = []
        data = {'accountExternalNumber': account.id}
        self.pre_comingpage.go(data=data)
        assert self.comingpage.is_here()
        # this page is "operations du jour" and may not have any date yet
        # so don't take transactions here, but it sets the "context"

        self.comingpage.go()
        assert self.comingpage.is_here()
        transactions += self.page.get_transactions(pattern='var jsonData =')
        self.deffered_transactionpage.go(data=data)
        transactions += self.page.get_transactions(pattern='var jsonData1 =', is_deffered=True)
        return sorted_transactions(transactions)

    @need_login
    def iter_recipients(self, account_id):
        self.transfer_start.go()
        self.emitters.go(data={
            'typevirradio': 'ponct',
        })
        if find_object(self.page.iter_emitters(), id=account_id) is None:
            return []

        self.recipients.go(data={
            'typevirradio': 'ponct',
            'nCompteDeb': account_id,
        })
        return self.page.iter_recipients()

    @need_login
    def init_transfer(self, transfer):
        date = new_date(transfer.exec_date or datetime.now())

        self.transfer_start.go()
        transfer_page = self.page

        self.emitters.go(data={
            'typevirradio': 'ponct',
        })
        self.recipients.go(data={
            'typevirradio': 'ponct',
            'nCompteDeb': transfer.account_id,
        })
        all_recipients = list(self.page.iter_recipients())

        self.transfer_date.go(data={
            'nCompteCred': transfer.recipient_id,
        })

        for page_date in self.page.iter_dates():
            if page_date >= date:
                date = page_date
                break
        else:
            raise TransferInvalidDate('The bank proposes no date greater or equal to the desired date')

        form = transfer_page.prepare_form(transfer=transfer, date=page_date)
        form.url = self.transfer_validate.build()
        form.submit()
        assert self.transfer_validate.is_here()

        form = transfer_page.prepare_form(transfer=transfer, date=page_date)
        form.url = self.transfer_post.build()
        form.submit()
        assert self.transfer_post.is_here()

        ret = self.page.get_transfer()
        if ret.recipient_iban:
            assert not ret.recipient_id # it's nowhere on the page
            recipient = find_object(all_recipients, iban=ret.recipient_iban)
            assert recipient
            ret.recipient_id = recipient.id
        return ret

    @need_login
    def execute_transfer(self, transfer):
        assert self.transfer_post.is_here()
        self.transfer_finish.go(method='POST', data='')
        assert self.transfer_finish.is_here()
        self.accountspage.go()
        return transfer

    @need_login
    def new_recipient(self, recipient, kwargs):
        if not kwargs.get('otp'):
            self.recipient_start.go()

            country = recipient.iban[:2]
            form = self.page.prepare_country(country)
            form.url = self.recipient_validate_country.build()
            form.submit()

            form.url = self.recipient_iban.build()
            form.req = None
            form.submit()

            form = self.page.prepare_recipient(recipient.iban, recipient.label)

            form.url = self.recipient_validate_iban.build()
            form.submit()

            form.url = self.recipient_challenge.build()
            form.req = None
            form.submit()

            challenge = self.page.get_challenge()
            msg = u'''Insérer votre carte dans le lecteur Sésame, Appuyez sur la touche "Réponse", Entrez votre code et validez, Entrez "%s" et validez, enfin renseignez le résultat''' % challenge

            raise AddRecipientStep(recipient, Value('otp', label=msg))
        else:
            form = self.page.prepare_otp(kwargs['otp'])
            form.url = self.recipient_finished.build()
            form.submit()

            self.accountspage.go()

