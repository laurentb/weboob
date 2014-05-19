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


import requests
import subprocess
import sys
import os

from weboob.capabilities.video import ICapVideo, BaseVideo
from weboob.capabilities.base import empty
from weboob.tools.application.repl import ReplApplication, defaultcount
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
    VERSION = '0.j'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz, Romain Bignon, John Obbele'
    DESCRIPTION = "Console application allowing to search for videos on various websites, " \
                  "play and download them and get information."
    SHORT_DESCRIPTION = "search and play videos"
    CAPS = ICapVideo
    EXTRA_FORMATTERS = {'video_list': VideoListFormatter}
    COMMANDS_FORMATTERS = {'search': 'video_list',
                           'ls': 'video_list',
                           'playlist': 'video_list'}
    COLLECTION_OBJECTS = (BaseVideo, )
    PLAYLIST = []
    nsfw = True

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)
        self.player = MediaPlayer(self.logger)

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def download(self, video, dest, default=None):
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

        dest = self.obj_to_filename(video, dest, default)

        if video.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                return 1
            args = ('rtmpdump', '-e', '-r', video.url, '-o', dest)
        elif video.url.startswith('mms'):
            if not check_exec('mimms'):
                return 1
            args = ('mimms', '-r', video.url, dest)
        elif u'm3u8' == video.ext:
            _dest, _ = os.path.splitext(dest)
            dest = u'%s.%s' % (_dest, 'mp4')
            args = ('wget',) + tuple(line for line in self.read_url(video.url) if not line.startswith('#')) + ('-O', dest)
        else:
            if check_exec('wget'):
                args = ('wget', '-c', video.url, '-O', dest)
            elif check_exec('curl'):
                args = ('curl', '-C', '-', video.url, '-o', dest)
            else:
                return 1

        os.spawnlp(os.P_WAIT, args[0], *args)

    def read_url(self, url):
        r = requests.get(url, stream=True)
        buf = r.iter_lines()
        r.close()
        return buf

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

        Braces-enclosed tags are replaced with data fields. Use the 'info'
        command to see what fields are available on a given video.

        Example: download KdRRge4XYIo@youtube '{title}.{ext}'
        """
        _id, dest = self.parse_command_args(line, 2, 1)
        video = self.get_object(_id, 'get_video', ['url'])
        if not video:
            print >>sys.stderr, 'Video not found: %s' % _id
            return 3

        return self.download(video, dest)

    def complete_play(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) >= 2:
            return self._complete_object()

    def do_play(self, line):
        """
        play ID

        Play a video with a found player.
        """
        if not line:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('play', short=True)
            return 2

        ret = 0
        for _id in line.split(' '):
            video = self.get_object(_id, 'get_video', ['url'])
            error = self.play(video, _id)
            if error is not None:
                ret = error

        return ret

    def play(self, video, _id):
        if not video:
            print >>sys.stderr, 'Video not found: %s' % _id
            return 3
        if not video.url:
            print >>sys.stderr, 'Error: the direct URL is not available.'
            return 4
        try:
            player_name = self.config.get('media_player')
            media_player_args = self.config.get('media_player_args')
            if not player_name:
                self.logger.info(u'You can set the media_player key to the player you prefer in the videoob '
                                 'configuration file.')
            self.player.play(video, player_name=player_name, player_args=media_player_args)
        except (InvalidMediaPlayer, MediaPlayerNotFound) as e:
            print '%s\nVideo URL: %s' % (e, video.url)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) >= 2:
            return self._complete_object()

    def do_info(self, line):
        """
        info ID [ID2 [...]]

        Get information about a video.
        """
        if not line:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        self.start_format()
        for _id in line.split(' '):
            video = self.get_object(_id, 'get_video')
            if not video:
                print >>sys.stderr, 'Video not found: %s' % _id
                return 3

            self.format(video)

    def complete_playlist(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return ['play', 'add', 'remove', 'export', 'display', 'download']
        if len(args) >= 3:
            if args[1] in ('export', 'download'):
                return self.path_completer(args[2])
            if args[1] in ('add', 'remove'):
                return self._complete_object()

    def do_playlist(self, line):
        """
        playlist cmd [args]

        playlist add ID [ID2 ID3 ...]
        playlist remove ID [ID2 ID3 ...]
        playlist export [FILENAME]
        playlist display
        playlist download [PATH]
        playlist play
        """

        if not self.interactive:
            print >>sys.stderr, 'This command can be used only in interactive mode.'
            return 1

        if not line:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('playlist')
            return 2

        cmd, args = self.parse_command_args(line, 2, req_n=1)
        if cmd == "add":
            _ids = args.strip().split(' ')
            for _id in _ids:
                video = self.get_object(_id, 'get_video')

                if not video:
                    print >>sys.stderr, 'Video not found: %s' % _id
                    return 3

                if not video.url:
                    print >>sys.stderr, 'Error: the direct URL is not available.'
                    return 4

                self.PLAYLIST.append(video)
        elif cmd == "remove":
            _ids = args.strip().split(' ')
            for _id in _ids:
                video_to_remove = self.get_object(_id, 'get_video')

                if not video_to_remove:
                    print >>sys.stderr, 'Video not found: %s' % _id
                    return 3

                if not video_to_remove.url:
                    print >>sys.stderr, 'Error: the direct URL is not available.'
                    return 4

                for video in self.PLAYLIST:
                    if video.id == video_to_remove.id:
                        self.PLAYLIST.remove(video)
                        break
        elif cmd == "export":
            filename = "playlist.m3u"
            if args:
                filename = args

            file = open(filename, 'w')
            for video in self.PLAYLIST:
                file.write('%s\r\n' % video.url)
            file.close()
        elif cmd == "display":
            for video in self.PLAYLIST:
                self.cached_format(video)
        elif cmd == "download":
            for i, video in enumerate(self.PLAYLIST):
                self.download(video, args, '%02d-{id}-{title}.{ext}' % (i+1))
        elif cmd == "play":
            for video in self.PLAYLIST:
                self.play(video, video.id)
        else:
            print >>sys.stderr, 'Playlist command only support "add", "remove", "display", "download" and "export" arguments.'
            return 2

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

    @defaultcount()
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
        for backend, video in self.do('search_videos', pattern=pattern, nsfw=self.nsfw):
            self.cached_format(video)
