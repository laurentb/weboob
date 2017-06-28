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


import re
import lxml.html

from weboob.capabilities.bugtracker import IssueError
from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.compat import urlsplit, urlencode, quote

from .pages.index import LoginPage, IndexPage, MyPage, ProjectsPage
from .pages.wiki import WikiPage, WikiEditPage
from .pages.issues import IssuesPage, IssuePage, NewIssuePage, IssueLogTimePage, \
                          IssueTimeEntriesPage


__all__ = ['RedmineBrowser']


# Browser
class RedmineBrowser(Browser):
    ENCODING = 'utf-8'
    PAGES = {
        'https?://[^/]+/':                                        IndexPage,
        'https?://[^/]+/login':                                   LoginPage,
        # compatibility with redmine 0.9
        'https?://[^/]+/login\?back_url.*':                       MyPage,
        'https?://[^/]+/my/page':                                 MyPage,
        'https?://[^/]+/projects':                                ProjectsPage,
        'https?://[^/]+/projects/([\w-]+)/wiki/([^\/]+)/edit(?:\?version=\d+)?': WikiEditPage,
        'https?://[^/]+/projects/[\w-]+/wiki/[^\/]*':             WikiPage,
        'https?://[^/]+/projects/[\w-]+/issues/new':              NewIssuePage,
        'https?://[^/]+/projects/[\w-]+/issues':                  IssuesPage,
        'https?://[^/]+/issues(|/?\?.*)':                         IssuesPage,
        'https?://[^/]+/issues/(\d+)':                            IssuePage,
        'https?://[^/]+/issues/(\d+)/time_entries/new':           IssueLogTimePage,
        'https?://[^/]+/projects/[\w-]+/time_entries':            IssueTimeEntriesPage,
    }

    def __init__(self, url, *args, **kwargs):
        self._userid = 0
        v = urlsplit(url)
        self.PROTOCOL = v.scheme
        self.DOMAIN = v.netloc
        self.BASEPATH = v.path
        if self.BASEPATH.endswith('/'):
            self.BASEPATH = self.BASEPATH[:-1]
        Browser.__init__(self, *args, **kwargs)
        self.projects = {}

    def is_logged(self):
        return self.is_on_page(LoginPage) or self.page and len(self.page.document.getroot().cssselect('a.my-account')) == 1

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('%s/login' % self.BASEPATH, no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        divs = self.page.document.getroot().cssselect('div#loggedas')
        if len(divs) > 0:
            parts = divs[0].find('a').attrib['href'].split('/')
            self._userid = int(parts[2])

    def get_userid(self):
        return self._userid

    def get_wiki_source(self, project, page, version=None):
        url = '%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, quote(page.encode('utf-8')))
        if version:
            url += '?version=%s' % version
        self.location(url)
        return self.page.get_source()

    def set_wiki_source(self, project, page, data, message):
        self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, quote(page.encode('utf-8'))))
        self.page.set_source(data, message)

    def get_wiki_preview(self, project, page, data):
        if (not self.is_on_page(WikiEditPage) or self.page.groups[0] != project
                or self.page.groups[1] != page):
            self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH,
                                                           project, quote(page.encode('utf-8'))))
        url = '%s/projects/%s/wiki/%s/preview' % (self.BASEPATH, project, quote(page.encode('utf-8')))
        params = {}
        params['content[text]'] = data.encode('utf-8')
        params['authenticity_token'] = "%s" % self.page.get_authenticity_token()
        preview_html = lxml.html.fragment_fromstring(self.readurl(url,
                                                    urlencode(params)),
                                                    create_parent='div')
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

    def query_issues(self, project_name, **kwargs):
        self.location('/projects/%s/issues' % project_name)
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
        for key, value in kwargs.iteritems():
            if value:
                value = self.page.get_value_from_label(self.METHODS[method]['value'] % key, value)
                data += ((self.METHODS[method]['value'] % key, value),)
                data += ((self.METHODS[method]['field'], key),)
                data += ((self.METHODS[method]['operator'] % key, '~'),)

        if method == 'POST':
            self.location('/issues?set_filter=1&per_page=100', urlencode(data))
        else:
            data += (('set_filter', '1'), ('per_page', '100'))
            self.location(self.buildurl('/issues', *data))

        assert self.is_on_page(IssuesPage)
        return {'project': self.page.get_project(project_name),
                'iter':    self.page.iter_issues(),
               }

    def get_project(self, project):
        self.location('/projects/%s/issues/new' % project)
        assert self.is_on_page(NewIssuePage)

        return self.page.get_project(project)

    def get_issue(self, id):
        self.location('/issues/%s' % id)

        assert self.is_on_page(IssuePage)
        return self.page.get_params()

    def logtime_issue(self, id, hours, message):
        self.location('/issues/%s/time_entries/new' % id)

        assert self.is_on_page(IssueLogTimePage)
        self.page.logtime(hours.seconds/3600, message)

    def comment_issue(self, id, message):
        self.location('/issues/%s' % id)

        assert self.is_on_page(IssuePage)
        self.page.fill_form(note=message)

    def get_custom_fields(self, project):
        self.location('/projects/%s/issues/new' % project)
        assert self.is_on_page(NewIssuePage)

        fields = {}
        for key, div in self.page.iter_custom_fields():
            if 'value' in div.attrib:
                fields[key] = div.attrib['value']
            else:
                olist = div.xpath('.//option[@selected="selected"]')
                fields[key] = ', '.join([i.attrib['value'] for i in olist])

        return fields

    def create_issue(self, project, **kwargs):
        self.location('/projects/%s/issues/new' % project)

        assert self.is_on_page(NewIssuePage)
        self.page.fill_form(**kwargs)

        error = self.page.get_errors()
        if len(error) > 0:
            raise IssueError(error)

        assert self.is_on_page(IssuePage)
        return int(self.page.groups[0])

    def edit_issue(self, id, **kwargs):
        self.location('/issues/%s' % id)

        assert self.is_on_page(IssuePage)
        self.page.fill_form(**kwargs)

        assert self.is_on_page(IssuePage)
        return int(self.page.groups[0])

    def remove_issue(self, id):
        self.location('/issues/%s' % id)

        assert self.is_on_page(IssuePage)
        token = self.page.get_authenticity_token()

        data = (('authenticity_token', token),)
        self.openurl('/issues/%s/destroy' % id, urlencode(data))

    def iter_projects(self):
        self.location('/projects')

        return self.page.iter_projects()

    def create_category(self, project, name, token):
        data = {'issue_category[name]': name.encode('utf-8')}
        headers = {'X-CSRF-Token': token,
                   'X-Prototype-Version': '1.7',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
                  }
        request = self.request_class(self.absurl(self.buildurl('%s/projects/%s/issue_categories' % (self.BASEPATH, project), **data)),
                                     '', headers)
        r = self.readurl(request)

        # Element.replace("issue_category_id", "\u003Cselect id=\"issue_category_id\" name=\"issue[category_id]\"\u003E\u003Coption\u003E\u003C/option\u003E\u003Coption value=\"28\"\u003Ebnporc\u003C/option\u003E\n\u003Coption value=\"31\"\u003Ebp\u003C/option\u003E\n\u003Coption value=\"30\"\u003Ecrag2r\u003C/option\u003E\n\u003Coption value=\"29\"\u003Ecragr\u003C/option\u003E\n\u003Coption value=\"27\"\u003Ei\u003C/option\u003E\n\u003Coption value=\"32\"\u003Elol\u003C/option\u003E\n\u003Coption value=\"33\" selected=\"selected\"\u003Elouiel\u003C/option\u003E\u003C/select\u003E");

        m = re.search('''value=\\\\"(\d+)\\\\" selected''', r)
        if m:
            return m.group(1)
