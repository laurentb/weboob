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


import errno
import logging
import os
from subprocess import Popen, PIPE


__all__ = ['VideoPlayer']


class VideoPlayer():
    """
    Black magic invoking a video player to this world.

    Presently, due to strong disturbances in the holidays of the ether
    world, the video player used is chosen from a static list of
    programs. See PLAYERS for more information.
    """

    PLAYERS = [
        ('parole', 'fd://0'),
        ('totem', 'fd://0'),
        ('mplayer', '-really-quiet -'),
        ('vlc', '-'),
        ('xine', 'stdin:/'),
    ]

    def get_player_name(self, preferred=None):
        player_names = preferred if preferred else [player[0] for player in self.PLAYERS]
        for player_name in player_names:
            if self._find_in_path(os.environ['PATH'], player_name):
                return player_name

    def play(self, video):
        """
        Play a video object, using programs from the PLAYERS list.

        This function dispatch calls to either _play_default or
        _play_rtmp for special rtmp streams using SWF verification.
        """
        if video.url.find('rtmp') == 0:
            self._play_rtmp(video)
        else:
            self._play_default(video)

    def _play_default(self, video):
        """
        Play video.url with the video player.
        """
        player_name = self.get_player_name()
        print 'Invoking "%s %s".' % (player_name, video.url)
        os.spawnlp(os.P_NOWAIT, player_name, player_name, video.url)

    def _play_rtmp(self, video):
        """
        Download data with rtmpdump and pipe them to a video player.

        You need a working version of rtmpdump installed and the SWF
        object url in order to comply with SWF verification requests
        from the server. The last one is retrieved from the non-standard
        non-API compliant 'swf_player' attribute of the 'video' object.
        """

        if not self._find_in_path(os.environ['PATH'], 'rtmpdump'):
            raise OSError(errno.ENOENT, '"rtmpdump" binary not found')

        video_url = video.url
        try:
            player_url = video.swf_player
            rtmp = 'rtmpdump -r %s --swfVfy %s' % (video_url, player_url)

        except AttributeError:
            logging.warning('Your video object does not have a "swf_player" attribute. SWF verification will be '
                            'disabled and may prevent correct video playback.')

            rtmp = 'rtmpdump -r %s' % video_url

        rtmp += ' --quiet'

        player_name = self.get_player_name()
        args = None
        for (binary, stdin_args) in self.PLAYERS:
            if binary == player_name:
                args = stdin_args
        assert args is not None

        print ':: Streaming from %s' % video_url
        print ':: to %s %s' % (player_name, args)
        p1 = Popen(rtmp.split(), stdout=PIPE)
        p2 = Popen([player_name, args], stdin=p1.stdout, stderr=PIPE)

    def _find_in_path(self,path, filename):
        for i in path.split(':'):
            if os.path.exists('/'.join([i, filename])):
                return True
        return False
