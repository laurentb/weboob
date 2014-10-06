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

from weboob.deprecated.browser import Page
from weboob.capabilities.radio import Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo


class LivePage(Page):
    def iter_radios_list(self):
        radio = Radio('nihon')
        radio.title = u'Nihon no Oto'
        radio.description = u'Nihon no Oto: le son du Japon'
        radio.streams = []

        index = -1

        for el in self.document.xpath('//source'):
            index += 1
            mime_type = unicode(el.attrib['type'])
            stream_url = unicode(el.attrib['src'])
            stream = BaseAudioStream(index)
            stream.bitrate = 128
            if (mime_type == u'audio/mpeg'):
                stream.format = u'mp3'
            elif (mime_type == u'audio/ogg'):
                stream.format = u'vorbis'
            stream.title = radio.title + ' ' + mime_type
            stream.url = stream_url
            radio.streams.append(stream)

        yield radio


class ProgramPage(Page):
    def get_current_emission(self):
        current = StreamInfo(0)
        two_or_more = unicode(self.document.xpath('//p')[0].text).split('/////')[0].split(' - ')
        # Consider that if String(' - ') appears it'll be in title rather in the artist name
        if len(two_or_more) > 2:
            current.who = two_or_more.pop(0)
            current.what = ' - '.join(two_or_more)
        else:
            current.who, current.what = two_or_more
        return current
