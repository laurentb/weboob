# -*- coding: utf-8 -*-

# Copyright(C) 2014-2015      Oleg Plakhotniuk
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import json
import os
from subprocess import STDOUT, CalledProcessError, check_output
from tempfile import mkstemp

from weboob.browser import URL, LoginBrowser, need_login
from weboob.capabilities.bank import AccountNotFound
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import unquote

from .pages import ActivityPage, SomePage, StatementPage, StatementsPage, SummaryPage

__all__ = ['AmazonStoreCard']


class AmazonStoreCard(LoginBrowser):
    BASEURL = 'https://www.synchronycredit.com'
    MAX_RETRIES = 10
    TIMEOUT = 120.0
    stmts = URL('/eService/EBill/eBillAction.action$', StatementsPage)
    statement = URL('eService/EBill/eBillViewPDFAction.action.*$',
                    StatementPage)
    summary = URL('/eService/AccountSummary/initiateAccSummaryAction.action$',
                  SummaryPage)
    activity = URL('/eService/BillingActivity'
                   '/initiateBillingActivityAction.action$',
                   ActivityPage)
    unknown = URL('.*', SomePage)

    def __init__(self, phone, code_file, *args, **kwargs):
        super(AmazonStoreCard, self).__init__(*args, **kwargs)
        self.phone = phone
        self.code_file = code_file

    def do_login(self):
        scrf, scrn = mkstemp('.js')
        cookf, cookn = mkstemp('.json')
        os.write(scrf, LOGIN_JS % {
            'timeout': 300,
            'username': self.username,
            'password': self.password,
            'output': cookn,
            'code': self.code_file,
            'phone': self.phone[-4:],
            'agent': self.session.headers['User-Agent']})
        os.close(scrf)
        os.close(cookf)
        for i in range(self.MAX_RETRIES):
            try:
                check_output(["phantomjs", scrn], stderr=STDOUT)
                break
            except CalledProcessError as error:
                last_error = error
        else:
            raise last_error
        with open(cookn) as cookf:
            cookies = json.loads(cookf.read())
        os.remove(scrn)
        os.remove(cookn)
        self.session.cookies.clear()
        for c in cookies:
            for k in ['expiry', 'expires', 'httponly']:
                c.pop(k, None)
            c['value'] = unquote(c['value'])
            self.session.cookies.set(**c)
        if not self.summary.go().logged:
            raise BrowserIncorrectPassword()

    @need_login
    def get_account(self, id_):
        a = next(self.iter_accounts())
        if (a.id != id_):
            raise AccountNotFound()
        return a

    @need_login
    def iter_accounts(self):
        yield self.summary.go().account()

    @need_login
    def iter_history(self, account):
        for t in self.activity.go().iter_recent():
            yield t
        for s in self.stmts.go().iter_statements():
            for t in s.iter_transactions():
                yield t


LOGIN_JS = u'''\
var TIMEOUT = %(timeout)s*1000; // milliseconds
var page = require('webpage').create();
page.settings.userAgent = "%(agent)s";
page.open('http://www.syncbank.com/amazon');

var waitForForm = function() {
  var hasForm = page.evaluate(function(){
    return !!document.getElementById('secLoginBtn')
  });
  if (hasForm) {
    page.evaluate(function(){
      document.getElementById('loginUserID').value = '%(username)s';
      document.getElementById('loginPassword').value = '%(password)s';
      var href = document.getElementById('secLoginBtn').getAttribute('href');
      window.location.href = href;
    });
  } else {
    setTimeout(waitForForm, 1000);
  }
}

var waitForLogin = function() {
  var hasLogout = page.content.indexOf('Logout') != -1;
  if (hasLogout) {
    var cookies = JSON.stringify(phantom.cookies);
    require('fs').write('%(output)s', cookies, 'w');
    phantom.exit();
  } else {
    setTimeout(waitForLogin, 2000);
  }
}

var waitForSendCode = function() {
  var hasSendCode = page.evaluate(function(){
    return document.getElementsByClassName('sendCodeTo').length > 0
        && document.getElementById('phoneNumbers').children.length > 0;
  });
  if (hasSendCode) {
    page.evaluate(function(){
      var nums = document.getElementById('phoneNumbers').children;
      for (var inum = 0; inum < nums.length; inum++) {
        var num = nums[inum].children[0];
        if (num.text.indexOf('%(phone)s') != -1) {
          selectPhone((inum+1).toString());
          var methods = document.getElementById('deliveryMethods').children;
          for (var imtd = 0; imtd < methods.length; imtd++) {
            var method = methods[imtd].children[0];
            if (method.text.indexOf('SMS') != -1) {
              selectDeliveryMenthod((imtd+1).toString());
              otpGenerateAjax('otpGenerateAjax');
              return;
            }
          }
        }
      }
    });
  } else {
    setTimeout(waitForSendCode, 2000);
  }
}

var waitForEnterCode = function() {
  var hasEnterCode = page.evaluate(function(){
    return !!document.getElementById('fourDigitId');
  });
  var code = "";
  try {
    code = require('fs').read('%(code)s');
  } catch (e) {
  }
  if (hasEnterCode && code.length >= 4) {
    page.evaluate(function(code){
      document.getElementById('fourDigitId').value = code.substr(0,4);
      document.getElementById('Yes1').checked = true;
      otpVerifyAjax('otpVerifyAjax');
    }, code);
  } else {
    setTimeout(waitForEnterCode, 2000);
  }
}

waitForForm();
waitForLogin();
waitForSendCode();
waitForEnterCode();
setTimeout(function(){phantom.exit(-1);}, TIMEOUT);
'''
