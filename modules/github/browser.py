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


from weboob.tools.browser import BaseBrowser
from weboob.capabilities.bugtracker import Issue, Project, User, Version, Status, Update, Attachment
from weboob.tools.json import json as json_module
from base64 import b64encode
import datetime
import re
import os
from urllib import quote_plus


__all__ = ['GithubBrowser']


STATUSES = {'open': Status('open', u'Open', Status.VALUE_NEW),
            'closed': Status('closed', u'closed', Status.VALUE_RESOLVED)}
# TODO tentatively parse github "labels"?

class GithubBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'api.github.com'
    ENCODING = 'utf-8'

    def __init__(self, *a, **kw):
        kw['parser'] = 'json'
        BaseBrowser.__init__(self, *a, **kw)
        self.fewer_requests = not bool(self.username)

    def home(self):
        pass

    def get_project(self, _id):
        json = self.do_get('https://api.github.com/repos/%s' % _id)

        project = Project(_id, json['name'])
        project.members = list(self.iter_members(_id))
        project.statuses = list(STATUSES.values())
        project.categories = []
        project.versions = list(self._get_milestones(_id))
        return project

    def get_issue(self, _id, fetch_project=True):
        project_id, issue_number = _id.rsplit('/', 1)
        json = self.do_get('https://api.github.com/repos/%s/issues/%s' % (project_id, issue_number))
        return self.make_issue(_id, json, fetch_project)

    def iter_issues(self, query):
        qsparts = ['repo:%s' % query.project]
        if query.assignee:
            qsparts.append('assignee:%s' % query.assignee)
        if query.author:
            qsparts.append('author:%s' % query.author)
        if query.status:
            qsparts.append('state:%s' % query.status)
        if query.title:
            qsparts.append('%s in:title' % query.title)
        
        qs = quote_plus(' '.join(qsparts))

        base_url = 'https://api.github.com/search/issues?q=%s' % qs
        for json in self._paginated(base_url):
            for jissue in json['items']:
                issue_id = '%s/%s' % (query.project, jissue['number'])
                yield self.make_issue(issue_id, jissue)
            if not len(json['items']):
                break

    def post_issue(self, issue):
        data = {'title': issue.title, 'body': issue.body}
        if issue.assignee:
            data['assignee'] = issue.assignee.id
        if issue.version:
            data['milestone'] = issue.version.id
        base_data = json_module.dumps(data)
        url = 'https://api.github.com/repos/%s/issues' % issue.project.id
        json = self.do_post(url, base_data)
        issue_id = '%s/%s' % (issue.project.id, json['id'])
        return self.make_issue(issue_id, json)

    def post_comment(self, issue_id, comment):
        project_id, issue_number = issue_id.rsplit('/', 1)
        url = 'https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number)
        data = json_module.dumps({'body': comment})
        self.do_post(url, data)

    # helpers
    def make_issue(self, _id, json, fetch_project=True):
        project_id, issue_number = _id.rsplit('/', 1)
        issue = Issue(_id)
        issue.title = json['title']
        issue.body = json['body']
        issue.category = None
        issue.creation = parse_date(json['created_at'])
        issue.updated = parse_date(json['updated_at'])
        issue.attachments = list(self._get_attachments(issue.body))
        if fetch_project:
            issue.project = self.get_project(project_id)
        issue.author = self.get_user(json['user']['login'])
        if json['assignee']:
            issue.assignee = self.get_user(json['assignee']['login'])
        else:
            issue.assignee = None
        issue.status = STATUSES[json['state']]
        if json['milestone']:
            issue.version = self.make_milestone(json['milestone'])
        if json['comments'] > 0:
            issue.history = [comment for comment in self.get_comments(project_id, issue_number)]
        else:
            issue.history = []
        # TODO fetch other updates?
        return issue

    def _get_milestones(self, project_id):
        for jmilestone in self.do_get('https://api.github.com/repos/%s/milestones' % project_id):
            yield self.make_milestone(jmilestone)

    def make_milestone(self, json):
        return Version(json['number'], json['title'])

    def get_comments(self, project_id, issue_number):
        json = self.do_get('https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number))
        for jcomment in json:
            comment = Update(jcomment['id'])
            comment.message = jcomment['body']
            comment.author = self.make_user(jcomment['user']['login'])
            comment.date = parse_date(jcomment['created_at'])
            comment.changes = []
            comment.attachments = list(self._get_attachments(comment.message))
            yield comment

    def _get_attachments(self, message):
        for attach_url in re.findall(r'https://f.cloud.github.com/assets/[\w/.-]+', message):
            attach = Attachment(attach_url)
            attach.url = attach_url
            attach.filename = os.path.basename(attach_url)
            yield attach

    def _paginated(self, url, start_at=1):
        while True:
            if '?' in url:
                page_url = '%s&per_page=100&page=%s' % (url, start_at)
            else:
                page_url = '%s?per_page=100&page=%s' % (url, start_at)
            yield self.do_get(page_url)
            start_at += 1

    def get_user(self, _id):
        json = self.do_get('https://api.github.com/users/%s' % _id)
        if 'name' in json:
            name = json['name']
        else:
            name = _id # wasted one request...
        return User(_id, name)
    
    def make_user(self, name):
        return User(name, name)

    def iter_members(self, project_id):
        for json in self._paginated('https://api.github.com/repos/%s/assignees' % project_id):
            for jmember in json:
                user = self.make_user(jmember['login']) # no request, no name
                yield user
            if len(json) < 100:
                break

    def do_get(self, url):
        headers = self.auth_headers()
        headers.update({'Accept': 'application/vnd.github.preview'})
        req = self.request_class(url, None, headers=headers)
        return self.get_document(self.openurl(req))

    def do_post(self, url, data):
        headers = self.auth_headers()
        headers.update({'Accept': 'application/vnd.github.preview'})
        req = self.request_class(url, data, headers=headers)
        return self.get_document(self.openurl(req))

    def auth_headers(self):
        if self.username:
            return {'Authorization': 'Basic %s' % b64encode('%s:%s' % (self.username, self.password))}
        else:
            return {}

# TODO use a cache for objects and/or pages?
# TODO use an api-key?

def parse_date(s):
    if s.endswith('Z'):
        s = s[:-1]

    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
