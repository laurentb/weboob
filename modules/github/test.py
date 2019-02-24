# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from time import time

from weboob.tools.test import BackendTest, skip_without_config
from weboob.capabilities.bugtracker import Query, Version, User, Status, Update


class GithubTest(BackendTest):
    MODULE = 'github'

    def test_project(self):
        project = self.backend.get_project('weboobie/testing')

        assert project
        self.assertEqual(project.name, 'testing')
        self.assertEqual(project.id, 'weboobie/testing')

        assert all(isinstance(user, User) for user in project.members)
        assert any(user.name == 'weboobie' for user in project.members)

        assert all(isinstance(version, Version) for version in project.versions)
        assert any(version.name == u'1.0' for version in project.versions)

        assert project.find_status('open').value == Status.VALUE_NEW
        assert project.find_status('closed').value == Status.VALUE_RESOLVED

    def test_get_issue(self):
        issue = self.backend.get_issue('weboobie/testing/1')

        assert issue
        self.assertEqual(issue.id, 'weboobie/testing/1')
        self.assertEqual(issue.title, 'an open issue')
        assert 'Hello' in issue.body
        assert issue.creation

        assert issue.history

    def test_search(self):
        query = Query()
        query.project = 'weboobie/testing'
        query.status = 'closed'
        query.title = 'fix'
        issues = iter(self.backend.iter_issues(query))
        issue = next(issues)
        assert issue.status.name == 'closed'
        assert 'fix' in issue.title

    @skip_without_config('username', 'password')
    def test_post_issue(self):
        project = self.backend.get_project('weboobie/testing')
        assert project

        issue = self.backend.create_issue(project.id)
        issue.title = 'posting an issue'
        issue.body = 'body of the issue'
        issue.version = project.versions[0]

        self.backend.post_issue(issue)
        assert issue.id

        fetched = self.backend.get_issue(issue.id)
        self.assertEqual(issue.title, fetched.title)
        self.assertEqual(issue.body, fetched.body)
        self.assertEqual(fetched.status.name, 'open')

    @skip_without_config('username', 'password')
    def test_post_comment(self):
        issue = self.backend.get_issue('weboobie/testing/26')
        assert issue

        ts = str(int(time()))
        update = Update(0)
        update.message = "Yes! It's now %s" % ts
        self.backend.update_issue(issue, update)

        new = self.backend.get_issue('weboobie/testing/26')
        assert any(ts in upd.message for upd in new.history)

    @skip_without_config('username', 'password')
    def test_change_status(self):
        issue = self.backend.get_issue('weboobie/testing/30')
        assert issue

        closing = (issue.status.name != 'closed')
        if closing:
            issue.status = issue.project.find_status('closed')
        else:
            issue.status = issue.project.find_status('open')

        self.backend.post_issue(issue)

        new = self.backend.get_issue('weboobie/testing/30')
        if closing:
            self.assertEqual(new.status.name, 'closed')
        else:
            self.assertEqual(new.status.name, 'open')
