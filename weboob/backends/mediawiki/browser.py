# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from urlparse import urlsplit
import urllib
import lxml.html

from weboob.tools.browser import BaseBrowser

try:
    import simplejson
except ImportError:
    # Python 2.6+ has a module similar to simplejson
    import json as simplejson

__all__ = ['MediawikiBrowser']


# Browser
class MediawikiBrowser(BaseBrowser):
    ENCODING = 'utf-8'
    
    def __init__(self, url, apiurl, *args, **kwargs):
        url_parsed = urlsplit(url)
        self.PROTOCOL = url_parsed.scheme
        self.DOMAIN = url_parsed.netloc
        self.BASEPATH = url_parsed.path
        if self.BASEPATH.endswith('/'):
            self.BASEPATH = self.BASEPATH[:-1]
            
        prefix = '%s://%s%s' % (self.PROTOCOL, self.DOMAIN, self.BASEPATH)
        self.apiurl = apiurl

        BaseBrowser.__init__(self, *args, **kwargs)

    def get_wiki_source(self, page):
        assert isinstance(self.apiurl, basestring)
        
        data = {'action':           'query',
                'prop':             'revisions|info',
                'titles':           page,
                'rvprop':           'content|timestamp',
                'rvlimit':          '1',
                'intoken':          'edit',
                }


        
        result = self.API_get(data)
        pageid = result['query']['pages'].keys()[0]
        if pageid == "-1":
            return None
        return result['query']['pages'][str(pageid)]['revisions'][0]['*']

    def get_token(self, page, _type):
        if not self.is_logged():
            self.login()

        data = {'action':      'query',
                'prop':        'info',
                'titles':      page,
                'intoken':     _type,
                }
        result = self.API_get(data)
        pageid = result['query']['pages'].keys()[0]
        if pageid == "-1":
            return None
        return result['query']['pages'][str(pageid)][_type+'token']

    
    def set_wiki_source(self, content, message=None, minor=False):
        if not self.is_logged():
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

        result = self.API_post(data)
        print result

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
            raise BrowserIncorrectPassword
        
        if result['login']['result'] == 'NeedToken':
            data['lgtoken'] = result['login']['token']
            result2 = self.API_post(data)

    def home(self):
        '''We don't need to change location, we're using the JSON API here.'''
        pass

    def API_get(self, data):
        '''Submit a GET request to the website
        The JSON data is parsed and returned as a dictionary'''
        data['format'] = 'json'
        return simplejson.load(self.openurl(self.buildurl(self.apiurl, **data)), 'utf-8')

    def API_post(self, data):
        '''Submit a POST request to the website
        The JSON data is parsed and returned as a dictionary'''

        data['format'] = 'json'
        return simplejson.load(self.openurl(self.apiurl, urllib.urlencode(data)), 'utf-8')
