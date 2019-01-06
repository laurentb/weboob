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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.captcha import CapCaptchaSolver, ImageCaptchaJob, RecaptchaJob, NocaptchaJob
from weboob.tools.value import ValueBackendPassword

from .browser import AnticaptchaBrowser


__all__ = ['AnticaptchaModule']


class AnticaptchaModule(Module, CapCaptchaSolver):
    NAME = 'anticaptcha'
    DESCRIPTION = 'Anti-Captcha website'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    CONFIG = BackendConfig(
        ValueBackendPassword('api_key', label='API key', regexp='^[0-9a-f]+$'),
        # TODO support proxy option
    )

    BROWSER = AnticaptchaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['api_key'].get(), None)

    def create_job(self, job):
        if isinstance(job, ImageCaptchaJob):
            job.id = self.browser.post_image(job.image)
        elif isinstance(job, RecaptchaJob):
            job.id = self.browser.post_recaptcha(job.site_url, job.site_key)
        elif isinstance(job, NocaptchaJob):
            job.id = self.browser.post_nocaptcha(job.site_url, job.site_key)
        else:
            raise NotImplementedError()

    def poll_job(self, job):
        return self.browser.poll(job)

    def report_wrong_solution(self, job):
        if isinstance(job, ImageCaptchaJob):
            self.browser.report_wrong(job)

    def get_balance(self):
        return self.browser.get_balance()
