# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Christophe Benz, Romain Bignon, John Obbele
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

import subprocess
import sys
import os

from weboob.capabilities.video import ICapVideo
from weboob.capabilities.base import NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.media_player import InvalidMediaPlayer, MediaPlayer, MediaPlayerNotFound
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Videoob']


class VideoListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'duration', 'date')

    count = 0

    def flush(self):
        self.count = 0
        pass

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s (%s)%s\n' % (self.BOLD, self.count, item['title'], backend, self.NC)
        else:
            result = u'%s* (%s) %s%s\n' % (self.BOLD, item['id'], item['title'], self.NC)
        result += '            %s' % (item['duration'] if item['duration'] else item['date'])
        if item['author'] is not NotLoaded:
            result += ' - %s' % item['author']
        if item['rating'] is not NotLoaded:
            result += u' (%s/%s)' % (item['rating'], item['rating_max'])
        return result


class Videoob(ReplApplication):
    APPNAME = 'videoob'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz, Romain Bignon, John Obbele'
    DESCRIPTION = "Videoob is a console application to search videos on supported websites " \
                  "and to play them or get informations."
    CAPS = ICapVideo
    EXTRA_FORMATTERS = {'video_list': VideoListFormatter}
    COMMANDS_FORMATTERS = {'search': 'video_list'}

    nsfw = True
    videos = []

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)
        self.player = MediaPlayer(self.logger)

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def _get_video(self, _id, fields=None):
        if self.interactive:
            try:
                video = self.videos[int(_id) - 1]
            except (IndexError,ValueError):
                pass
            else:
                for backend, video in self.do('fillobj', video, fields, backends=[video.backend]):
                    if video:
                        return video
        _id, backend_name = self.parse_id(_id)
        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends
        for backend, video in self.do('get_video', _id, backends=backend_names):
            if video:
                return video

    def _complete_id(self):
        return ['%s@%s' % (video.id, video.backend) for video in self.videos]

    def complete_download(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_download(self, line):
        """
        download ID [FILENAME]

        Download a video
        """
        _id, dest = self.parse_command_args(line, 2, 1)
        video = self._get_video(_id, ['url'])
        if not video:
            print 'Video not found: %s' %  _id
            return 1

        with open('/dev/null', 'w') as devnull:
            process = subprocess.Popen(['which', 'wget'], stdout=devnull)
            if process.wait() != 0:
                print >>sys.stderr, 'Please install "wget"'
                return 1

        if dest is None:
            ext = video.ext
            if not ext:
                ext = 'avi'
            dest = '%s.%s' % (video.id, ext)

        os.system('wget "%s" -O "%s"' % (video.url, dest))

    def complete_play(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()

    def do_play(self, _id):
        """
        play ID

        Play a video with a found player.
        """
        if not _id:
            print 'This command takes an argument: %s' % self.get_command_help('play', short=True)
            return

        video = self._get_video(_id, ['url'])
        if not video:
            print 'Video not found: %s' %  _id
            return
        try:
            player_name = self.config.get('media_player')
            if not player_name:
                self.logger.debug(u'You can set the media_player key to the player you prefer in the videoob '
                                  'configuration file.')
            self.player.play(video, player_name=player_name)
        except (InvalidMediaPlayer, MediaPlayerNotFound), e:
            print '%s\nVideo URL: %s' % (e, video.url)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()

    def do_info(self, _id):
        """
        info ID

        Get information about a video.
        """
        if not _id:
            print 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return

        video = self._get_video(_id)
        if not video:
            print >>sys.stderr, 'Video not found: %s' %  _id
            return
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
        else:
            print "on" if self.nsfw else "off"

    def do_search(self, pattern=None):
        """
        search [PATTERN]

        Search for videos matching a PATTERN.

        If PATTERN is not given, this command will search for the latest videos.
        """
        if len(self.enabled_backends) == 0:
            if self.interactive:
                print 'No backend loaded. Please use the "backends" command.'
            else:
                print 'No backend loaded.'
            return 1

        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest videos')
        self.videos = []
        for backend, video in self.do('iter_search_results', pattern=pattern, nsfw=self.nsfw,
                                      max_results=self.options.count):
            self.videos.append(video)
            self.format(video)
        self.flush()
