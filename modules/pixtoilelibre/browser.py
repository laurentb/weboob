# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
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
from weboob.tools.capabilities.paste import image_mime
from StringIO import StringIO

from .pages import PageHome, PageImage, PageError


__all__ = ['PixtoilelibreBrowser']


class PixtoilelibreBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'pix.toile-libre.org'
    ENCODING = None

    PAGES = {'%s://%s/' % (PROTOCOL, DOMAIN): PageHome,
             r'%s://%s/\?action=upload': PageError,
             r'%s://%s/\?img=(.+)' % (PROTOCOL, DOMAIN): PageImage}

    def post_image(self, filename, contents, private=False, description=''):
        self.location('/')
        assert self.is_on_page(PageHome)

        mime = image_mime(contents.encode('base64'))
        self.select_form(nr=0)
        self.form.find_control('private').items[0].selected = private
        self.form['description'] = description or ''
        self.form.find_control('img').add_file(StringIO(contents), filename=filename, content_type=mime)
        self.submit()

        assert self.is_on_page(PageImage)
        return self.page.get_info()

    def get_contents(self, id):
        return self.readurl('%s://%s/upload/original/%s' % (self.PROTOCOL, self.DOMAIN, id))
