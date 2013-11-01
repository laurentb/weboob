# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.bugtracker import ICapBugTracker, Issue

from .browser import GithubBrowser


__all__ = ['GithubBackend']


class GithubBackend(BaseBackend, ICapBugTracker):
    NAME = 'github'
    DESCRIPTION = u'GitHub issues tracking'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '0.h'
    CONFIG = BackendConfig(Value('username', label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''))

    BROWSER = GithubBrowser

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
        else:
            password = None
        return self.create_browser(username, password)

    def get_project(self, _id):
        return self.browser.get_project(_id)

    def get_issue(self, _id):
        return self.browser.get_issue(_id)

    def iter_issues(self, query):
        if ((query.assignee, query.author, query.status, query.title) ==
                                             (None, None, None, None)):
            it = self.browser.iter_project_issues(query.project)
        else:
            it = self.browser.iter_issues(query)

        for issue in it:
            yield issue

    def create_issue(self, project_id):
        issue = Issue(0)
        issue.project = self.browser.get_project(project_id)
        return issue

    def post_issue(self, issue):
        assert not issue.attachments
        self.browser.post_issue(issue)

    def update_issue(self, issue_id, update):
        assert not update.attachments
        self.browser.post_comment(issue_id, update.message)

    # iter_projects, remove_issue are impossible

