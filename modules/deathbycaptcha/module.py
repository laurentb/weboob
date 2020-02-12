# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.captcha import CapCaptchaSolver, ImageCaptchaJob

from .browser import DeathbycaptchaBrowser


__all__ = ['DeathbycaptchaModule']


class DeathbycaptchaModule(Module, CapCaptchaSolver):
    NAME = 'deathbycaptcha'
    DESCRIPTION = 'Death By Captcha'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'

    CONFIG = BackendConfig(
        Value('login'),
        ValueBackendPassword('password'),
    )

    BROWSER = DeathbycaptchaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def create_job(self, job):
        if not isinstance(job, ImageCaptchaJob):
            raise NotImplementedError()
        job.id = self.browser.create_job(job.image)

    def poll_job(self, job):
        job.solution = self.browser.poll(job.id)
        return job.solution is not None
