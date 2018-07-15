# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from datetime import datetime
import re

from weboob.tools.json import json
from weboob.browser.browsers import APIBrowser
from weboob.browser.filters.standard import CleanText
from weboob.capabilities.gallery import BaseImage
from weboob.capabilities.image import Thumbnail


class TumblrBrowser(APIBrowser):
    def __init__(self, baseurl, *args, **kwargs):
        super(TumblrBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl

    def consent(self):
        response = self.open(self.BASEURL)
        html = response.text
        # I hope their Macbooks catch fire for making it that painful
        token = re.search(r'name="tumblr-form-key".*?content="([^"]*)"', html).group(1)

        data = {
            "eu_resident": False, # i don't want to live on this planet anymore
            "gdpr_is_acceptable_age": True,
            "gdpr_consent_core": True,
            "gdpr_consent_first_party_ads": True,
            "gdpr_consent_third_party_ads": True,
            "gdpr_consent_search_history": True,
            "redirect_to": self.BASEURL,
        }
        headers = {
            'X-tumblr-form-key': token,
            'Referer': response.url,
        }
        super(TumblrBrowser, self).request('https://www.tumblr.com/svc/privacy/consent', data=data, headers=headers)

    def request(self, *args, **kwargs):
        def perform():
            # JSONP
            r = super(TumblrBrowser, self).open(*args, **kwargs).text
            r = re.sub(r'^var tumblr_api_read = (.*);$', r'\1', r)
            return json.loads(r)

        try:
            return perform()
        except ValueError:
            self.consent()
            return perform()

    def get_title_icon(self):
        r = self.request('/api/read/json?type=photo&num=1&start=0&filter=text')
        icon = None
        if r['posts']:
            icon = r['posts'][0]['tumblelog']['avatar_url_512']
        return (r['tumblelog']['title'], icon)

    def iter_images(self, gallery):
        index = 0
        offset = 0
        step = 50

        while True:
            r = self.request('/api/read/json?type=photo&filter=text', params={'start': offset, 'num': step})
            for post in r['posts']:
                # main photo only if single
                if not post['photos']:
                    img = BaseImage(
                        index=index,
                        gallery=gallery,
                        url=post['photo-url-1280'],
                        thumbnail=Thumbnail(post['photo-url-250']),
                    )
                    img.id = post['id']
                    index += 1
                    img.title = CleanText().filter(post['photo-caption'])
                    img.date = datetime.strptime(post['date-gmt'], '%Y-%m-%d %H:%M:%S %Z')
                    img._page_url = post["url"]
                    yield img

                # if multiple
                for photo in post['photos']:
                    img = BaseImage(
                        index=index,
                        gallery=gallery,
                        url=photo['photo-url-1280'],
                        thumbnail=Thumbnail(photo['photo-url-250']),
                    )
                    img.id = '%s.%s' % (post['id'], photo['offset'])
                    index += 1
                    img.title = CleanText().filter(photo['caption'] or post['photo-caption'])
                    img.date = datetime.strptime(post['date-gmt'], '%Y-%m-%d %H:%M:%S %Z')
                    img._page_url = post["url"]
                    yield img

            offset += step
            if not r['posts'] or offset >= r['posts-total']:
                break
