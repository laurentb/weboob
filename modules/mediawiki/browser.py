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

from urlparse import urlsplit, urljoin
import datetime
import re

from weboob.browser.browsers import DomainBrowser
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.content import Revision

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
                'intoken':          'edit',
                }
        if rev:
            data['rvstartid'] = rev

        result = self.API_get(data)
        pageid = result['query']['pages'].keys()[0]
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
                'prop':        'info',
                'titles':      page,
                'intoken':     _type,
                }
        result = self.API_get(data)
        pageid = result['query']['pages'].keys()[0]
        return result['query']['pages'][str(pageid)][_type + 'token']

    def set_wiki_source(self, content, message=None, minor=False):
        if len(self.username) > 0 and not self.is_logged():
            self.login()

        page = content.id
        token = self.get_token(page, 'edit')

        data = {'action':      'edit',
                'title':       page,
                'token':       token,
                'text':        content.content.encode('utf-8'),
                'summary':     message,
                }
        if minor:
            data['minor'] = 'true'

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
            pageid = str(result['query']['pages'].keys()[0])

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
                'prop':         'info|pageimages|imageinfo',
                'piprop':       'thumbnail|name|original',
                'inprop':       'url',
                'iiprop':       'extmetadata|size'
               }

    def _common_parse_file(self, info):
        res = {'canonicalurl': info['canonicalurl'],
               'title':        info['title'],
               'size':         info['imageinfo'][0]['size'],
              }
        if 'thumbnail' in info:
            res['original'] = info['thumbnail']['original']
            res['thumbnail'] = info['thumbnail']['source']
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

            if 'query-continue' in response:
                data.update(response['query-continue']['search'])
            else:
                break

    def get_image(self, page):
        page = self.url2page(page)
        data = self._common_file_request()
        data['titles'] = page

        response = self.API_get(data)
        pageid = response['query']['pages'].keys()[0]
        info = response['query']['pages'][pageid]
        return self._common_parse_file(info)

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
