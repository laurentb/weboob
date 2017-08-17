# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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

from collections import OrderedDict
import datetime
import re

import dateutil.parser

from weboob.browser.browsers import DomainBrowser
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.content import Revision
from weboob.tools.compat import urlsplit, urljoin, basestring

__all__ = ['MediawikiBrowser']


class APIError(Exception):
    pass


# Browser
class MediawikiBrowser(DomainBrowser):
    ENCODING = 'utf-8'

    def __init__(self, url, apiurl, username, password, *args, **kwargs):
        url_parsed = urlsplit(url)
        self.PROTOCOL = url_parsed.scheme
        self.DOMAIN = url_parsed.netloc
        self.BASEPATH = url_parsed.path
        if self.BASEPATH.endswith('/'):
            self.BASEPATH = self.BASEPATH[:-1]

        self.apiurl = apiurl
        self.username = username
        self.password = password
        DomainBrowser.__init__(self, *args, **kwargs)

    def url2page(self, page):
        baseurl = self.PROTOCOL + '://' + self.DOMAIN + self.BASEPATH
        m = re.match('^' + urljoin(baseurl, 'wiki/(.+)$'), page)
        if m:
            return m.group(1)
        else:
            return page

    def get_wiki_source(self, page, rev=None):
        assert isinstance(self.apiurl, basestring)

        page = self.url2page(page)

        data = {'action':           'query',
                'prop':             'revisions|info',
                'titles':           page,
                'rvprop':           'content|timestamp|ids',
                'rvlimit':          '1',
                }
        if rev:
            data['rvstartid'] = rev

        result = self.API_get(data)
        pageid = list(result['query']['pages'].keys())[0]
        if pageid == "-1":    # Page does not exist
            return ""

        if 'revisions' not in repr(result['query']['pages'][str(pageid)]):
            raise APIError('Revision %s does not exist' % rev)
        if rev and result['query']['pages'][str(pageid)]['revisions'][0]['revid'] != int(rev):
            raise APIError('Revision %s does not exist' % rev)

        return result['query']['pages'][str(pageid)]['revisions'][0]['*']

    def get_token(self, page, _type):
        ''' _type can be edit, delete, protect, move, block, unblock, email or import'''
        if len(self.username) > 0 and not self.is_logged():
            self.login()

        data = {'action':      'query',
                'meta':        'tokens',
                'type':        'csrf',
                }
        result = self.API_get(data)
        return result['query']['tokens']['csrftoken']

    def set_wiki_source(self, content, message=None, minor=False):
        if len(self.username) > 0 and not self.is_logged():
            self.login()

        page = content.id
        token = self.get_token(page, 'edit')

        data = {'action':      'edit',
                'title':       page,
                'text':        content.content.encode('utf-8'),
                'summary':     message,
                }
        if minor:
            data['minor'] = 'true'
        data = OrderedDict(data)
        data['token'] = token

        self.API_post(data)

    def get_wiki_preview(self, content, message=None):
        data = {'action':     'parse',
                'title':      content.id,
                'text':       content.content.encode('utf-8'),
                'summary':    message,
                }
        result = self.API_post(data)
        return result['parse']['text']['*']

    def is_logged(self):
        data = {'action':     'query',
                'meta':       'userinfo',
                }
        result = self.API_get(data)
        return result['query']['userinfo']['id'] != 0

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.apiurl, basestring)

        data = {'action':       'login',
                'lgname':       self.username,
                'lgpassword':   self.password,
                }
        result = self.API_post(data)
        if result['login']['result'] == 'WrongPass':
            raise BrowserIncorrectPassword()

        if result['login']['result'] == 'NeedToken':
            data['lgtoken'] = result['login']['token']
            self.API_post(data)

    def iter_wiki_revisions(self, page):
        """
        Yield 'Revision' objects.
        """
        if len(self.username) > 0 and not self.is_logged():
            self.login()

        MAX_RESULTS = 50
        results = MAX_RESULTS
        last_id = None

        while results == MAX_RESULTS:
            data = {'action':       'query',
                    'titles':       page,
                    'prop':         'revisions',
                    'rvprop':       'ids|timestamp|comment|user|flags',
                    'rvlimit':      str(MAX_RESULTS),
                    }

            if last_id is not None:
                data['rvstartid'] = last_id

            result = self.API_get(data)
            pageid = str(list(result['query']['pages'].keys())[0])

            results = 0
            if pageid != "-1":
                for rev in result['query']['pages'][pageid]['revisions']:
                    rev_content = Revision(str(rev['revid']))
                    rev_content.comment = rev['comment']
                    rev_content.author = rev['user']
                    rev_content.timestamp = datetime.datetime.strptime(rev['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
                    rev_content.minor = 'minor' in rev
                    yield rev_content

                    last_id = rev_content.id
                    results += 1

    def _common_file_request(self):
        return {'action':       'query',
                'prop':         'info|imageinfo',
                'inprop':       'url',
                'iiprop':       'extmetadata|size|url|canonicaltitle',
                'iiurlwidth':   512,
                'iiurlheight':  512,
               }

    def _common_parse_file(self, info):
        res = {'canonicalurl': info['canonicalurl'],
               'title':        info['title'],
               'size':         info['imageinfo'][0]['size'],
              }

        iinfo = info['imageinfo'][0]
        if 'url' in iinfo:
            res['original'] = iinfo['url']
        if 'thumburl' in iinfo:
            res['thumbnail'] = iinfo['thumburl']
        return res

    def search_file(self, pattern):
        data = self._common_file_request()
        data['generator'] = 'search'
        data['gsrnamespace'] = 6 # File: namespace
        data['gsrsearch'] = pattern

        while True:
            response = self.API_get(data)
            for fdict in response['query']['pages'].values():
                yield self._common_parse_file(fdict)

            if 'continue' in response:
                data.update(response['continue'])
            else:
                break

    def get_image(self, page):
        page = self.url2page(page)
        data = self._common_file_request()
        data['titles'] = page

        response = self.API_get(data)
        pageid = list(response['query']['pages'].keys())[0]
        info = response['query']['pages'][pageid]
        return self._common_parse_file(info)

    def search_categories(self, pattern):
        request = {
            'action': 'query',
            'prop': 'info|categoryinfo',
            'inprop': 'url',
        }

        request.update({
            'generator': 'search',
            'gsrnamespace': 14, # 'Category:' namespace
            'gsrsearch': pattern,
        })

        while True:
            response = self.API_get(request)
            for cdict in response['query']['pages'].values():
                if not cdict['categoryinfo'].get('files', 0):
                    continue
                yield {
                    'id': cdict['title'],
                    'title': cdict['title'],
                    'url': cdict['canonicalurl'],
                }

            if 'continue' in response:
                request.update(response['continue'])
            else:
                break

    def iter_images(self, category):
        request = self._common_file_request()
        request.update({
            'generator': 'categorymembers',
            'gcmtitle': category,
            'gcmtype': 'file',
        })

        while True:
            response = self.API_get(request)
            for fdict in response['query']['pages'].values():
                yield self._common_parse_file(fdict)

            if 'continue' in response:
                request.update(response['continue'])
            else:
                break

    def fill_file(self, obj, fields):
        response = self.open(obj.url)
        if 'data' in fields:
            obj.data = response.content
        if 'size' in fields:
            obj.size = len(response.content)
        if 'date' in fields:
            obj.date = dateutil.parser.parse(response.headers.get('Date'))

    def home(self):
        # We don't need to change location, we're using the JSON API here.
        pass

    def check_result(self, result):
        if 'error' in result:
            raise APIError(result['error']['info'])

    def API_get(self, data):
        """
        Submit a GET request to the website
        The JSON data is parsed and returned as a dictionary
        """
        data['format'] = 'json'
        result = self.open(self.apiurl, params=data).json()
        self.check_result(result)
        return result

    def API_post(self, data):
        """
        Submit a POST request to the website
        The JSON data is parsed and returned as a dictionary
        """
        data['format'] = 'json'
        result = self.open(self.apiurl, data=data).json()
        self.check_result(result)
        return result
