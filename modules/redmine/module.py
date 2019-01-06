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


from weboob.capabilities.content import CapContent, Content
from weboob.capabilities.bugtracker import CapBugTracker, Issue, Project, User, \
                                           Version, Status, Update, Attachment, \
                                           Query, Change
from weboob.capabilities.collection import CapCollection, Collection, CollectionNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.exceptions import BrowserHTTPNotFound
from weboob.tools.compat import basestring, unicode
from weboob.tools.value import ValueBackendPassword, Value

from .browser import RedmineBrowser


__all__ = ['RedmineModule']


class RedmineModule(Module, CapContent, CapBugTracker, CapCollection):
    NAME = 'redmine'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = 'The Redmine project management web application'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('url',      label='URL of the Redmine website', regexp=r'https?://.*'),
                           Value('username', label='Login'),
                           ValueBackendPassword('password', label='Password'))
    BROWSER = RedmineBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['url'].get(),
                                   self.config['username'].get(),
                                   self.config['password'].get())

    ############# CapContent ######################################################

    def id2path(self, id):
        return id.split('/', 2)

    def get_content(self, id, revision=None):
        if isinstance(id, basestring):
            content = Content(id)
        else:
            content = id
            id = content.id

        try:
            _type, project, page = self.id2path(id)
        except ValueError:
            return None

        version = revision.id if revision else None
        data = self.browser.get_wiki_source(project, page, version)

        content.content = data
        return content

    def push_content(self, content, message=None, minor=False):
        try:
            _type, project, page = self.id2path(content.id)
        except ValueError:
            return

        return self.browser.set_wiki_source(project, page, content.content, message)

    def get_content_preview(self, content):
        try:
            _type, project, page = self.id2path(content.id)
        except ValueError:
            return

        return self.browser.get_wiki_preview(project, page, content.content)

    ############# CapCollection ###################################################
    def iter_resources(self, objs, split_path):
        if Project in objs or Issue in objs:
            self._restrict_level(split_path, 1)
            if len(split_path) == 0:
                return [Collection([project.id], project.name)
                        for project in self.iter_projects()]
            elif len(split_path) == 1:
                query = Query()
                query.project = unicode(split_path[0])
                return self.iter_issues(query)

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if Issue in objs and collection.path_level == 1:
            for project in self.iter_projects():
                if collection.basename == project.id:
                    return Collection([project.id], project.name)
            # if the project is not found by ID, try again by name
            for project in self.iter_projects():
                if collection.basename == project.name:
                    return Collection([project.id], project.name)
        raise CollectionNotFound(collection.split_path)

    ############# CapBugTracker ###################################################
    @classmethod
    def _build_project(cls, project_dict):
        project = Project(project_dict['name'], project_dict['name'])
        project.members = [User(int(u[0]), u[1]) for u in project_dict['members']]
        project.versions = [Version(int(v[0]), v[1]) for v in project_dict['versions']]
        project.categories = [c[1] for c in project_dict['categories']]
        # TODO set the value of status
        project.statuses = [Status(int(s[0]), s[1], 0) for s in project_dict['statuses']]
        return project

    @staticmethod
    def _attr_to_id(availables, text):
        if not text:
            return None

        if isinstance(text, basestring) and text.isdigit():
            return text

        for value, key in availables:
            if key.lower() == text.lower():
                return value

        return text

    def iter_issues(self, query):
        """
        Iter issues with optionnal patterns.

        @param  query [Query]
        @return [iter(Issue)] issues
        """
        params = self.browser.get_project(query.project)
        kwargs = {'subject':          query.title,
                  'author_id':        self._attr_to_id(params['members'], query.author),
                  'assigned_to_id':   self._attr_to_id(params['members'], query.assignee),
                  'fixed_version_id': self._attr_to_id(params['versions'], query.version),
                  'category_id':      self._attr_to_id(params['categories'], query.category),
                  'status_id':        self._attr_to_id(params['statuses'], query.status),
                 }
        r = self.browser.query_issues(query.project, **kwargs)
        project = self._build_project(r['project'])
        for issue in r['iter']:
            obj = Issue(issue['id'])
            obj.project = project
            obj.title = issue['subject']
            obj.creation = issue['created_on']
            obj.updated = issue['updated_on']
            obj.start = issue['start_date']
            obj.due = issue['due_date']

            if isinstance(issue['author'], tuple):
                obj.author = project.find_user(*issue['author'])
            else:
                obj.author = User(0, issue['author'])
            if isinstance(issue['assigned_to'], tuple):
                obj.assignee = project.find_user(*issue['assigned_to'])
            else:
                obj.assignee = issue['assigned_to']

            obj.tracker = issue['tracker']
            obj.category = issue['category']

            if issue['fixed_version'] is not None:
                obj.version = project.find_version(*issue['fixed_version'])
            else:
                obj.version = None
            obj.status = project.find_status(issue['status'])
            obj.priority = issue['priority']
            yield obj

    def get_issue(self, issue):
        if isinstance(issue, Issue):
            id = issue.id
        else:
            id = issue
            issue = Issue(issue)

        try:
            params = self.browser.get_issue(id)
        except BrowserHTTPNotFound:
            return None

        issue.project = self._build_project(params['project'])
        issue.title = params['subject']
        issue.body = params['body']
        issue.creation = params['created_on']
        issue.updated = params['updated_on']
        issue.start = params['start_date']
        issue.due = params['due_date']
        issue.fields = {}
        for key, value in params['fields'].items():
            issue.fields[key] = value
        issue.attachments = []
        for a in params['attachments']:
            attachment = Attachment(a['id'])
            attachment.filename = a['filename']
            attachment.url = a['url']
            issue.attachments.append(attachment)
        issue.history = []
        for u in params['updates']:
            update = Update(u['id'])
            update.author = issue.project.find_user(*u['author'])
            update.date = u['date']
            update.message = u['message']
            update.changes = []
            for i, (field, last, new) in enumerate(u['changes']):
                change = Change(i)
                change.field = field
                change.last = last
                change.new = new
                update.changes.append(change)
            issue.history.append(update)
        issue.author = issue.project.find_user(*params['author'])
        issue.assignee = issue.project.find_user(*params['assignee'])
        issue.tracker = params['tracker'][1]
        issue.category = params['category'][1]
        issue.version = issue.project.find_version(*params['version'])
        issue.status = issue.project.find_status(params['status'][1])
        issue.priority = params['priority'][1]

        return issue

    def create_issue(self, project):
        try:
            r = self.browser.get_project(project)
        except BrowserHTTPNotFound:
            return None

        issue = Issue(0)
        issue.project = self._build_project(r)
        issue.fields = self.browser.get_custom_fields(project)
        return issue

    def post_issue(self, issue):
        project = issue.project.id

        kwargs = {'title':      issue.title,
                  'version':    issue.version.id if issue.version else None,
                  'assignee':   issue.assignee.id if issue.assignee else None,
                  'tracker':    issue.tracker if issue.tracker else None,
                  'category':   issue.category,
                  'status':     issue.status.id if issue.status else None,
                  'priority':   issue.priority if issue.priority else None,
                  'start':      issue.start if issue.start else None,
                  'due':        issue.due if issue.due else None,
                  'body':       issue.body,
                  'fields':     issue.fields,
                 }

        if int(issue.id) < 1:
            id = self.browser.create_issue(project, **kwargs)
        else:
            id = self.browser.edit_issue(issue.id, **kwargs)

        if id is None:
            return None

        issue.id = id
        return issue

    def update_issue(self, issue, update):
        if isinstance(issue, Issue):
            issue = issue.id

        if update.hours:
            return self.browser.logtime_issue(issue, update.hours, update.message)
        else:
            return self.browser.comment_issue(issue, update.message)

    def remove_issue(self, issue):
        """
        Remove an issue.
        """
        if isinstance(issue, Issue):
            issue = issue.id

        return self.browser.remove_issue(issue)

    def iter_projects(self):
        """
        Iter projects.

        @return [iter(Project)] projects
        """
        for project in self.browser.iter_projects():
            yield Project(project['id'], project['name'])

    def get_project(self, id):
        try:
            params = self.browser.get_project(id)
        except BrowserHTTPNotFound:
            return None

        return self._build_project(params)

    def fill_issue(self, issue, fields):
        return self.get_issue(issue)

    OBJECTS = {Issue: fill_issue}
