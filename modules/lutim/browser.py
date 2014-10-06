# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
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


from weboob.deprecated.browser import Browser
from StringIO import StringIO
import re

from .pages import PageAll


__all__ = ['LutimBrowser']


class LutimBrowser(Browser):
    ENCODING = 'utf-8'

    def __init__(self, base_url, *args, **kw):
        Browser.__init__(self, *args, **kw)
        self.base_url = base_url
        self.PAGES = {re.escape(self.base_url): PageAll}

    def post(self, name, content, max_days):
        self.location(self.base_url)
        assert self.is_on_page(PageAll)
        self.select_form(nr=0)
        self.form['delete-day'] = [str(max_days)]
        self.form.find_control('file').add_file(StringIO(content), filename=name)
        self.submit()

        assert self.is_on_page(PageAll)
        return self.page.get_info()
