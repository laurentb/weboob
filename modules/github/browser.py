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


from weboob.deprecated.browser import Browser
from weboob.tools.json import json as json_module
from base64 import b64encode
import datetime
import re
import os
from urllib import quote_plus


__all__ = ['GithubBrowser']


class GithubBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'api.github.com'
    ENCODING = 'utf-8'

    def __init__(self, *a, **kw):
        kw['parser'] = 'json'
        Browser.__init__(self, *a, **kw)
        self.fewer_requests = not bool(self.username)

    def home(self):
        pass

    def get_project(self, project_id):
        json = self.do_get('https://api.github.com/repos/%s' % project_id)
        return {'name': json['name'], 'id': project_id}

    def get_issue(self, project_id, issue_number):
        json = self.do_get('https://api.github.com/repos/%s/issues/%s' % (project_id, issue_number))
        return self._make_issue(project_id, issue_number, json)

    def iter_project_issues(self, project_id):
        base_url = 'https://api.github.com/repos/%s/issues' % project_id
        for json in self._paginated(base_url):
            for jissue in json:
                issue_number = jissue['number']
                yield self._make_issue(project_id, issue_number, jissue)
            if len(json) < 100:
                break

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
                issue_number = jissue['number']
                yield self._make_issue(query.project, issue_number, jissue)
            if not len(json['items']):
                break

    def post_issue(self, issue):
        base_data = self._issue_post_body(issue)
        url = 'https://api.github.com/repos/%s/issues' % issue.project.id
        json = self.do_post(url, base_data)
        issue_number = json['id']
        return self._make_issue(issue.project.id, issue_number, json)

    def edit_issue(self, issue, issue_number):
        base_data = self._issue_post_body(issue)
        url = 'https://api.github.com/repos/%s/issues/%s' % (issue.project.id, issue_number)
        self.do_patch(url, base_data)
        return issue

    def _issue_post_body(self, issue):
        data = {'title': issue.title, 'body': issue.body}
        if issue.assignee:
            data['assignee'] = issue.assignee.id
        if issue.version:
            data['milestone'] = issue.version.id
        if issue.status:
            data['state'] = issue.status.name # TODO improve if more statuses are implemented
        return json_module.dumps(data)

    def post_comment(self, issue_id, comment):
        project_id, issue_number = issue_id.rsplit('/', 1)
        url = 'https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number)
        data = json_module.dumps({'body': comment})
        self.do_post(url, data)

    # helpers
    def _make_issue(self, project_id, issue_number, json):
        d = {'number': issue_number, 'title': json['title'], 'body': json['body'], 'creation': parse_date(json['created_at']), 'updated': parse_date(json['updated_at']), 'author': json['user']['login'], 'status': json['state']}

        if json['assignee']:
            d['assignee'] = json['assignee']['login']
        else:
            d['assignee'] = None
        if json['milestone']:
            d['version'] = json['milestone']
        else:
            d['version'] = None
        d['has_comments'] = (json['comments'] > 0)
        d['attachments'] = list(self._extract_attachments(d['body']))

        # TODO fetch other updates?
        return d

    def iter_milestones(self, project_id):
        for jmilestone in self.do_get('https://api.github.com/repos/%s/milestones' % project_id):
            yield {'id': jmilestone['number'], 'name': jmilestone['title']}

    def iter_comments(self, project_id, issue_number):
        json = self.do_get('https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number))
        for jcomment in json:
            d = {'id': jcomment['id'], 'message': jcomment['body'], 'author': jcomment['user']['login'], 'date': parse_date(jcomment['created_at'])}
            d['attachments'] = list(self._extract_attachments(d['message']))
            yield d

    def _extract_attachments(self, message):
        for attach_url in re.findall(r'https://f.cloud.github.com/assets/[\w/.-]+', message):
            d = {'url': attach_url, 'filename': os.path.basename(attach_url)}
            yield d

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
        return {'id': _id, 'name': name}

    def iter_members(self, project_id):
        for json in self._paginated('https://api.github.com/repos/%s/assignees' % project_id):
            for jmember in json:
                yield {'id': jmember['login'], 'name': jmember['login']}
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

    def do_patch(self, url, data):
        class PatchRequest(self.request_class):
            def get_method(self):
                return 'PATCH'
        headers = self.auth_headers()
        headers.update({'Accept': 'application/vnd.github.preview'})
        req = PatchRequest(url, data, headers=headers)
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
