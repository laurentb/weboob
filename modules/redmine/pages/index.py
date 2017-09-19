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


from weboob.browser.pages import HTMLPage


class BaseHTMLPage(HTMLPage):
    @property
    def logged(self):
        return len(self.doc.xpath('//a[has-class("my-account")]'))


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(xpath='//form[@method="post"]')
        form['username'] = username
        form['password'] = password
        form.submit()


class IndexPage(BaseHTMLPage):
    pass


class MyPage(BaseHTMLPage):
    pass


class ProjectsPage(BaseHTMLPage):
    def iter_projects(self):
        for ul in self.doc.xpath('//ul[has-class("projects")]'):
            for li in ul.findall('li'):
                prj = {}
                link = li.find('div').find('a')
                prj['id'] = link.attrib['href'].split('/')[-1]
                prj['name'] = link.text
                yield prj
