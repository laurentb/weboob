# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon, John Obbele, Nicolas Duhamel
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

from __future__ import with_statement

import subprocess
import sys
import os

from weboob.capabilities.video import ICapVideo, BaseVideo
from weboob.capabilities.base import empty
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.media_player import InvalidMediaPlayer, MediaPlayer, MediaPlayerNotFound
from weboob.tools.application.formatters.iformatter import PrettyFormatter

__all__ = ['Videoob']


class VideoListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'duration', 'date')

    def get_title(self, obj):
        return obj.title

    def get_description(self, obj):
        if empty(obj.duration) and empty(obj.date):
            return None

        result = '%s' % (obj.duration or obj.date)
        if hasattr(obj, 'author') and not empty(obj.author):
            result += u' - %s' % obj.author
        if hasattr(obj, 'rating') and not empty(obj.rating):
            result += u' (%s/%s)' % (obj.rating, obj.rating_max)
        return result

class Videoob(ReplApplication):
    APPNAME = 'videoob'
    VERSION = '0.e'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz, Romain Bignon, John Obbele'
    DESCRIPTION = 'Console application allowing to search for videos on various websites, ' \
                  'play and download them and get information.'
    CAPS = ICapVideo
    EXTRA_FORMATTERS = {'video_list': VideoListFormatter}
    COMMANDS_FORMATTERS = {'search': 'video_list',
                           'ls': 'video_list'}
    COLLECTION_OBJECTS = (BaseVideo, )

    nsfw = True

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)
        self.player = MediaPlayer(self.logger)

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def complete_download(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_download(self, line):
        """
        download ID [FILENAME]

        Download a video
        """
        _id, dest = self.parse_command_args(line, 2, 1)
        video = self.get_object(_id, 'get_video', ['url'])
        if not video:
            print >>sys.stderr, 'Video not found: %s' % _id
            return 3

        if not video.url:
            print >>sys.stderr, 'Error: the direct URL is not available.'
            return 4

        def check_exec(executable):
            with open('/dev/null', 'w') as devnull:
                process = subprocess.Popen(['which', executable], stdout=devnull)
                if process.wait() != 0:
                    print >>sys.stderr, 'Please install "%s"' % executable
                    return False
            return True

        if dest is None:
            ext = video.ext
            if not ext:
                ext = 'avi'
            dest = '%s.%s' % (video.id, ext)

        if video.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                return 1
            args = ('rtmpdump', '-r', video.url, '-o', dest)
        elif video.url.startswith('mms'):
            if not check_exec('mimms'):
                return 1
            args = ('mimms', video.url, dest)
        else:
            if not check_exec('wget'):
                return 1
            args = ('wget', video.url, '-O', dest)

        os.spawnlp(os.P_WAIT, args[0], *args)

    def complete_play(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_play(self, _id):
        """
        play ID

        Play a video with a found player.
        """
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('play', short=True)
            return 2

        video = self.get_object(_id, 'get_video', ['url'])
        if not video:
            print >>sys.stderr, 'Video not found: %s' % _id
            return 3
        if not video.url:
            print >>sys.stderr, 'Error: the direct URL is not available.'
            return 4
        try:
            player_name = self.config.get('media_player')
            if not player_name:
                self.logger.info(u'You can set the media_player key to the player you prefer in the videoob '
                                  'configuration file.')
            self.player.play(video, player_name=player_name)
        except (InvalidMediaPlayer, MediaPlayerNotFound), e:
            print '%s\nVideo URL: %s' % (e, video.url)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        """
        info ID

        Get information about a video.
        """
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        video = self.get_object(_id, 'get_video')
        if not video:
            print >>sys.stderr, 'Video not found: %s' % _id
            return 3

        self.start_format()
        self.format(video)
        self.flush()

    def complete_nsfw(self, text, line, begidx, endidx):
        return ['on', 'off']

    def do_nsfw(self, line):
        """
        nsfw [on | off]

        If argument is given, enable or disable the non-suitable for work behavior.

        If no argument is given, print the current behavior.
        """
        line = line.strip()
        if line:
            if line == 'on':
                self.nsfw = True
            elif line == 'off':
                self.nsfw = False
            else:
                print 'Invalid argument "%s".' % line
                return 2
        else:
            print "on" if self.nsfw else "off"

    def do_search(self, pattern):
        """
        search PATTERN

        Search for videos matching a PATTERN.
        """
        if not pattern:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('search', short=True)
            return 2

        self.change_path([u'search'])
        self.start_format(pattern=pattern)
        for backend, video in self.do('search_videos', pattern=pattern, nsfw=self.nsfw,
                                      max_results=self.options.count):
            self.cached_format(video)
        self.flush()
