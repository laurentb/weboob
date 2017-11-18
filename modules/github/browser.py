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


import datetime
import re
import os

from weboob.browser.browsers import APIBrowser
from weboob.browser.cache import CacheMixin
from weboob.browser.exceptions import ClientError
from weboob.tools.compat import quote_plus

__all__ = ['GithubBrowser']


class GithubBrowser(CacheMixin, APIBrowser):
    BASEURL = 'https://api.github.com'

    def __init__(self, username, password, *a, **kw):
        super(GithubBrowser, self).__init__(*a, **kw)
        self.username = username
        self.password = password
        self.fewer_requests = not bool(self.username)

    def get_project(self, project_id):
        json = self.request('https://api.github.com/repos/%s' % project_id)
        return {
            'name': json['name'],
            'id': project_id
        }

    def get_issue(self, project_id, issue_number):
        json = self.request('https://api.github.com/repos/%s/issues/%s' % (project_id, issue_number))
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
        base_data = self._issue_post_data(issue)
        url = 'https://api.github.com/repos/%s/issues' % issue.project.id
        json = self.request(url, data=base_data)
        issue_number = json['number']
        return self._make_issue(issue.project.id, issue_number, json)

    def edit_issue(self, issue, issue_number):
        base_data = self._issue_post_data(issue)
        url = 'https://api.github.com/repos/%s/issues/%s' % (issue.project.id, issue_number)
        self.open(url, data=base_data, method='PATCH')
        return issue

    def _issue_post_data(self, issue):
        data = {
            'title': issue.title,
            'body': issue.body
        }

        if issue.assignee:
            data['assignee'] = issue.assignee.id
        if issue.version:
            data['milestone'] = issue.version.id
        if issue.status:
            data['state'] = issue.status.name # TODO improve if more statuses are implemented
        return data

    def post_comment(self, issue_id, comment):
        project_id, issue_number = issue_id.rsplit('/', 1)
        url = 'https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number)
        data = {'body': comment}
        self.request(url, data=data)

    # helpers
    def _make_issue(self, project_id, issue_number, json):
        d = {}
        d['number'] = issue_number
        d['title'] = json['title']
        d['body'] = json['body'].strip()
        d['creation'] = parse_date(json['created_at'])
        d['updated'] = parse_date(json['updated_at'])
        d['author'] = json['user']['login']
        d['status'] = json['state']
        d['url'] = 'https://github.com/%s/issues/%s' % (project_id, issue_number)

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
        url = 'https://api.github.com/repos/%s/milestones' % project_id
        for jmilestone in self.request(url):
            yield {
                'id': jmilestone['number'],
                'name': jmilestone['title']
            }

    def iter_comments(self, project_id, issue_number):
        url = 'https://api.github.com/repos/%s/issues/%s/comments' % (project_id, issue_number)
        for json in self._paginated(url):
            for jcomment in json:
                d = {}
                d['id'] = jcomment['id']
                d['message'] = jcomment['body']
                d['author'] = jcomment['user']['login']
                d['date'] = parse_date(jcomment['created_at'])
                d['attachments'] = list(self._extract_attachments(d['message']))
                yield d
            if len(json) < 100:
                break

    def _extract_attachments(self, message):
        for attach_url in re.findall(r'https://f.cloud.github.com/assets/[\w/.-]+', message):
            yield {
                'url': attach_url,
                'filename': os.path.basename(attach_url)
            }

    def _paginated(self, url, start_at=1):
        while True:
            if '?' in url:
                page_url = '%s&per_page=100&page=%s' % (url, start_at)
            else:
                page_url = '%s?per_page=100&page=%s' % (url, start_at)
            yield self.request(page_url)
            start_at += 1

    def get_user(self, _id):
        json = self.request('https://api.github.com/users/%s' % _id)
        if 'name' in json:
            name = json['name']
        else:
            name = _id # wasted one request...
        return {
            'id': _id,
            'name': name
        }

    def iter_members(self, project_id):
        url = 'https://api.github.com/repos/%s/assignees' % project_id
        for json in self._paginated(url):
            for jmember in json:
                yield {
                    'id': jmember['login'],
                    'name': jmember['login']
                }
            if len(json) < 100:
                break

    def get_rate_limit(self):
        return self.request('/rate_limit')

    def _extract_rate_info(self, headers):
        left = headers.get('X-RateLimit-Remaining')
        total = headers.get('X-RateLimit-Limit')
        end = headers.get('X-RateLimit-Reset')
        return left, total, end

    def open(self, *args, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Accept'] = 'application/vnd.github.v3+json'
        kwargs.update(**self.auth_headers())

        left = total = end = None
        try:
            ret = super(GithubBrowser, self).open_with_cache(*args, **kwargs)
        except ClientError as err:
            left, total, end = self._extract_rate_info(err.response.headers)
            raise
        else:
            left, total, end = self._extract_rate_info(ret.headers)
        finally:
            self.logger.debug('github API request quota: %s/%s (end at %s)',
                              left, total, end)
        return ret

    def auth_headers(self):
        if self.username:
            return {'auth': (self.username, self.password)}
        else:
            return {}

# TODO use a cache for objects and/or pages?


def parse_date(s):
    if s.endswith('Z'):
        s = s[:-1]

    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
