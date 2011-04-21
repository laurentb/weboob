# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


import sys

from weboob.capabilities.radio import ICapRadio
from weboob.capabilities.base import NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.media_player import InvalidMediaPlayer, MediaPlayer, MediaPlayerNotFound
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Radioob']


class RadioListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'description')

    count = 0

    def flush(self):
        self.count = 0
        pass

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s (%s)%s\n' % (ReplApplication.BOLD, self.count, item['title'], backend, ReplApplication.NC)
        else:
            result = u'%s* (%s) %s%s\n' % (ReplApplication.BOLD, item['id'], item['title'], ReplApplication.NC)
        result += '   %-30s' % item['description']
        if item['current'] is not NotLoaded:
            if item['current'].artist:
                result += ' (Current: %s - %s)' % (item['current'].artist, item['current'].title)
            else:
                result += ' (Current: %s)' % item['current'].title
        return result


class Radioob(ReplApplication):
    APPNAME = 'radioob'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to search for web radio stations, listen to them and get information ' \
                  'like the current song.'
    CAPS = ICapRadio
    EXTRA_FORMATTERS = {'radio_list': RadioListFormatter}
    COMMANDS_FORMATTERS = {'ls':     'radio_list',
                           'search': 'radio_list',
                          }

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)
        self.player = MediaPlayer(self.logger)

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def complete_play(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_play(self, _id):
        """
        play ID

        Play a radio with a found player.
        """
        if not _id:
            print 'This command takes an argument: %s' % self.get_command_help('play', short=True)
            return

        radio = self.get_object(_id, 'get_radio', ['streams'])
        if not radio:
            print >>sys.stderr, 'Radio not found: ' % _id
            return
        try:
            player_name = self.config.get('media_player')
            if not player_name:
                self.logger.debug(u'You can set the media_player key to the player you prefer in the radioob '
                                  'configuration file.')
            self.player.play(radio.streams[0], player_name=player_name)
        except (InvalidMediaPlayer, MediaPlayerNotFound), e:
            print '%s\nVideo URL: %s' % (e, radio.streams[0].url)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        """
        info ID

        Get information about a radio.
        """
        if not _id:
            print 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return

        radio = self.get_object(_id, 'get_radio')
        if not radio:
            print 'Radio not found:', _id
            return
        self.format(radio)
        self.flush()

    def do_search(self, pattern=None):
        """
        search PATTERN

        List radios matching a PATTERN.

        If PATTERN is not given, this command will list all the radios.
        """
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'All radios')
        self.change_path('/search')
        for backend, radio in self.do('iter_radios_search', pattern=pattern):
            self.add_object(radio)
            self.format(radio)
        self.flush()

