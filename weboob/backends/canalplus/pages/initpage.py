# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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


from weboob.tools.browser import BasePage

from weboob.capabilities.collection import Collection

__all__ = ['InitPage']


class InitPage(BasePage):
    
    def on_loaded(self):
        self.collections = []
        
        def do(id):
            self.browser.location("http://service.canal-plus.com/video/rest/getMEAs/cplus/" + id)
            return self.browser.page.iter_channel()

        ### Parse liste des channels
        for elem in self.document[2].getchildren():
            coll = Collection()
            for e in elem.getchildren():
                if e.tag == "NOM":
                    coll.title = e.text.strip().encode('utf-8')
                elif e.tag == "SELECTIONS":
                    for select in e:
                        sub = Collection(title=select[1].text.strip().encode('utf-8'))
                        sub.id = select[0].text
                        sub.children = do
                        coll.appendchild(sub)
            self.collections.append(coll)
