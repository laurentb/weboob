# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
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


import os
import logging
import errno
from subprocess import Popen, PIPE

from weboob.capabilities.video import ICapVideo
from weboob.tools.application.repl import ReplApplication


__all__ = ['Videoob']

class Player():
    """Black magic invoking a video player to this world.

    Presently, due to strong disturbances in the holidays of the ether
    world, the video player used is chosen from a static list of
    programs. See PLAYERS for more information.

    You MAY want to move it into a separate weboob.tools.applications
    module.
    """

    # A list of tuples: (player , play_from_stdin_cmd)
    # FIXME: lookup preference in freedesktop MIME database
    PLAYERS = [
        ('parole', 'parole fd://0'),
        ('totem', 'totem fd://0'),
        ('mplayer', 'mplayer -really-quiet -'),
        ('vlc', 'vlc -'),
        ('xine', 'xine stdin:/'),
    ]

    def __init__(self):
        self.player = None
        for (binary,cmd_stdin) in self.PLAYERS:
            if self._find_in_path(os.environ['PATH'], binary):
                self.player = binary
                self.player_stdin = cmd_stdin
                break
        if not self.player:
            raise OSError(errno.ENOENT, "video player not found")

    def play(self, video):
        """Play a video object, using programs from the PLAYERS list.

        This function dispatch calls to either _play_default or
        _play_rtmp for special rtmp streams using SWF verification.
        """
        if video.url.find('rtmp') == 0:
            self._play_rtmp(video)
        else:
            self._play_default(video)

    def _play_default(self, video):
        "Play video.url with the video player."
        cmd = self.player + " " + video.url
        args = cmd.split()

        print "invoking [%s]" % cmd
        os.spawnlp(os.P_NOWAIT, args[0], *args)

    def _play_rtmp(self, video):
        """"Download data with rtmpdump and pipe them to a video player.

        You need a working version of rtmpdump installed and the SWF
        object url in order to comply with SWF verification requests
        from the server. The last one is retrieved from the non-standard
        non-API compliant 'swf_player' attribute of the 'video' object.
        """

        if not self._find_in_path(os.environ['PATH'], 'rtmpdump'):
            raise OSError(errno.ENOENT, "\'rtmpdump\' binary not found")

        video_url = video.url
        try:
            player_url = video.swf_player
            rtmp = 'rtmpdump -r %s --swfVfy %s' % (video_url, player_url)

        except AttributeError:
            logging.warning("Your video object does not have a 'swf_player' "
                            "attribute. SWF verification will be disabled and "
                            "may prevent correct video playback.")

            rtmp = 'rtmpdump -r %s' % video_url

        rtmp += ' --quiet'

        print ':: Streaming from %s' % video_url
        print ':: to %s' % self.player_stdin
        p1 = Popen(rtmp.split(), stdout=PIPE)
        p2 = Popen(self.player_stdin.split(),
                   stdin=p1.stdout, stderr=PIPE)

    def _find_in_path(self,path, filename):
        for i in path.split(':'):
            if os.path.exists('/'.join([i, filename])):
                return True
        return False


class Videoob(ReplApplication):
    APPNAME = 'videoob'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz, Romain Bignon, John Obbele'
    CAPS = ICapVideo

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)

        try:
            self.player = Player()
        except OSError:
            self.player = None

        self.videos = []

    def add_application_options(self, group):
        group.add_option('--nsfw', action='store_true', help='enable non-suitable for work videos')

    def handle_application_options(self):
        if self.options.backends:
            self.options.nsfw = True

    def _get_video(self, _id):
        if self.interactive:
            try:
                video = self.videos[int(_id)]
            except (KeyError,ValueError):
                pass
            else:
                return video
        _id, backend_name = self.parse_id(_id)
        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends
        for backend, video in self.do('get_video', _id, backends=backend_names):
            return video

    def do_play(self, _id):
        """
        play ID

        Play a video with a found player.
        """
        if not _id:
            print 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return

        video = self._get_video(_id)
        if not video:
            print 'Video not found: ', _id
            return

        backend = self.weboob.get_backend(video.backend)
        backend.fillobj(video, ['url'])

        if self.player:
            self.player.play(video)
        else:
            print 'No player has been found on this system.'
            print 'The URL of this video is:'
            print '  %s' % video.url

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
            print 'Video not found: ', _id
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
                self.options.nsfw = True
            elif line == 'off':
                self.options.nsfw = False
            else:
                print 'Invalid argument "%s".' % line
        else:
            print "on" if self.options.nsfw else "off"

    def do_search(self, pattern=None):
        """
        search [PATTERN]

        Search for videos matching a PATTERN.

        If PATTERN is not given, this command will search for the latest videos.
        """
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest videos')
        self.videos = []
        for backend, video in self.do('iter_search_results', pattern=pattern, nsfw=self.options.nsfw,
                                      max_results=self.options.count):
            self.videos.append(video)
            self.format(video)
        self.flush()
