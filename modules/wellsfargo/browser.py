# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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


import json
import os
import ssl
from subprocess import STDOUT, CalledProcessError, check_output
from tempfile import mkstemp

from weboob.browser import URL, LoginBrowser, need_login
from weboob.capabilities.bank import AccountNotFound
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.compat import unquote

from .pages import (ActivityCardPage, ActivityCashPage, CodeRequestPage, CodeSubmitPage, DocumentsPage, LoggedInPage,
                    LoginProceedPage, LoginRedirectPage, StatementPage, StatementsEmbeddedPage, StatementsPage,
                    SummaryPage)

__all__ = ['WellsFargo']


class WellsFargo(LoginBrowser):
    BASEURL = 'https://online.wellsfargo.com'
    TIMEOUT = 30
    MAX_RETRIES = 10
    login_proceed = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON.*$',
                        '/login\?ERROR_CODE=.*LOB=CONS&$',
                        LoginProceedPage)
    login_redirect = URL('/das/cgi-bin/session.cgi\?screenid=SIGNON.*$',
                         '/login\?ERROR_CODE=.*LOB=CONS&$',
                         LoginRedirectPage)
    code_request = URL('https://oam.wellsfargo.com/oam/access'
                       '/twoFAAARDisplay\?OAM_TKN=.+$', CodeRequestPage)
    code_submit = URL('https://oam.wellsfargo.com/oam/access'
                      '/twoFAAARDisplay\?OAM_TKN=.+$',
                      'https://oam.wellsfargo.com/oam/access'
                      '/twoFAAARSubmitCode\?OAM_TKN=.+$', CodeSubmitPage)
    summary = URL('/das/channel/accountSummary$', SummaryPage)
    activity_cash = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                        ActivityCashPage)
    activity_card = URL('/das/cgi-bin/session.cgi\?sessargs=.+$',
                        ActivityCardPage)
    documents = URL('https://connect.secure.wellsfargo.com'
                    '/accounts/start\?.+$', DocumentsPage)
    statements_embedded = URL('https://connect.secure.wellsfargo.com'
                              '/accounts/start\?.+$', StatementsEmbeddedPage)
    statements = URL('https://connect.secure.wellsfargo.com'
                     '/accounts/documents/statement/list.+$',
                     StatementsPage)
    statement = URL('https://connect.secure.wellsfargo.com'
                    '/accounts/documents/retrieve/.+$',
                    StatementPage)
    unknown = URL('/.*$', LoggedInPage)  # e.g. random advertisement pages.

    def __init__(self, question1, answer1, question2, answer2,
                 question3, answer3, phone_last4, code_file, *args, **kwargs):
        super(WellsFargo, self).__init__(*args, **kwargs)
        self.question1 = question1
        self.answer1 = answer1
        self.question2 = question2
        self.answer2 = answer2
        self.question3 = question3
        self.answer3 = answer3
        self.phone_last4 = phone_last4
        self.code_file = code_file

    def do_login(self):
        '''
        There's a bunch of dynamically generated obfuscated JavaScript,
        which uses DOM. For now the easiest option seems to be to run it in
        PhantomJs.
        '''
        for i in range(self.MAX_RETRIES):
            scrf, scrn = mkstemp('.js')
            cookf, cookn = mkstemp('.json')
            os.write(scrf, LOGIN_JS % {
                'scriptTimeout': self.TIMEOUT*2,
                'resourceTimeout': self.TIMEOUT,
                'username': self.username,
                'password': self.password,
                'output': cookn,
                'question1': self.question1,
                'answer1': self.answer1,
                'question2': self.question2,
                'answer2': self.answer2,
                'question3': self.question3,
                'answer3': self.answer3})
            os.close(scrf)
            os.close(cookf)
            try:
                check_output(["phantomjs", scrn], stderr=STDOUT)
                with open(cookn) as cookf:
                    cookies = json.loads(cookf.read())
            except CalledProcessError:
                continue
            finally:
                os.remove(scrn)
                os.remove(cookn)
            self.session.cookies.clear()
            for c in cookies:
                for k in ['expiry', 'expires', 'httponly']:
                    c.pop(k, None)
                c['value'] = unquote(c['value'])
                self.session.cookies.set(**c)
            self.summary.go()
            if self.page.logged:
                break
        else:
            raise BrowserIncorrectPassword

    def location(self, *args, **kwargs):
        """
        Wells Fargo inserts redirecting pages from time to time,
        so we should follow them whenever we see them.
        """
        r = super(WellsFargo, self).location(*args, **kwargs)
        if self.login_proceed.is_here():
            return self.page.proceed()
        elif self.login_redirect.is_here():
            return self.page.redirect()
        elif self.code_request.is_here():
            return self.page.request_code()
        elif self.code_submit.is_here():
            return self.page.submit_code()
        else:
            return r

    def prepare_request(self, req):
        """
        Wells Fargo uses TLS v1.0. See issue #1647 for details.
        """
        preq = super(WellsFargo, self).prepare_request(req)
        conn = self.session.adapters['https://'].get_connection(preq.url)
        conn.ssl_version = ssl.PROTOCOL_TLSv1
        return preq

    def get_account(self, id_):
        self.to_activity()
        if id_ not in self.page.accounts_ids():
            raise AccountNotFound()
        else:
            self.to_activity(id_)
            return self.page.get_account()

    def iter_accounts(self):
        self.to_activity()
        for id_ in self.page.accounts_ids():
            self.to_activity(id_)
            yield self.page.get_account()

    @need_login
    def to_summary(self):
        self.summary.stay_or_go()
        assert self.summary.is_here()

    def is_activity(self):
        return self.activity_cash.is_here() or self.activity_card.is_here()

    @need_login
    def to_activity(self, id_=None):
        if not self.is_activity():
            self.to_summary()
            self.page.to_activity()
            assert self.is_activity()
        if id_ and self.page.account_id() != id_:
            self.page.to_account(id_)
            assert self.is_activity()
            assert self.page.account_id() == id_

    @need_login
    def to_statements(self, id_=None, year=None):
        if not self.statements.is_here() \
           and not self.statements_embedded.is_here():
            self.to_summary()
            self.page.to_documents()
            if self.documents.is_here():
                self.page.to_statements()
                assert self.statements.is_here()
            else:
                assert self.statements_embedded.is_here()
        if id_ and self.page.parser().account_id() != id_:
            self.page.parser().to_account(id_)
            assert self.statements.is_here()
            assert self.page.parser().account_id() == id_
        if year and self.page.parser().year() != year:
            self.page.parser().to_year(year)
            assert self.statements.is_here()
            assert self.page.parser().year() == year

    @need_login
    def to_statement(self, uri):
        for i in range(self.MAX_RETRIES):
            self.location(uri)
            if self.statement.is_here():
                break
        else:
            raise BrowserUnavailable()

    def iter_history(self, account):
        self.to_activity(account.id)
        # Skip transactions on web page if we cannot apply
        # "since last statement" filter.
        # This might be the case, for example, if Wells Fargo
        # is processing the current statement:
        # "Since your credit card account statement is being processed,
        #  transactions grouped by statement period will not be available
        #  for up to seven days."
        # (www.wellsfargo.com, 2014-07-20)
        if self.page.since_last_statement():
            assert self.page.account_id() == account.id
            while True:
                for trans in self.page.iter_transactions():
                    yield trans
                if not self.page.next_():
                    break

        self.to_statements(account.id)
        for year in self.page.parser().years():
            self.to_statements(account.id, year)
            for stmt in self.page.parser().statements():
                self.to_statement(stmt)
                for trans in self.page.iter_transactions():
                    yield trans


LOGIN_JS = u'''\
var page = require('webpage').create();

page.settings.resourceTimeout = %(resourceTimeout)s*1000;
page.open('https://www.wellsfargo.com/');

var waitForForm = function() {
  var hasForm = page.evaluate(function(){
    return !!document.getElementById('frmSignon')
  });
  if (hasForm) {
    page.evaluate(function(){
      document.getElementById('userid').value = '%(username)s';
      document.getElementById('password').value = '%(password)s';
      document.getElementById('frmSignon').submit();
    });
  } else {
    setTimeout(waitForForm, 1000);
  }
}

var waitForQuestions = function() {
  var isQuestion = page.content.indexOf('Confirm Your Identity') != -1;
  if (isQuestion) {
    var questions = {
      "%(question1)s": "%(answer1)s",
      "%(question2)s": "%(answer2)s",
      "%(question3)s": "%(answer3)s"
    };
    for (var question in questions) {
      if (page.content.indexOf(question)) {
        page.evaluate(function(answer){
          document.getElementById('answer').value = answer;
          document.getElementById('command').submit.click();
        }, questions[question]);
      }
    }
  }
  setTimeout(waitForQuestions, 2000);
}

var waitForLogin = function() {
  var isSplash = page.content.indexOf('Splash Page') != -1;
  var hasSignOff = page.content.indexOf('Sign Off') != -1;
  if (isSplash || hasSignOff) {
    var cookies = JSON.stringify(phantom.cookies);
    require('fs').write('%(output)s', cookies, 'w');
    phantom.exit();
  } else {
    setTimeout(waitForLogin, 2000);
  }
}

waitForForm();
waitForQuestions();
waitForLogin();
setTimeout(function(){phantom.exit(-1);}, %(scriptTimeout)s*1000);
'''
