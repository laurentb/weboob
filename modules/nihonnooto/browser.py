# * -*- coding: utf-8 -*-

# Copyright(C) 2013  Thomas Lecavelier
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
from .pages import LivePage, ProgramPage

__all__ = ['NihonNoOtoBrowser']


class NihonNoOtoBrowser(Browser):
    DOMAIN = 'www.nihon-no-oto.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['desktop_firefox']
    PAGES = {
        'http://www\.nihon-no-oto\.com/': LivePage,
        'http://www\.nihon-no-oto\.com/app/playlist.php': ProgramPage,
    }

    def home(self):
        self.location('/')

        assert self.is_on_page(LivePage)

    def iter_radios_list(self):
        self.location('/')

        assert self.is_on_page(LivePage)
        return self.page.iter_radios_list()

    def get_current_emission(self):
        self.location('/app/playlist.php')
        assert self.is_on_page(ProgramPage)
        return self.page.get_current_emission()
