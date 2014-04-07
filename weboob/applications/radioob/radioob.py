# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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

import subprocess
import sys
import os
import re
import requests

from weboob.capabilities.radio import ICapRadio, Radio
from weboob.capabilities.audio import ICapAudio, BaseAudio
from weboob.capabilities.base import empty
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.application.media_player import InvalidMediaPlayer, MediaPlayer, MediaPlayerNotFound
from weboob.tools.application.formatters.iformatter import PrettyFormatter

__all__ = ['Radioob']


class RadioListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'description')

    def get_title(self, obj):
        return obj.title

    def get_description(self, obj):
        result = '%-30s' % obj.description
        if hasattr(obj, 'current') and not empty(obj.current):
            if obj.current.who:
                result += ' (Current: %s - %s)' % (obj.current.who, obj.current.what)
            else:
                result += ' (Current: %s)' % obj.current.what
        return result


class Radioob(ReplApplication):
    APPNAME = 'radioob'
    VERSION = '0.i'
    COPYRIGHT = 'Copyright(C) 2010-2013 Romain Bignon\nCopyright(C) 2013 Pierre Maziere'
    DESCRIPTION = "Console application allowing to search for web radio stations, listen to them and get information " \
                  "like the current song."
    SHORT_DESCRIPTION = "search, show or listen to radio stations"
    CAPS = (ICapRadio, ICapAudio)
    EXTRA_FORMATTERS = {'radio_list': RadioListFormatter}
    COMMANDS_FORMATTERS = {'ls':     'radio_list',
                           'search': 'radio_list',
                           'playlist': 'radio_list',
                          }
    COLLECTION_OBJECTS = (Radio, BaseAudio, )
    PLAYLIST = []

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

        Download an audio file
        """
        _id, dest = self.parse_command_args(line, 2, 1)
        audio = self.get_object(_id, 'get_audio', ['url'])
        if not audio:
            print >>sys.stderr, 'Audio file not found: %s' % _id
            return 3

        if not audio.url:
            print >>sys.stderr, 'Error: the direct URL is not available.'
            return 4

        def check_exec(executable):
            with open('/dev/null', 'w') as devnull:
                process = subprocess.Popen(['which', executable], stdout=devnull)
                if process.wait() != 0:
                    print >>sys.stderr, 'Please install "%s"' % executable
                    return False
            return True

        def audio_to_file(_audio):
            ext = _audio.ext
            if not ext:
                ext = 'audiofile'
            return '%s.%s' % (re.sub('[?:/]', '-', _audio.id), ext)

        if dest is not None and os.path.isdir(dest):
            dest += '/%s' % audio_to_file(audio)

        if dest is None:
            dest = audio_to_file(audio)

        if audio.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                return 1
            args = ('rtmpdump', '-e', '-r', audio.url, '-o', dest)
        elif audio.url.startswith('mms'):
            if not check_exec('mimms'):
                return 1
            args = ('mimms', '-r', audio.url, dest)
        else:
            if check_exec('wget'):
                args = ('wget', '-c', audio.url, '-O', dest)
            elif check_exec('curl'):
                args = ('curl', '-C', '-', audio.url, '-o', dest)
            else:
                return 1

        os.spawnlp(os.P_WAIT, args[0], *args)

    def complete_play(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_play(self, line):
        """
        play ID [stream_id]

        Play a radio or a audio file with a found player (optionnaly specify the wanted stream).
        """
        _id, stream_id = self.parse_command_args(line, 2, 1)
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('play', short=True)
            return 2

        try:
            stream_id = int(stream_id)
        except (ValueError,TypeError):
            stream_id = 0

        radio = self.get_object(_id, 'get_radio')
        audio = self.get_object(_id, 'get_audio')

        if radio is None and audio is None:
            print >>sys.stderr, 'Radio or Audio file not found:', _id
            return 3

        if audio is None:
            try:
                stream = radio.streams[stream_id]
            except IndexError:
                print >>sys.stderr, 'Stream #%d not found' % stream_id
                return 1
        else:
            stream = audio

        try:
            player_name = self.config.get('media_player')
            media_player_args = self.config.get('media_player_args')
            if not player_name:
                self.logger.debug(u'You can set the media_player key to the player you prefer in the radioob '
                                  'configuration file.')

            r = requests.get(stream.url, stream=True)
            buf = r.iter_content(512).next()
            r.close()
            playlistFormat = None
            for line in buf.split("\n"):
                if playlistFormat is None:
                    if line == "[playlist]":
                        playlistFormat = "pls"
                    elif line == "#EXTM3U":
                        playlistFormat = "m3u"
                    else:
                        break
                elif playlistFormat == "pls":
                    if line.startswith('File'):
                        stream.url = line.split('=', 1).pop(1).strip()
                        break
                elif playlistFormat == "m3u":
                    if line[0] != "#":
                        stream.url = line.strip()
                        break

            self.player.play(stream, player_name=player_name, player_args=media_player_args)
        except (InvalidMediaPlayer, MediaPlayerNotFound) as e:
            print '%s\nRadio URL: %s' % (e, stream.url)

    def do_playlist(self, line):
        """
        playlist cmd [args]
        playlist add ID [ID2 ID3 ...]
        playlist remove ID [ID2 ID3 ...]
        playlist export [FILENAME]
        playlist display
        """

        if not line:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('playlist')
            return 2

        cmd, args = self.parse_command_args(line, 2, req_n=1)
        if cmd == "add":
            _ids = args.strip().split(' ')
            for _id in _ids:
                audio = self.get_object(_id, 'get_audio')

                if not audio:
                    print >>sys.stderr, 'Audio file not found: %s' % _id
                    return 3

                if not audio.url:
                    print >>sys.stderr, 'Error: the direct URL is not available.'
                    return 4

                self.PLAYLIST.append(audio)

        elif cmd == "remove":
            _ids = args.strip().split(' ')
            for _id in _ids:

                audio_to_remove = self.get_object(_id, 'get_audio')

                if not audio_to_remove:
                    print >>sys.stderr, 'Audio file not found: %s' % _id
                    return 3

                if not audio_to_remove.url:
                    print >>sys.stderr, 'Error: the direct URL is not available.'
                    return 4

                for audio in self.PLAYLIST:
                    if audio.id == audio_to_remove.id:
                        self.PLAYLIST.remove(audio)
                        break

        elif cmd == "export":
            filename = "playlist.m3u"
            if args:
                filename = args

            file = open(filename, 'w')
            for audio in self.PLAYLIST:
                file.write('%s\r\n' % audio.url)
            file.close()

        elif cmd == "display":
            for audio in self.PLAYLIST:
                self.cached_format(audio)

        else:
            print >>sys.stderr, 'Playlist command only support "add", "remove", "display" and "export" arguments.'
            return 2


    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        """
        info ID

        Get information about a radio or an audio file.
        """
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        radio = self.get_object(_id, 'get_radio')
        audio = self.get_object(_id, 'get_audio')
        if radio is None and audio is None:
            print >>sys.stderr, 'Radio or Audio file not found:', _id
            return 3

        if audio is None:
            self.format(radio)
        else:
            self.format(audio)

    @defaultcount(10)
    def do_search(self, pattern=None):
        """
        search PATTERN

        List radios matching a PATTERN.

        If PATTERN is not given, this command will list all the radios.
        """
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'All radios')
        self.change_path([u'search'])
        for backend, radio in self.do('iter_radios_search', pattern=pattern):
            self.add_object(radio)
            self.format(radio)
        for backend, audio in self.do('search_audio', pattern=pattern):
            self.add_object(audio)
            self.format(audio)


    def do_ls(self, line):
        """
        ls

        List radios
        """
        ret = super(Radioob, self).do_ls(line)
        return ret
