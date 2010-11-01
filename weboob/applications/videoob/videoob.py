# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon, John Obbele
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


from weboob.capabilities.video import ICapVideo
from weboob.capabilities.base import NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.media_player import MediaPlayer
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Videoob']


class VideoListFormatter(IFormatter):
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
        result += '            %s' % item['duration']
        if item['author'] is not NotLoaded:
            result += ' - %s' % item['author']
        if item['rating'] is not NotLoaded:
            result += u' (%s/%s)' % (item['rating'], item['rating_max'])
        return result

class Videoob(ReplApplication):
    APPNAME = 'videoob'
    VERSION = '0.4'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz, Romain Bignon, John Obbele'
    CAPS = ICapVideo
    EXTRA_FORMATTERS = {'video_list': VideoListFormatter}
    COMMANDS_FORMATTERS = {'search':    'video_list'}

    nsfw = True
    videos = []

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)
        try:
            self.player = MediaPlayer()
        except OSError:
            self.player = None

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
            print 'Video not found: ', _id
            return

        if self.player:
            self.player.play(video)
        else:
            print 'No player has been found on this system.'
            print 'The URL of this video is:'
            print '  %s' % video.url

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
            print 'Video not found:', _id
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
