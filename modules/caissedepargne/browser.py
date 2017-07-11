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
import datetime

from weboob.browser import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.capabilities.bank import Account, AddRecipientStep, Recipient, TransferBankError
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.profile import Profile
from weboob.browser.exceptions import BrowserHTTPNotFound, ClientError
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.compat import urljoin
from weboob.tools.value import Value
from weboob.tools.decorators import retry
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    IndexPage, ErrorPage, MarketPage, LifeInsurance, GarbagePage,
    MessagePage, LoginPage,
    TransferPage, ProTransferPage, TransferConfirmPage, TransferSummaryPage,
    SmsPage, AuthentPage, RecipientPage, CanceledAuth, CaissedepargneKeyboard,
)


__all__ = ['CaisseEpargne']


class ChangeBrowser(Exception):
    pass


class CaisseEpargne(LoginBrowser, StatesMixin):
    BASEURL = "https://www.caisse-epargne.fr"
    STATE_DURATION = 5

    login = URL('/authentification/manage\?step=identification&identifiant=(?P<login>.*)',
                'https://.*/login.aspx', LoginPage)
    account_login = URL('/authentification/manage\?step=account&identifiant=(?P<login>.*)&account=(?P<accountType>.*)', LoginPage)
    recipient = URL('https://.*/Portail.aspx.*', RecipientPage)
    transfer = URL('https://.*/Portail.aspx.*', TransferPage)
    transfer_summary = URL('https://.*/Portail.aspx.*', TransferSummaryPage)
    transfer_confirm = URL('https://.*/Portail.aspx.*', TransferConfirmPage)
    pro_transfer = URL('https://.*/Portail.aspx.*', ProTransferPage)
    authent = URL('https://.*/Portail.aspx.*', AuthentPage)
    home = URL('https://.*/Portail.aspx.*', IndexPage)
    home_tache = URL('https://.*/Portail.aspx\?tache=(?P<tache>).*', IndexPage)
    error = URL('https://.*/login.aspx',
                'https://.*/Pages/logout.aspx.*',
                'https://.*/particuliers/Page_erreur_technique.aspx.*', ErrorPage)
    market = URL('https://.*/Pages/Bourse.*',
                 'https://www.caisse-epargne.offrebourse.com/ReroutageSJR',
                 'https://www.caisse-epargne.offrebourse.com/Portefeuille.*', MarketPage)
    life_insurance = URL('https://.*/Assurance/Pages/Assurance.aspx',
                         'https://www.extranet2.caisse-epargne.fr.*', LifeInsurance)
    message = URL('https://www.caisse-epargne.offrebourse.com/DetailMessage\?refresh=O', MessagePage)
    garbage = URL('https://www.caisse-epargne.offrebourse.com/Portefeuille',
                  'https://www.caisse-epargne.fr/particuliers/.*/emprunter.aspx',
                  'https://.*/particuliers/emprunter.*',
                  'https://.*/particuliers/epargner.*', GarbagePage)
    sms = URL('https://www.icgauth.caisse-epargne.fr/dacswebssoissuer/AuthnRequestServlet', SmsPage)

    __states__ = ('BASEURL', 'multi_type', 'typeAccount', 'is_cenet_website', 'recipient_form')

    def __init__(self, nuser, *args, **kwargs):
        self.BASEURL = kwargs.pop('domain', self.BASEURL)
        if not self.BASEURL.startswith('https://'):
            self.BASEURL = 'https://%s' % self.BASEURL

        self.is_cenet_website = False
        self.multi_type = False
        self.accounts = None
        self.loans = None
        self.typeAccount = 'WE'
        self.nuser = nuser
        self.recipient_form = None

        super(CaisseEpargne, self).__init__(*args, **kwargs)

    def load_state(self, state):
        if 'recipient_form' in state and state['recipient_form'] is not None:
            super(CaisseEpargne, self).load_state(state)
            self.logged = True

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        if not self.username or not self.password:
            raise BrowserIncorrectPassword()

        # Reset domain to log on pro website if first login attempt failed on personal website.
        if self.multi_type:
            self.BASEURL = 'https://www.caisse-epargne.fr'
            self.typeAccount = 'WP'

        data = self.login.go(login=self.username).get_response()

        if data is None:
            raise BrowserIncorrectPassword()

        if "authMode" in data and data['authMode'] == 'redirect':
            raise ChangeBrowser()

        if len(data['account']) > 1:
            self.multi_type = True
            data = self.account_login.go(login=self.username, accountType=self.typeAccount).get_response()

        assert data is not None

        typeAccount = data['account'][0]

        idTokenClavier = data['keyboard']['Id']
        vk = CaissedepargneKeyboard(data['keyboard']['ImageClavier'], data['keyboard']['Num']['string'])
        newCodeConf = vk.get_string_code(self.password)

        playload = {
            'idTokenClavier': idTokenClavier,
            'newCodeConf': newCodeConf,
            'auth_mode': 'ajax',
            'nuusager': self.nuser.encode('utf-8'),
            'codconf': self.password,
            'typeAccount': typeAccount,
            'step': 'authentification',
            'ctx': 'typsrv=WE',
            'clavierSecurise': '1',
            'nuabbd': self.username
        }

        res = self.location(data['url'], params=playload)
        if not res.page:
            raise BrowserUnavailable()

        response = res.page.get_response()

        assert response is not None

        if not response['action']:
            if not self.typeAccount == 'WP' and self.multi_type:
                # If we haven't test PRO espace we check before raising wrong pass
                self.do_login()
                return
            raise BrowserIncorrectPassword(response['error'])

        self.BASEURL = urljoin(data['url'], '/')

        try:
            self.home.go()
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        if self.accounts is None:
            if self.home.is_here():
                self.page.check_no_accounts()
                self.page.go_list()
            else:
                self.home.go()

            self.accounts = list(self.page.get_list())
            for account in self.accounts:
                if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
                    self.home_tache.go(tache='CPTSYNT0')
                    self.page.go_history(account._info)

                    if self.message.is_here():
                        self.page.submit()
                        self.page.go_history(account._info)

                    # Some users may not have access to this.
                    if not self.market.is_here():
                        continue

                    self.page.submit()

                    if self.page.is_error():
                        continue

                    self.garbage.go()

                    if self.garbage.is_here():
                        continue
                    self.page.get_valuation_diff(account)
        return iter(self.accounts)

    @need_login
    def get_loans_list(self):
        if self.loans is None:
            self.loans = []

            if self.home.is_here():
                if self.page.check_no_accounts() or self.page.check_no_loans():
                    return iter([])

            self.home_tache.go(tache='CRESYNT0')

            if self.home.is_here():
                if not self.page.is_access_error():
                    self.page.go_loan_list()
                    self.loans = list(self.page.get_loan_list())

            for _ in range(3):
                try:
                    self.home_tache.go(tache='CPTSYNT0')

                    if self.home.is_here():
                        self.page.go_list()
                except ClientError:
                    pass
                else:
                    break

        return iter(self.loans)

    @need_login
    def _get_history(self, info):
        if isinstance(info['link'], list):
            info['link'] = info['link'][0]
        if not info['link'].startswith('HISTORIQUE'):
            return
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home_tache.go(tache='CPTSYNT0')

        self.page.go_history(info)

        info['link'] = [info['link']]
        if info['type'] == "HISTORIQUE_CB":
            info['link'] += self.page.get_cbtabs()

        while True:
            for i, link in enumerate(info['link'], 1):
                if i > 1:
                    info['link'] = link
                    self.page.go_history(info, True)

                assert self.home.is_here()

                if not self.new_website:
                    # list of transactions on account page
                    transactions_list = [tr for tr in self.page.get_history()]
                    # list of summaries
                    detail_card = [tr for tr in transactions_list if re.match('^CB [\d]{4}\*{6}[\d]{6} TOT DIF [\w]{3,8}$' , tr.label.upper(), flags=re.UNICODE)]

                    # add detail card to list of transactions
                    for tr in detail_card:
                        self.page.go_form_to_detail(tr)
                        transactions_list.extend([tr for tr in self.page.get_detail()])
                        self.page.go_form_to_summary()

                    # order by date the transactions without the summaries
                    transactions = sorted_transactions(transactions_list)
                    for tr in transactions:
                        yield tr
                else:
                    for tr in self.page.get_history():
                        yield tr

                if not self.page.go_next():
                    return

    @need_login
    def _get_history_invests(self, account):
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()

        self.page.go_history(account._info)

        try:
            self.page.go_life_insurance(account)

            if self.market.is_here() is False and self.message.is_here() is False:
                return iter([])

            self.page.submit()
            self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_histo())
        except (IndexError, AttributeError) as e:
            self.logger.error(e)
            return iter([])
        return self.page.iter_history()

    @need_login
    def get_history(self, account):
        if not hasattr(account, '_info'):
            raise NotImplementedError
        if account.type is Account.TYPE_LIFE_INSURANCE:
            return self._get_history_invests(account)
        return self._get_history(account._info)

    @need_login
    def get_coming(self, account):
        trs = []

        if not hasattr(account, '_info'):
            raise NotImplementedError()
        for info in account._card_links:
            for tr in self._get_history(info.copy()):
                tr.type = tr.TYPE_DEFERRED_CARD
                tr.nopurge = True
                trs.append(tr)

        return iter(sorted(trs, key=lambda t: t.rdate, reverse=True))

    @need_login
    def get_investment(self, account):
        if account.type not in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET, Account.TYPE_PEA):
            raise NotImplementedError()
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()

        self.page.go_history(account._info)
        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            # Some users may not have access to this.
            if not self.market.is_here():
                return
            self.page.submit()
            if self.page.is_error():
                return
            self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille')
            if self.message.is_here():
                return
            if not self.page.is_on_right_portfolio(account):
                self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille?compte=%s' % self.page.get_compte(account))
        elif account.type is Account.TYPE_LIFE_INSURANCE:
            try:
                self.page.go_life_insurance(account)

                if self.market.is_here() is False and self.message.is_here() is False:
                    return

                self.page.submit()
                self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_repart())
            except (IndexError, AttributeError) as e:
                self.logger.error(e)
                return
        if self.garbage.is_here():
            return
        for i in self.page.iter_investment():
            yield i
        if self.market.is_here():
            self.page.come_back()

    @need_login
    def get_advisor(self):
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        from weboob.tools.misc import to_unicode
        profile = Profile()
        if 'username=' in self.session.cookies.get('CTX', ''):
            profile.name = to_unicode(re.search('username=([^&]+)', self.session.cookies['CTX']).group(1))
        elif 'nomusager=' in self.session.cookies.get('headerdei'):
            profile.name = to_unicode(re.search('nomusager=(?:[^&]+/ )?([^&]+)', self.session.cookies['headerdei']).group(1))
        return profile

    @need_login
    def iter_recipients(self, origin_account):
        if origin_account.type == Account.TYPE_LOAN:
            return []

        # Transfer unavailable
        try:
            self.pre_transfer(origin_account)
        except TransferBankError:
            return []
        if self.page.transfer_unavailable() or self.page.need_auth() or not self.page.can_transfer(origin_account):
            return []
        return self.page.iter_recipients(account_id=origin_account.id)

    def pre_transfer(self, account):
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()
        self.page.go_transfer(account)
        if self.pro_transfer.is_here():
            raise NotImplementedError()

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.pre_transfer(account)
        self.page.init_transfer(account, recipient, transfer)
        self.page.continue_transfer(account.label, recipient, transfer.label)
        return self.page.create_transfer(account, recipient, transfer)

    @need_login
    def execute_transfer(self, transfer):
        self.page.confirm()
        return self.page.populate_reference(transfer)

    def get_recipient_obj(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = u'Externe'
        r.enabled_at = datetime.datetime.now().replace(microsecond=0)
        r.currency = u'EUR'
        r.bank_name = NotAvailable
        return r

    def post_sms_password(self, sms_password):
        data = {}
        for k, v in self.recipient_form.items():
            if k != 'url':
                data[k] = v
        data['uiAuthCallback__1_'] = sms_password
        self.location(self.recipient_form['url'], data=data)

    def end_sms_recipient(self, recipient, **params):
        self.post_sms_password(params['sms_password'])
        self.recipient_form = None
        self.page.post_form()
        self.page.go_on()
        self.page.post_recipient(recipient)
        self.page.confirm_recipient()
        return self.get_recipient_obj(recipient)

    @retry(CanceledAuth)
    @need_login
    def new_recipient(self, recipient, **params):
        if 'sms_password' in params:
            return self.end_sms_recipient(recipient, **params)

        self.pre_transfer(next(acc for acc in self.get_accounts_list() if acc.type in (Account.TYPE_CHECKING, Account.TYPE_SAVINGS)))
        # This send sms to user.
        self.page.go_add_recipient()
        self.page.check_canceled_auth()
        self.page.set_browser_form()
        raise AddRecipientStep(self.get_recipient_obj(recipient), Value('sms_password', label=self.page.get_prompt_text()))
