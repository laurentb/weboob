# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.tools.json import json as simplejson

from .calendar import SensCritiquenCalendarEvent
from .pages import ProgramPage, EventPage

import urllib
import urllib2

__all__ = ['SenscritiqueBrowser']


class SenscritiqueBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.senscritique.com'
    ENCODING = 'utf-8'

    PAGES = {
        '%s://%s/sc/tv_guides' % (PROTOCOL, DOMAIN): ProgramPage,
        '%s://%s/film/(.*?)' % (PROTOCOL, DOMAIN): EventPage,
    }

    LIMIT = 25  # number of results returned for each ajax call (defined in the website).

    LIMIT_NB_PAGES = 10 #  arbitrary limit to avoid infinitive loop that can occurs if total number of films is a multiple of LIMIT (in website it causes an infinite scroll)

    HEADER_AJAX = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows "
                   "NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"
                   " GTB7.1 (.NET CLR 3.5.30729)",
                   "Accept": "gzip, deflate",
                   "X-Requested-With": "XMLHttpRequest",
                   "Referer": "http://www.senscritique.com/sc/tv_guides",
                   }

    HEADER_RESUME = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows "
                     "NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"
                     " GTB7.1 (.NET CLR 3.5.30729)",
                     "Accept": "application/json, text/javascript, */*; q=0.01",
                     "X-Requested-With": "XMLHttpRequest",
                     }

    DATA = {'order': 'chrono',
            'without_product_done': '0',
            'period': 'cette-semaine',
            'limit': '%d' % LIMIT,
            }

    URL = "http://www.senscritique.com/sc/tv_guides/gridContent.ajax"

    def home(self):
        self.location("http://www.senscritique.com/sc/tv_guides")
        assert self.is_on_page(ProgramPage)

    def list_events(self, date_from, date_to=None, package=None, channels=None):
        self.home()
        page = 1

        if package and channels:
            self.set_package_settings(package, channels)

        while True:
            self.DATA['page'] = '%d' % page
            self.page.document = self.get_ajax_content()
            nb_events = self.page.count_events()
            events = self.page.list_events(date_from, date_to)

            for event in events:
                yield event

            if nb_events < self.LIMIT or page >= self.LIMIT_NB_PAGES:
                break

            page += 1

    def set_package_settings(self, package, channels):
        url = 'http://www.senscritique.com/sc/tv_guides/saveSettings.json'
        params = "network=%s" % package
        params += ''.join(["&channels%%5B%%5D=%d" % (channel) for channel in channels])
        self.openurl(url, params)

    def get_ajax_content(self):
        req = urllib2.Request(self.URL, urllib.urlencode(self.DATA), headers=self.HEADER_AJAX)
        response = self.open(req)
        return self.get_document(response)

    def get_event(self, _id, event=None):
        if not event:
            self.home()
            page = 1

            while True:
                self.DATA['page'] = '%d' % page
                self.page.document = self.get_ajax_content()
                event = self.page.find_event(_id)
                nb_events = self.page.count_events()
                if event or nb_events < self.LIMIT or page >= self.LIMIT_NB_PAGES:
                    break

                page += 1

        if event:
            url = SensCritiquenCalendarEvent.id2url(_id)
            self.location(url)
            assert self.is_on_page(EventPage)
            return self.page.get_event(url, event)

    def get_resume(self, url, _id):
        self.HEADER_RESUME['Referer'] = url
        req = urllib2.Request('http://www.senscritique.com/sc/products/storyline/%s.json' % _id,
                              headers=self.HEADER_RESUME)
        response = self.open(req)
        result = simplejson.loads(response.read(), self.ENCODING)
        if result['json']['success']:
            return result['json']['data']
