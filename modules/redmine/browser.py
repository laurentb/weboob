# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

import re
import lxml.html

from weboob.capabilities.bugtracker import IssueError
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import quote

from .pages.index import LoginPage, IndexPage, MyPage, ProjectsPage
from .pages.wiki import WikiPage, WikiEditPage
from .pages.issues import IssuesPage, IssuePage, NewIssuePage, IssueLogTimePage, \
                          IssueTimeEntriesPage


__all__ = ['RedmineBrowser']


class RedmineBrowser(LoginBrowser):
    index = URL(r'/$', IndexPage)
    login = URL(r'/login$', r'/login\?back_url.*', LoginPage) # second url is related to redmine 0.9
    mypage = URL(r'/my/page', MyPage)
    projects_page = URL(r'/projects$', ProjectsPage)
    wiki_edit = URL(r'/projects/(?P<project>[\w-]+)/wiki/(?P<page>[^\/]+)/edit(?:\?version=\d+)?', WikiEditPage)
    wiki = URL(r'/projects/[\w-]+/wiki/[^\/]*', WikiPage)
    new_issue = URL(r'/projects/[\w-]+/issues/new', NewIssuePage)
    issues = URL(r'/projects/[\w-]+/issues$',
                 r'/issues/?\?.*$',
                 r'/issues$',
                 IssuesPage)
    issue = URL(r'/issues/(?P<id>\d+)', IssuePage)
    issues_log_time = URL(r'/issues/(?P<id>\d+)/time_entries/new', IssueLogTimePage)
    issues_time_entry = URL(r'/projects/[\w-]+/time_entries', IssueTimeEntriesPage)

    def __init__(self, url, *args, **kwargs):
        super(RedmineBrowser, self).__init__(*args, **kwargs)
        self._userid = 0
        self.BASEURL = url
        self.projects = {}

    def do_login(self):
        if not self.login.is_here():
            self.login.go()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

        divs = self.page.doc.xpath('//div[@id="loggedas"]')
        if len(divs) > 0:
            parts = divs[0].find('a').attrib['href'].split('/')
            self._userid = int(parts[2])

    def get_userid(self):
        return self._userid

    @need_login
    def get_wiki_source(self, project, page, version=None):
        url = self.absurl('projects/%s/wiki/%s/edit' % (project, quote(page)), True)
        if version:
            url += '?version=%s' % version
        self.location(url)
        return self.page.get_source()

    @need_login
    def set_wiki_source(self, project, page, data, message):
        self.location(self.absurl('projects/%s/wiki/%s/edit' % (project, quote(page)), True))
        self.page.set_source(data, message)

    @need_login
    def get_wiki_preview(self, project, page, data):
        if (not self.wiki_edit.is_here() or self.page.params['project'] != project
                or self.page.params['page'] != page):
            url = self.absurl('projects/%s/wiki/%s/edit' % (project, quote(page)), True)
            self.location(url)
        url = self.absurl('projects/%s/wiki/%s/preview' % (project, quote(page)), True)
        params = self.get_submit()
        params['content[text]'] = data
        #params['authenticity_token'] = self.page.get_authenticity_token()
        preview_html = lxml.html.fragment_fromstring(self.open(url, data=params), create_parent='div')
        preview_html.find("fieldset").drop_tag()
        preview_html.find("legend").drop_tree()
        return lxml.html.tostring(preview_html)

    METHODS = {'POST': {'project_id': 'project_id',
                        'column':     'query[column_names][]',
                        'value':      'values[%s][]',
                        'field':      'fields[]',
                        'operator':   'operators[%s]',
                       },
               'GET':  {'project_id': 'project_id',
                        'column':     'c[]',
                        'value':      'v[%s][]',
                        'field':      'f[]',
                        'operator':   'op[%s]',
                       }
            }

    @need_login
    def query_issues(self, project_name, **kwargs):
        self.location(self.absurl('projects/%s/issues' % project_name, True))
        token = self.page.get_authenticity_token()
        method = self.page.get_query_method()
        data = ((self.METHODS[method]['project_id'], project_name),
                (self.METHODS[method]['column'], 'tracker'),
                ('authenticity_token',    token),
                (self.METHODS[method]['column'], 'status'),
                (self.METHODS[method]['column'], 'priority'),
                (self.METHODS[method]['column'], 'subject'),
                (self.METHODS[method]['column'], 'assigned_to'),
                (self.METHODS[method]['column'], 'updated_on'),
                (self.METHODS[method]['column'], 'category'),
                (self.METHODS[method]['column'], 'fixed_version'),
                (self.METHODS[method]['column'], 'done_ratio'),
                (self.METHODS[method]['column'], 'author'),
                (self.METHODS[method]['column'], 'start_date'),
                (self.METHODS[method]['column'], 'due_date'),
                (self.METHODS[method]['column'], 'estimated_hours'),
                (self.METHODS[method]['column'], 'created_on'),
               )
        for key, value in kwargs.items():
            if value:
                value = self.page.get_value_from_label(self.METHODS[method]['value'] % key, value)
                data += ((self.METHODS[method]['value'] % key, value),)
                data += ((self.METHODS[method]['field'], key),)
                data += ((self.METHODS[method]['operator'] % key, '~'),)

        if method == 'POST':
            self.location('/issues?set_filter=1&per_page=100', data=data)
        else:
            data += (('set_filter', '1'), ('per_page', '100'))
            self.location(self.absurl('issues', True), params=data)

        assert self.issues.is_here()
        return {'project': self.page.get_project(project_name),
                'iter':    self.page.iter_issues(),
               }

    @need_login
    def get_project(self, project):
        self.location(self.absurl('projects/%s/issues/new' % project, True))
        assert self.new_issue.is_here()

        return self.page.get_project(project)

    @need_login
    def get_issue(self, id):
        self.location(self.absurl('issues/%s' % id, True))

        assert self.issue.is_here()
        return self.page.get_params()

    @need_login
    def logtime_issue(self, id, hours, message):
        self.location(self.absurl('issues/%s/time_entries/new' % id, True))

        assert self.issues_log_time.is_here()
        self.page.logtime(hours.seconds/3600, message)

    @need_login
    def comment_issue(self, id, message):
        self.location(self.absurl('issues/%s' % id, True))

        assert self.issue.is_here()
        self.page.fill_form(note=message)

    @need_login
    def get_custom_fields(self, project):
        self.location(self.absurl('projects/%s/issues/new' % project, True))
        assert self.new_issue.is_here(NewIssuePage)

        fields = {}
        for key, div in self.page.iter_custom_fields():
            if 'value' in div.attrib:
                fields[key] = div.attrib['value']
            else:
                olist = div.xpath('.//option[@selected="selected"]')
                fields[key] = ', '.join([i.attrib['value'] for i in olist])

        return fields

    @need_login
    def create_issue(self, project, **kwargs):
        self.location(self.absurl('projects/%s/issues/new' % project, True))

        assert self.new_issue.is_here()
        self.page.fill_form(**kwargs)

        error = self.page.get_errors()
        if len(error) > 0:
            raise IssueError(error)

        assert self.issue.is_here()
        return int(self.page.params['id'])

    @need_login
    def edit_issue(self, id, **kwargs):
        self.location(self.absurl('issues/%s' % id, True))

        assert self.issue.is_here()
        self.page.fill_form(**kwargs)

        assert self.issue.is_here()
        return int(self.page.params['id'])

    @need_login
    def remove_issue(self, id):
        self.location(self.absurl('issues/%s' % id, True))

        assert self.issue.is_here()
        token = self.page.get_authenticity_token()

        data = (('authenticity_token', token),)
        self.open(self.absurl('issues/%s/destroy' % id, True), data=data)

    @need_login
    def iter_projects(self):
        self.location(self.absurl('projects', True))

        return self.page.iter_projects()

    @need_login
    def create_category(self, project, name, token):
        data = {'issue_category[name]': name}
        headers = {'X-CSRF-Token': token,
                   'X-Prototype-Version': '1.7',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
                  }
        url = self.absurl('projects/%s/issue_categories' % project, True)
        r = self.open(url, data=data, headers=headers).text

        # Element.replace("issue_category_id", "\u003Cselect id=\"issue_category_id\" name=\"issue[category_id]\"\u003E\u003Coption\u003E\u003C/option\u003E\u003Coption value=\"28\"\u003Ebnporc\u003C/option\u003E\n\u003Coption value=\"31\"\u003Ebp\u003C/option\u003E\n\u003Coption value=\"30\"\u003Ecrag2r\u003C/option\u003E\n\u003Coption value=\"29\"\u003Ecragr\u003C/option\u003E\n\u003Coption value=\"27\"\u003Ei\u003C/option\u003E\n\u003Coption value=\"32\"\u003Elol\u003C/option\u003E\n\u003Coption value=\"33\" selected=\"selected\"\u003Elouiel\u003C/option\u003E\u003C/select\u003E");

        m = re.search('''value=\\\\"(\d+)\\\\" selected''', r)
        if m:
            return m.group(1)
