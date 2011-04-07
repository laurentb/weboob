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


__all__ = ['InitPage']


class InitPage(BasePage):
    def on_loaded(self):
        channels = []
        ### Parse liste des channels
        for elem in self.document[2].getchildren():
            channel = {}
            for e in elem.getchildren():
                subchannels = []
                if e.tag == "NOM":
                    channel['nom'] = e.text
                elif e.tag == "SELECTIONS":
                    for select in e:
                        subchannel = {}
                        subchannel['id'] = select[0].text
                        subchannel['nom'] = select[1].text
                        subchannels.append(subchannel)
            channel['subchannels'] = subchannels
            channels.append(channel)
