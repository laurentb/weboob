# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


from weboob.tools.browser import BasePage

from weboob.capabilities.collection import Collection

__all__ = ['InitPage']


class InitPage(BasePage):
    def on_loaded(self):
        self.collections = []

        def do(_id):
            self.browser.location("http://service.canal-plus.com/video/rest/getMEAs/cplus/%s" % _id)
            return self.browser.page.iter_channel()

        # Parse the list of channels
        for elem in self.document[2].getchildren():
            children = []
            for e in elem.getchildren():
                if e.tag == "NOM":
                    _id = e.text.strip()
                elif e.tag == "SELECTIONS":
                    for select in e:
                        sub = Collection(_id=select[0].text,
                                title=select[1].text.strip(),
                                fct=do)
                        children.append(sub)
            coll = Collection(_id, children=children)
            self.collections.append(coll)
