# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.content import ICapContent, Content
from weboob.tools.backend import BaseBackend

from .browser import Newspaper20minutesBrowser


__all__ = ['Newspaper20minutesBackend']


class Newspaper20minutesBackend(BaseBackend, ICapContent):
    NAME = 'minutes20'
    MAINTAINER = 'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'20minutes French news  website'
    #CONFIG = ValuesDict(Value('login',      label='Account ID'),
    #                    Value('password',   label='Password', masked=True))
    BROWSER = Newspaper20minutesBrowser

    def get_content(self, url):
        if isinstance(url, basestring):
            content = Content(url)
        else:
            content = url
            url = content._id
        with self.browser:
            data = self.browser.get_content(url)
            print "blabla"
        
        content.content = data[1]
        content.title = data[0]
        return content

    def log_content(self, id):
        raise NotImplementedError()

    def push_content(self, content, message = None):
        raise NotImplementedError()
