# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json
from collections import OrderedDict
from functools import wraps
import re

from weboob.browser import LoginBrowser, URL, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, AuthMethodNotImplemented
from weboob.browser.exceptions import ClientError
from weboob.capabilities.bank import (
    TransferBankError, TransferInvalidAmount,
    AddRecipientStep, RecipientInvalidOTP,
    AddRecipientTimeout, AddRecipientBankError, RecipientInvalidIban,
)
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.value import Value

from .api import (
    LoginPage, AccountsPage, HistoryPage, ComingPage,
    DebitAccountsPage, CreditAccountsPage, TransferPage,
    ProfilePage,
    AddRecipientPage, OtpChannelsPage, ConfirmOtpPage,
)
from .web import StopPage, ActionNeededPage

from .browser import IngBrowser


def need_login(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        browser_conditions = (
            getattr(self, 'logged', False),
            getattr(self.old_browser, 'logged', False)
        )
        page_conditions = (
            (getattr(self, 'page', False) and self.page.logged),
            (getattr(self.old_browser, 'page', False) and self.old_browser.page.logged)
        )
        if not any(browser_conditions) and not any(page_conditions):
            self.do_login()

            if self.logger.settings.get('export_session'):
                self.logger.debug('logged in with session: %s', json.dumps(self.export_session()))
        return func(self, *args, **kwargs)

    return inner


def need_to_be_on_website(website):
    assert website in ('web', 'api')

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # if on other website than web or api, redirect to old website
            if self.old_browser.url:
                if 'https://bourse.ing.fr/' in self.old_browser.url:
                    self.old_browser.return_from_titre_page.go()
                elif 'https://ingdirectvie.ing.fr/' in self.old_browser.url:
                    self.old_browser.return_from_life_insurance()
                elif 'https://subscribe.ing.fr/' in self.old_browser.url:
                    self.old_browser.return_from_loan_site()

            if website == 'web' and self.is_on_new_website:
                self.redirect_to_old_browser()
            elif website == 'api' and not self.is_on_new_website:
                self.redirect_to_api_browser()
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class IngAPIBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://m.ing.fr'
    STATE_DURATION = 10

    # Login
    context = URL(r'/secure/api-v1/session/context')
    login = URL(r'/secure/api-v1/login/cif', LoginPage)
    keypad = URL(r'/secure/api-v1/login/keypad', LoginPage)
    pin_page = URL(r'/secure/api-v1/login/sca/pin', LoginPage)

    # Error on old website
    errorpage = URL(r'https://secure.ing.fr/.*displayCoordonneesCommand.*', StopPage)
    actioneeded = URL(r'https://secure.ing.fr/general\?command=displayTRAlertMessage',
                      r'https://secure.ing.fr/protected/pages/common/eco1/moveMoneyForbidden.jsf', ActionNeededPage)

    # bank
    history = URL(r'/secure/api-v1/accounts/(?P<account_uid>.*)/transactions/after/(?P<tr_id>\d+)/limit/50', HistoryPage)
    coming = URL(r'/secure/api-v1/accounts/(?P<account_uid>.*)/futureOperations', ComingPage)
    accounts = URL(r'/secure/api-v1/accounts', AccountsPage)

    # transfer
    credit_accounts = URL(r'/secure/api-v1/transfers/debitAccounts/(?P<account_uid>.*)/creditAccounts', CreditAccountsPage)
    debit_accounts = URL(r'/secure/api-v1/transfers/debitAccounts', DebitAccountsPage)
    init_transfer_page = URL(r'/secure/api-v1/transfers/v2/new/validate', TransferPage)
    exec_transfer_page = URL(r'/secure/api-v1/transfers/v2/new/execute/pin', TransferPage)

    # recipient
    add_recipient = URL(r'secure/api-v1/externalAccounts/add/validateRequest', AddRecipientPage)
    otp_channels = URL(r'secure/api-v1/sensitiveoperation/ADD_TRANSFER_BENEFICIARY/otpChannels', OtpChannelsPage)
    confirm_otp = URL(r'secure/api-v1/sca/confirmOtp', ConfirmOtpPage)

    # profile
    informations = URL(r'/secure/api-v1/customer/info', ProfilePage)

    __states__ = ('need_reload_state', 'add_recipient_info')

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday')
        super(IngAPIBrowser, self).__init__(*args, **kwargs)

        self.old_browser = IngBrowser(*args, **kwargs)
        self.transfer_data = None
        self.need_reload_state = None
        self.add_recipient_info = None

    def load_state(self, state):
        # reload state only for new recipient
        if state.get('need_reload_state'):
            state.pop('url', None)
            self.need_reload_state = None
            super(IngAPIBrowser, self).load_state(state)

    WRONGPASS_CODES = (
        'AUTHENTICATION.INVALID_PIN_CODE',
        'AUTHENTICATION.INVALID_CIF_AND_BIRTHDATE_COMBINATION',
        'AUTHENTICATION.FIRST_WRONG_PIN_ATTEMPT',
        'AUTHENTICATION.SECOND_WRONG_PIN_ATTEMPT',
        'AUTHENTICATION.CUSTOMER_DECEASED',
        'SCA.WRONG_AUTHENTICATION',
    )

    ACTIONNEEDED_CODES = (
        'AUTHENTICATION.ACCOUNT_INACTIVE',
        'AUTHENTICATION.ACCOUNT_LOCKED',
        'AUTHENTICATION.NO_COMPLETE_ACCOUNT_FOUND',
        'SCA.ACCOUNT_LOCKED',
    )

    def handle_login_error(self, r):
        error_page = r.response.json()
        assert 'error' in error_page, "Something went wrong in login"
        error = error_page['error']

        if error['code'] in self.WRONGPASS_CODES:
            raise BrowserIncorrectPassword(error['message'])
        elif error['code'] in self.ACTIONNEEDED_CODES:
            raise ActionNeeded(error['message'])

        raise Exception("%r code isn't handled yet: %s" % (error['code'], error['message']))

    def do_login(self):
        assert self.birthday.isdigit()
        if not self.password.isdigit():
            raise BrowserIncorrectPassword()

        # login on new website
        # update cookies
        self.context.go()

        data = OrderedDict([
            ('birthDate', self.birthday),
            ('cif', self.username),
        ])
        try:
            self.login.go(json=data)
        except ClientError as e:
            self.handle_login_error(e)

        data = '{"keyPadSize":{"width":3800,"height":1520},"mode":""}'
        self.keypad.go(data=data, headers={'Content-Type': 'application/json'})

        keypad_url = self.page.get_keypad_url()
        img = self.open('/secure/api-v1%s' % keypad_url).content
        data = {
            'clickPositions': self.page.get_password_coord(img, self.password)
        }

        try:
            self.pin_page.go(json=data, headers={'Referer': self.pin_page.build()})
        except ClientError as e:
            self.handle_login_error(e)

        if not self.page.has_strong_authentication():
            self.auth_token = self.page.response.headers['Ingdf-Auth-Token']
            self.session.headers['Ingdf-Auth-Token'] = self.auth_token
            self.session.cookies['ingdfAuthToken'] = self.auth_token
        else:
            raise ActionNeeded("Vous devez réaliser la double authentification sur le portail internet")

        # to be on logged page, to avoid relogin
        self.accounts.go()

    def deinit(self):
        self.old_browser.deinit()
        super(IngAPIBrowser, self).deinit()

    def redirect_to_old_browser(self):
        self.logger.info('Go on old website')
        token = self.location(
            '/secure/api-v1/sso/exit?context={"originatingApplication":"SECUREUI"}&targetSystem=INTERNET',
            method='POST'
        ).content
        data = {
            'token': token,
            'next': 'protected/pages/index.jsf',
            'redirectUrl': 'protected/pages/index.jsf',
            'targetApplication': 'INTERNET',
            'accountNumber': 'undefined'
        }
        self.session.cookies['produitsoffres'] = 'comptes'
        self.location('https://secure.ing.fr', data=data, headers={'Referer': 'https://secure.ing.fr'})
        self.old_browser.session.cookies.update(self.session.cookies)

    def redirect_to_api_browser(self):
        self.logger.info('Go on new website')
        self.old_browser.redirect_to_api_browser()
        self.session.cookies.update(self.old_browser.session.cookies)
        self.accounts.go()

    @property
    def is_on_new_website(self):
        return self.BASEURL in self.url

    ############# CapBank #############
    @need_to_be_on_website('web')
    def get_web_accounts(self):
        """iter accounts on old website"""
        return self.old_browser.get_accounts_list()

    @need_to_be_on_website('api')
    def get_api_accounts(self):
        """iter accounts on new website"""
        self.accounts.stay_or_go()
        for account in self.page.iter_accounts():
            self.coming.go(account_uid=account.id)
            yield self.page.get_account_coming(obj=account)

    @need_login
    def iter_matching_accounts(self):
        """Do accounts matching for old and new website"""

        api_accounts = [acc for acc in self.get_api_accounts()]

        # go on old website because new website have only cheking and card account information
        for web_acc in self.get_web_accounts():
            for api_acc in api_accounts:
                if web_acc.id[-4:] == api_acc.number[-4:]:
                    web_acc._uid = api_acc.id
                    web_acc.coming = api_acc.coming
                    web_acc.ownership = api_acc.ownership
                    yield web_acc
                    break
            else:
                assert False, 'There should be same account in web and api website'

        # can use this to use export session on old browser
        # new website is an API, export session is not relevant
        if self.logger.settings.get('export_session'):
            self.logger.debug('logged in with session: %s', json.dumps(self.export_session()))

    @need_to_be_on_website('web')
    def get_web_history(self, account):
        """iter history on old website"""
        return self.old_browser.get_history(account)

    @need_to_be_on_website('api')
    def get_api_history(self, account):
        """iter history on new website"""

        # first request transaction id is 0 to get the most recent transaction
        first_transaction_id = 0
        request_number_security = 0

        while request_number_security < 200:
            request_number_security += 1

            # first_transaction_id is 0 for the first request, then
            # it will decreasing after first_transaction_id become the last transaction id of the list
            self.history.go(account_uid=account._uid, tr_id=first_transaction_id)
            if self.page.is_empty_page():
                # empty page means that there are no more transactions
                break

            for tr in self.page.iter_history():
                # transaction id is decreasing
                first_transaction_id = int(tr._web_id)
                if tr.type == FrenchTransaction.TYPE_CARD:
                    tr.bdate = tr.rdate
                yield tr

            # like website, add 1 to the last transaction id of the list to get next transactions page
            first_transaction_id += 1

    @need_login
    def iter_history(self, account):
        """History switch"""

        if account.type not in (account.TYPE_CHECKING, ):
            return self.get_web_history(account)
        else:
            return self.get_api_history(account)

    @need_to_be_on_website('web')
    def get_web_coming(self, account):
        """iter coming on old website"""
        return self.old_browser.get_coming(account)

    @need_to_be_on_website('api')
    def get_api_coming(self, account):
        """iter coming on new website"""
        self.coming.go(account_uid=account._uid)
        for tr in self.page.iter_coming():
            if tr.type == FrenchTransaction.TYPE_CARD:
                tr.bdate = tr.rdate
            yield tr

    @need_login
    def iter_coming(self, account):
        """Incoming switch"""

        if account.type not in (account.TYPE_CHECKING, ):
            return self.get_web_coming(account)
        else:
            return self.get_api_coming(account)

    ############# CapWealth #############
    @need_login
    def get_investments(self, account):
        if account.type not in (account.TYPE_MARKET, account.TYPE_LIFE_INSURANCE, account.TYPE_PEA):
            return []

        # can't use `need_to_be_on_website`
        # because if return without iter invest on old website,
        # previous page is not handled by new website
        if self.is_on_new_website:
            self.redirect_to_old_browser()
        return self.old_browser.get_investments(account)

    ############# CapTransferAddRecipient #############
    @need_login
    @need_to_be_on_website('api')
    def iter_recipients(self, account):
        self.debit_accounts.go()
        if account._uid not in self.page.get_debit_accounts_uid():
            return

        self.credit_accounts.go(account_uid=account._uid)
        for recipient in self.page.iter_recipients(acc_uid=account._uid):
            yield recipient

    def handle_transfer_errors(self, r):
        error_page = r.response.json()
        assert 'error' in error_page, "Something went wrong, transfer is not created"

        error = error_page['error']
        error_msg = error['message']

        if error['code'] == 'TRANSFER.INVALID_AMOUNT_MINIMUM':
            raise TransferInvalidAmount(message=error_msg)
        elif error['code'] == 'INPUT_INVALID' and len(error['values']):
            for value in error['values']:
                error_msg = '%s %s %s.' % (error_msg, value, error['values'][value])

        raise TransferBankError(message=error_msg)

    @need_to_be_on_website('api')
    @need_login
    def init_transfer(self, account, recipient, transfer):
        data = {
            'amount': transfer.amount,
            'executionDate': transfer.exec_date.strftime('%Y-%m-%d'),
            'keyPadSize': {'width': 3800, 'height': 1520},
            'label': transfer.label,
            'fromAccount': account._uid,
            'toAccount': recipient.id
        }
        try:
            self.init_transfer_page.go(json=data, headers={'Referer': self.absurl('/secure/transfers/new')})
        except ClientError as e:
            self.handle_transfer_errors(e)

        if self.page.is_otp_authentication():
            raise AuthMethodNotImplemented()

        suggested_date = self.page.suggested_date
        if transfer.exec_date and transfer.exec_date < suggested_date:
            transfer.exec_date = suggested_date
        assert suggested_date == transfer.exec_date, "Transfer date is not valid"

        self.transfer_data = data
        self.transfer_data.pop('keyPadSize')
        self.transfer_data['clickPositions'] = self.page.get_password_coord(self.password)

        return transfer

    @need_to_be_on_website('api')
    @need_login
    def execute_transfer(self, transfer):
        headers = {
            'Referer': self.absurl('/secure/transfers/new'),
            'Accept': 'application/json, text/plain, */*'
        }
        self.exec_transfer_page.go(json=self.transfer_data, headers=headers)

        assert self.page.transfer_is_validated, "Transfer is not validated"
        return transfer

    @need_login
    def send_sms_to_user(self, recipient, sms_info):
        """Add recipient with OTP SMS authentication"""
        data = {
            'channelType': sms_info['type'],
            'externalAccountsRequest': self.add_recipient_info,
            'sensitiveOperationAction': 'ADD_TRANSFER_BENEFICIARY',
        }

        phone_id = sms_info['phone']
        data['channelValue'] = phone_id
        self.add_recipient_info['phoneUid'] = phone_id

        self.location(self.absurl('/secure/api-v1/sca/sendOtp', base=True), json=data)
        self.need_reload_state = True
        raise AddRecipientStep(recipient, Value('code', label='Veuillez saisir le code temporaire envoyé par SMS'))

    def handle_recipient_error(self, r):
        # The bank gives an error message when an error occures.
        # But sometimes the message is not relevant.
        # So I may replace it by nothing or by a custom message.
        # The exception to raise can be coupled with:
        # * Nothing: empty message
        # * None: message of the bank
        # * String: custom message
        RECIPIENT_ERROR = {
            'SENSITIVE_OPERATION.SENSITIVE_OPERATION_NOT_FOUND': (AddRecipientTimeout,),
            'SENSITIVE_OPERATION.EXPIRED_TEMPORARY_CODE': (AddRecipientTimeout, None),
            'EXTERNAL_ACCOUNT.EXTERNAL_ACCOUNT_ALREADY_EXISTS': (AddRecipientBankError, None),
            'EXTERNAL_ACCOUNT.ACCOUNT_RESTRICTION': (AddRecipientBankError, None),
            'EXTERNAL_ACCOUNT.EXTERNAL_ACCOUNT_IS_INTERNAL_ACCOUT': (AddRecipientBankError, None),  # nice spelling
            'EXTERNAL_ACCOUNT.IBAN_NOT_FRENCH': (RecipientInvalidIban, "L'IBAN doit correpondre à celui d'une banque domiciliée en France."),
            'SCA.WRONG_OTP_ATTEMPT': (RecipientInvalidOTP, None),
            'INPUT_INVALID': (AssertionError, None),  # invalid request
        }

        error_page = r.response.json()
        if 'error' in error_page:
            error = error_page['error']

            error_exception = RECIPIENT_ERROR.get(error['code'])
            if error_exception:
                if len(error_exception) == 1:
                    raise error_exception[0]()
                elif error_exception[1] is None:
                    raise error_exception[0](message=error['message'])
                else:
                    raise error_exception[0](message=error_exception[1])

            assert False, 'Recipient error "%s" not handled' % error['code']

    @need_login
    def end_sms_recipient(self, recipient, code):
        # create a variable to empty the add_recipient_info
        # so that if there is a problem it will not be caught
        # in the StatesMixin
        rcpt_info = self.add_recipient_info
        self.add_recipient_info = None

        if not re.match(r'^\d{6}$', code):
            raise RecipientInvalidOTP()

        data = {
            'externalAccountsRequest': rcpt_info,
            'otp': code,
            'sensitiveOperationAction': 'ADD_TRANSFER_BENEFICIARY',
        }

        try:
            self.confirm_otp.go(json=data)
        except ClientError as e:
            self.handle_recipient_error(e)
            raise

    @need_login
    @need_to_be_on_website('api')
    def new_recipient(self, recipient, **params):
        # sms only, we don't handle the call
        if 'code' in params:
            # part 2 - finalization
            self.end_sms_recipient(recipient, params['code'])

            # WARNING: On the recipient list, the IBAN is masked
            # so I cannot match it
            # The label is not checked by the website
            # so I cannot match it
            return recipient

        # part 1 - initialization
        # Set sign method
        self.otp_channels.go()
        sms_info = self.page.get_sms_info()

        try:
            self.add_recipient.go(json={
                'accountHolderName': recipient.label,
                'iban': recipient.iban
            })
        except ClientError as e:
            self.handle_recipient_error(e)
            raise

        assert self.page.check_recipient(recipient), "The recipients don't match."
        self.add_recipient_info = self.page.doc

        # WARNING: this send validation request to user
        self.send_sms_to_user(recipient, sms_info)

    ############# CapDocument #############
    @need_login
    @need_to_be_on_website('web')
    def get_subscriptions(self):
        return self.old_browser.get_subscriptions()

    @need_login
    @need_to_be_on_website('web')
    def get_documents(self, subscription):
        return self.old_browser.get_documents(subscription)

    @need_login
    @need_to_be_on_website('web')
    def download_document(self, bill):
        return self.old_browser.download_document(bill)

    ############# CapProfile #############
    @need_login
    @need_to_be_on_website('api')
    def get_profile(self):
        self.informations.go()
        return self.page.get_profile()
