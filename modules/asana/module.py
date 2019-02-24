# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
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

from weboob.capabilities.base import empty
from weboob.capabilities.bugtracker import CapBugTracker, Project, Issue, User
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import AsanaBrowser


__all__ = ['AsanaModule']


class AsanaModule(Module, CapBugTracker):
    NAME = 'asana'
    DESCRIPTION = 'Asana'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    CONFIG = BackendConfig(ValueBackendPassword('token', label='Personal access token'))

    BROWSER = AsanaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['token'].get())

    ## read-only issues and projects
    def iter_issues(self, query):
        query = query.copy()

        params = {}

        if query.title:
            params['text'] = query.title

        if query.project:
            if not isinstance(query.project, Project):
                query.project = next(p for p in self.iter_projects() if query.project.lower() in p.name.lower())
            params['project'] = query.project.id

            if query.tags:
                params['tags.all'] = ','.join(query.project._tagdict[tag] for tag in query.tags)

        if query.assignee:
            if isinstance(query.assignee, User):
                params['assignee'] = query.assignee.id
            else:
                params['assignee'] = query.assignee

        if query.author:
            if isinstance(query.author, User):
                params['created_by'] = query.author.id
            else:
                params['created_by'] = query.author

        if query.status:
            if query.status.lower() == 'closed':
                params['completed'] = 'true'
            else:
                params['completed'] = 'false'
                params['completed_since'] = 'now' # completed=false is not enough...

        if not query.project:
            workspaces = list(self._iter_workspaces())
            if len(workspaces) == 1:
                params['workspace'] = workspaces[0]

        if query.project and query.assignee:
            # asana's wtf api doesn't allow more than 1 filter...
            del params['project']
            params['workspace'] = query.project._workspace

        opt = '?opt_fields=%s' % ','.join([
            'name', 'completed', 'due_at', 'due_on', 'created_at', 'modified_at',
            'notes', 'custom_fields', 'tags.name', 'assignee.name', 'created_by.name',
            'projects.name', 'projects.workspace',
        ])
        if params:
            data = self.browser.paginate('tasks%s' % opt, params=params)
        else:
            data = []

        for issue in data:
            issue = self.browser._make_issue(issue)
            if issue is None:  # section
                continue

            # post-filter because many server-side filters don't always work...
            if query.title and query.title.lower() not in issue.title.lower():
                self.logger.debug('"title" filter failed on issue %r', issue)
                continue

            if query.status and query.status.lower() != issue.status.name.lower():
                self.logger.debug('"completed" filter failed on issue %r', issue)
                continue

            if query.tags and not (set(query.tags) <= set(issue.tags)):
                self.logger.debug('"tags" filter failed on issue %r', issue)
                continue

            if query.author:
                if isinstance(query.author, User):
                    if query.author.id != issue.author.id:
                        continue
                else:
                    if query.author.lower() != issue.author.name.lower():
                        continue

            yield issue

    def _set_stories(self, issue):
        ds = self.browser.request('tasks/%s/stories' % issue.id)['data']
        issue.history = [self.browser._make_update(d) for d in ds]

    def get_issue(self, id):
        if not id.isdigit():
            return

        data = self.browser.request('tasks/%s' % id)['data']
        return self.browser._make_issue(data)

    def iter_projects(self):
        for w in self._iter_workspaces():
            tags = self.browser.request('tags?workspace=%s' % w)['data']
            data = self.browser.paginate('projects?opt_fields=name,members.name,workspace&workspace=%s' % w)
            for p in data:
                project = self.browser._make_project(p)
                self._assign_tags(tags, project)
                yield project

    def _assign_tags(self, data, project):
        project._tagdict = {d['name']: str(d['id']) for d in data}
        project.tags = list(project._tagdict)

    def get_project(self, id):
        if not id.isdigit():
            return

        data = self.browser.request('projects/%s' % id)['data']
        return self.browser._make_project(data)

    def _iter_workspaces(self):
        return (d['id'] for d in self.browser.paginate('workspaces'))

    ## writing issues
    def create_issue(self, project):
        issue = Issue(0)
        issue._project = project
        return issue

    def post_issue(self, issue):
        data = {}
        if issue.title:
            data['name'] = issue.title
        if issue.body:
            data['notes'] = issue.body
        if issue.due:
            data['due_at'] = issue.due.strftime('%Y-%m-%d')
        if issue.assignee:
            data['assignee'] = issue.assignee.id

        if issue.id and issue.id != '0':
            data['projects'] = issue._project
            self.browser.request('tasks', data=data)
            if issue.tags:
                self._set_tag_list(issue, True)
        else:
            self.browser.request('tasks/%s' % issue.id, data=data, method='PUT')
            if not empty(issue.tags):
                self._set_tag_list(issue)

    def _set_tag_list(self, issue, add=False):
        to_remove = set()
        to_add = set(issue.tags)

        if not add:
            existing = set(self.get_issue(issue.id).tags)
            to_add = to_add - existing
            to_remove = existing - to_add

        for old in to_remove:
            tagid = issue.project._tagdict[old]
            self.browser.request('tasks/%s/removeTag', data={'tag': tagid})
        for new in to_add:
            tagid = issue.project._tagdict[new]
            self.browser.request('tasks/%s/addTag', data={'tag': tagid})

    def update_issue(self, issue, update):
        assert not update.changes, 'changes are not supported yet'
        assert update.message
        self.browser.request('tasks/%s/stories' % issue.id, data={'text': update.message})

    def remove_issue(self, issue):
        self.browser.request('tasks/%s' % issue.id, method='DELETE')

    ## filling
    def fill_project(self, project, fields):
        if set(['members']) & set(fields):
            return self.get_project(project.id)

    def fill_issue(self, issue, fields):
        if set(['body', 'assignee', 'due', 'creation', 'updated', 'project']) & set(fields):
            new = self.get_issue(issue.id)
            for f in fields:
                if getattr(new, f):
                    setattr(issue, f, getattr(new, f))
        if 'history' in fields:
            self._set_stories(issue)

    OBJECTS = {
        Project: fill_project,
        Issue: fill_issue,
    }
