# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
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

from __future__ import unicode_literals

from weboob.capabilities.base import empty
from weboob.capabilities.bugtracker import Query
from weboob.tools.test import BackendTest


class AsanaTest(BackendTest):
    MODULE = 'asana'

    def test_iter_projects(self):
        projects = list(self.backend.iter_projects())
        self.assertTrue(projects)
        self.assertTrue(projects[0].statuses)
        self.assertTrue(projects[0].members)

    def test_find_any_issues(self):
        projects = list(self.backend.iter_projects())
        self.assertTrue(projects)

        q = Query()
        q.project = projects[0]

        issues = [issue for issue, _ in zip(self.backend.iter_issues(q), range(30))]
        self.assertTrue(issues)

        for issue in issues:
            self.assertTrue(issue.project)
            self.assertEquals(issue.project.id, projects[0].id)
            self.assertTrue(issue.title)
            self.assertFalse(empty(issue.body))
            self.assertTrue(issue.creation)

            self.assertTrue(issue.author, issue.title)

    def _test_find_by_criterion(self, attr, first_cb=None, matcher_cb=None):
        if matcher_cb is None:
            def matcher_cb(expected, actual):
                self.assertEquals(expected.id, actual.id, 'different id on: %s != %s' % (expected, actual))

        if first_cb is None:
            def first_cb(obj):
                return bool(obj)

        projects = list(self.backend.iter_projects())
        self.assertTrue(projects)

        q = Query()
        q.project = projects[0]

        for issue, _ in zip(self.backend.iter_issues(q), range(30)):
            criterion_obj = getattr(issue, attr)
            if first_cb(criterion_obj):
                break
        else:
            assert False, 'not a single issue has this criterion'

        setattr(q, attr, criterion_obj)

        some = False
        for issue, _ in zip(self.backend.iter_issues(q), range(30)):
            some = True
            fetched_obj = getattr(issue, attr)
            matcher_cb(criterion_obj, fetched_obj)
        assert some, 'the issue searched for was not found'

    def test_find_by_assignee(self):
        self._test_find_by_criterion('assignee')

    def test_find_by_author(self):
        self._test_find_by_criterion('author')

    def test_find_by_title(self):
        self._test_find_by_criterion(
            'title',
            matcher_cb=lambda crit, actual: self.assertIn(crit.lower(), actual.lower())
        )

    def test_find_by_tags(self):
        self._test_find_by_criterion(
            'tags',
            first_cb=lambda tags: bool(tags),
            matcher_cb=lambda crit, actual: self.assertLessEqual(set(crit), set(actual))
        )

    def _test_find_by_fields(self):
        self._test_find_by_criterion(
            'fields',
            first_cb=lambda tags: bool(tags),
            matcher_cb=lambda crit, actual: self.assertLessEqual(set(crit), set(actual))
        )

    def test_find_by_status(self):
        projects = list(self.backend.iter_projects())
        self.assertTrue(projects)

        q = Query()
        q.project = projects[0]
        q.status = 'open'

        for issue, _ in zip(self.backend.iter_issues(q), range(30)):
            self.assertEquals(issue.status.name.lower(), 'open', issue.title)

        q.status = 'closed'
        for issue, _ in zip(self.backend.iter_issues(q), range(30)):
            self.assertEquals(issue.status.name.lower(), 'closed', issue.title)

    def test_read_comments(self):
        projects = list(self.backend.iter_projects())
        self.assertTrue(projects)

        q = Query()
        q.project = projects[0]

        for issue, _ in zip(self.backend.iter_issues(q), range(30)):
            self.backend.fillobj(issue, ['history'])
            self.assertNotEmpty(issue.history)
            if issue.history:
                for update in issue.history:
                    self.assertTrue(update.author)
                    self.assertTrue(update.author.id)
                    self.assertTrue(update.author.name)
                    self.assertTrue(update.date)
                    self.assertTrue(update.message)
                    self.assertNotEmpty(update.changes)

                break
        else:
            assert 0, 'no issue had history'
