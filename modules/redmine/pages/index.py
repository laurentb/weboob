# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.tools.browser import BasePage


class LoginPage(BasePage):
    def login(self, username, password):
        self.browser.select_form(predicate=lambda f: f.attrs.get('method', '') == 'post')
        self.browser['username'] = username.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit()


class IndexPage(BasePage):
    pass


class MyPage(BasePage):
    pass


class ProjectsPage(BasePage):
    def iter_projects(self):
        for ul in self.parser.select(self.document.getroot(), 'ul.projects'):
            for li in ul.findall('li'):
                prj = {}
                link = li.find('div').find('a')
                prj['id'] = link.attrib['href'].split('/')[-1]
                prj['name'] = link.text
                yield prj
