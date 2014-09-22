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


from weboob.tools.test import BackendTest
from weboob.capabilities.bugtracker import Query


class GithubTest(BackendTest):
    MODULE = 'github'

    def test_project(self):
        project = self.backend.get_project('github/hubot')
        assert project
        assert project.name
        assert project.members

    def test_issue(self):
        issue = self.backend.get_issue('github/hubot/1')
        assert issue
        assert issue.title
        assert issue.body
        assert issue.creation
        assert issue.history

    def test_search(self):
        query = Query()
        query.project = u'github/hubot'
        query.status = u'closed'
        query.title = u'fix'
        issues = self.backend.iter_issues(query)
        issue = issues.next()
        assert issue.status.name == 'closed'
