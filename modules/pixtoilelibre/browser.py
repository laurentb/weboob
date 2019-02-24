# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from base64 import b64encode
from io import BytesIO

from weboob.browser import PagesBrowser, URL
from weboob.tools.capabilities.paste import image_mime

from .pages import PageHome, PageImage, PageError


__all__ = ['PixtoilelibreBrowser']


class PixtoilelibreBrowser(PagesBrowser):
    BASEURL = 'http://pix.toile-libre.org'

    home = URL(r'/$', PageHome)
    error = URL(r'/\?action=upload', PageError)
    img = URL(r'/\?img=(?P<id>.+)', PageImage)

    def post_image(self, filename, contents, private=False, description=''):
        self.location('/')
        assert self.home.is_here()

        mime = image_mime(b64encode(contents))
        form = self.page.get_form(nr=0)
        form['private'] = int(private)
        form['description'] = description or ''
        del form['img']
        f = (filename, BytesIO(contents), mime)
        self.location(form.url, data=form, files={'img': f})

        assert self.img.is_here()
        return self.page.get_info()

    def get_contents(self, id):
        return self.open('/upload/original/%s' % id).content
