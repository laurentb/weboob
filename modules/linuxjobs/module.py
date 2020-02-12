# -*- coding: utf-8 -*-

# Copyright(C) 2016      François Revol
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


from weboob.tools.backend import Module
from weboob.capabilities.job import CapJob

from .browser import LinuxJobsBrowser


__all__ = ['LinuxJobsModule']


class LinuxJobsModule(Module, CapJob):
    NAME = 'linuxjobs'
    DESCRIPTION = u'linuxjobs website'
    MAINTAINER = u'François Revol'
    EMAIL = 'revol@free.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'

    BROWSER = LinuxJobsBrowser

    def advanced_search_job(self):
        """
         Iter results of an advanced search

        :rtype: iter[:class:`BaseJobAdvert`]
        """
        raise NotImplementedError()

    def get_job_advert(self, _id, advert=None):
        """
        Get an announce from an ID.

        :param _id: id of the advert
        :type _id: str
        :param advert: the advert
        :type advert: BaseJobAdvert
        :rtype: :class:`BaseJobAdvert` or None if not found.
        """
        return self.browser.get_job_advert(_id, advert)

    def search_job(self, pattern=None):
        """
        Iter results of a search on a pattern.

        :param pattern: pattern to search on
        :type pattern: str
        :rtype: iter[:class:`BaseJobAdvert`]
        """
        for job_advert in self.browser.search_job(pattern):
            yield job_advert
