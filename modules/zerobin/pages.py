# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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

from base64 import b64decode, b64encode
from datetime import datetime
from zlib import decompress, MAX_WBITS, compressobj, DEFLATED

from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText
from weboob.tools.json import json
from weboob.tools.compat import urljoin

from .crypto import decrypt, encrypt


class ReadPageZero(HTMLPage):
    # for zerobin
    def decode_paste(self, key):
        d = json.loads(CleanText('//div[@id="cipherdata"]')(self.doc))
        subd = json.loads(d[0]['data'])
        decr = decrypt(key, subd)
        return decompress(b64decode(decr), -MAX_WBITS)

    def get_expire(self):
        d = json.loads(CleanText('//div[@id="cipherdata"]')(self.doc))[0]['meta']
        if 'expire_date' in d:
            return datetime.fromtimestamp(d['expire_date'])

    def has_paste(self):
        return bool(CleanText('//div[@id="cipherdata"]')(self.doc))


def fix_base64(s):
    pad = {
        2: '==',
        3: '=',
    }
    return s + pad.get(len(s) % 4, '')


class ReadPage0(HTMLPage):
    # for 0bin
    def decode_paste(self, key):
        d = json.loads(CleanText('//pre[@id="paste-content"]')(self.doc))
        for k in ('iv', 'ct', 'salt'):
            d[k] = fix_base64(d[k])
        decr = decrypt(key, d)
        # 0bin is supposed to use LZW but their js impl is such a piece of crap it doesn't compress anything
        # this is easier for us though hehe
        return b64decode(decr).decode('utf-8')

    def has_paste(self):
        return len(self.doc.xpath('//pre[@id="paste-content"]'))


class WritePageZero(HTMLPage):
    AGES = {
        300: '5min',
        600: '10min',
        3600: '1hour',
        86400: '1day',
        7 * 86400: '1week',
        30 * 86400: '1month',
        30.5 * 86400: '1month', # pastoob's definition of "1 month" is approximately okay
        365 * 86400: '1year',
        None: 'never',
        0: 0,
    }

    def is_here(self):
        return 'zerobin' in self.text and self.doc.xpath('//select[@id="pasteExpiration"]')

    def post(self, contents, max_age):
        compressor = compressobj(-1, DEFLATED, -MAX_WBITS)
        contents = compressor.compress(contents.encode('utf-8'))
        contents += compressor.flush()

        password, d = encrypt(b64encode(contents))
        data = {
            'data': json.dumps(d),
            'expire': self.AGES[max_age],
            'burnafterreading': str(int(max_age is 0)),
            'opendiscussion': str(int(self.browser.opendiscussion)),
            'syntaxcoloring': '1',
        }
        response = self.browser.location(self.url, data=data)
        j = response.json()

        assert j['status'] == 0
        return '%s?%s#%s' % (self.url, j['id'], password)


class WritePage0(HTMLPage):
    AGES = {
        86400: '1_day',
        30 * 86400: '1_month',
        30.5 * 86400: '1_month', # pastoob's definition of "1 month" is approximately okay
        None: 'never',
        0: 'burn_after_reading',
    }

    is_here = '//form[contains(@action,"paste/create")]'

    def post(self, contents, max_age):
        form = self.get_form(xpath='//form[@class="well"]')

        password, d = encrypt(b64encode(contents.encode('utf-8')))
        form['content'] = json.dumps(d)
        form['expiration'] = self.AGES[max_age]
        j = form.submit().json()

        assert j['status'] == 'ok'
        return urljoin(urljoin(self.url, form.url), '%s#%s' % (j['paste'], password))
