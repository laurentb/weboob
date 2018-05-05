# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from base64 import b64encode

from weboob.browser.browsers import APIBrowser
from weboob.exceptions import BrowserIncorrectPassword, BrowserBanned
from weboob.capabilities.captcha import (
    ImageCaptchaJob, RecaptchaJob, NocaptchaJob, CaptchaError,
    InsufficientFunds, UnsolvableCaptcha, InvalidCaptcha,
)


class AnticaptchaBrowser(APIBrowser):
    BASEURL = 'https://api.anti-captcha.com/'

    def __init__(self, apikey, captcha_proxy, *args, **kwargs):
        super(AnticaptchaBrowser, self).__init__(*args, **kwargs)
        self.apikey = apikey
        self.captcha_proxy = captcha_proxy

    def post_image(self, data):
        data = {
            "clientKey": self.apikey,
            "task": {
                "type": "ImageToTextTask",
                "body": b64encode(data).decode('ascii'),
                "phrase": False,
                "case": False,
                "numeric": False,
                "math": 0,
                "minLength": 0,
                "maxLength": 0,
            }
        }
        r = self.request('/createTask', data=data)
        return str(r['taskId'])

    def post_recaptcha(self, url, key):
        return self.post_gcaptcha(url, key, 'RecaptchaV1')

    def post_nocaptcha(self, url, key):
        return self.post_gcaptcha(url, key, 'NoCaptcha')

    def post_gcaptcha(self, url, key, prefix):
        data = {
            "clientKey": self.apikey,
            "task": {
                "type": "%sTaskProxyless" % prefix,
                "websiteURL": url,
                "websiteKey": key,
            },
            "softId": 0,
            "languagePool": "en",
        }
        r = self.request('/createTask', data=data)
        return str(r['taskId'])

    def check_reply(self, r):
        excs = {
            'ERROR_KEY_DOES_NOT_EXIST': BrowserIncorrectPassword,
            'ERROR_PROXY_NOT_AUTHORISED': BrowserIncorrectPassword,
            'ERROR_ZERO_CAPTCHA_FILESIZE': InvalidCaptcha,
            'ERROR_TOO_BIG_CAPTCHA_FILESIZE': InvalidCaptcha,
            'ERROR_IMAGE_TYPE_NOT_SUPPORTED': InvalidCaptcha,
            'ERROR_RECAPTCHA_INVALID_SITEKEY': InvalidCaptcha,
            'ERROR_RECAPTCHA_INVALID_DOMAIN': InvalidCaptcha,
            'ERROR_ZERO_BALANCE': InsufficientFunds,
            'ERROR_CAPTCHA_UNSOLVABLE': UnsolvableCaptcha,
            'ERROR_IP_BLOCKED': BrowserBanned,
            'ERROR_PROXY_BANNED': BrowserBanned,
        }

        if not r['errorId']:
            return

        err = r.get('errorCode')
        exc_type = excs.get(err, CaptchaError)
        raise exc_type(r['errorDescription'])

    def poll(self, job):
        data = {
            "clientKey": self.apikey,
            "taskId": int(job.id),
        }
        r = self.request('/getTaskResult', data=data)
        self.check_reply(r)

        if r['status'] != 'ready':
            return False

        sol = r['solution']
        if isinstance(job, ImageCaptchaJob):
            job.solution = sol['text']
        elif isinstance(job, RecaptchaJob):
            job.solution = sol['recaptchaResponse']
            job.solution_challenge = sol['recaptchaChallenge']
        elif isinstance(job, NocaptchaJob):
            job.solution = sol['gRecaptchaResponse']
        else:
            raise NotImplementedError()

        return True

    def get_balance(self):
        data = {
            "clientKey": self.apikey
        }
        r = self.request('/getBalance', data=data)
        return r['balance']

    def report_wrong(self, job):
        data = {
            "clientKey": self.apikey,
            "taskId": int(job.id),
        }
        r = self.request('/reportIncorrectImageCaptcha', data=data)
        self.logger.debug('complaint accepted? %s', r['errorId'] == 0)
