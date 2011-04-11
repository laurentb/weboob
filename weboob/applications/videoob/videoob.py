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
from weboob.capabilities.base import NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.media_player import InvalidMediaPlayer, MediaPlayer, MediaPlayerNotFound
from weboob.tools.application.formatters.iformatter import IFormatter

from weboob.capabilities.collection import Collection, ICapCollection, CollectionNotFound


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
    DESCRIPTION = 'Console application allowing to search for videos on various websites, ' \
                  'play and download them and get information.'
    CAPS = ICapVideo
    EXTRA_FORMATTERS = {'video_list': VideoListFormatter}
    COMMANDS_FORMATTERS = {'search': 'video_list', 'ls': 'video_list'}

    nsfw = True
    videos = []
    
    working_dir = []

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
        
        if video.url.find('rtmp') == 0:
            if check_exec('rtmpdump'):
                cmd = "rtmpdump -r " + video.url + " -o " + dest
            else:
                return 1
        else:
            if check_exec('wget'):
                cmd = 'wget "%s" -O "%s"' % (video.url, dest)
            else:
                return 1
        
        os.system(cmd)

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
    
    def do_ls(self, line):
        self.videos = []
        if len(self.working_dir) == 0:
            for name in [b.NAME for b in self.weboob.iter_backends(caps=ICapCollection)]:
                print name
            return 0
        
        def do(backend):
            return backend.iter_resources(self.working_dir[1:])
        
        for backend, rep in self.do(do, backends=self.working_dir[0]):
            if isinstance(rep, BaseVideo):
                self.videos.append(rep)
                self.format(rep)
            else:
                print rep

        self.flush()
    
    def do_cd(self, line):
        line = line.encode('utf-8')
        
        import urllib
        line = urllib.quote_plus(line)
        import posixpath
        path = posixpath.normpath(line)
        abspath =  posixpath.normpath(posixpath.join('/' + '/'.join(self.working_dir), path))
        final_parse = abspath.split('/')[1:]
        while len(final_parse) > 0 and final_parse[0] == u'': del final_parse[0]
        if len(final_parse) == 0:
            self.working_dir = []
            self.prompt = '%s> ' % self.APPNAME
            return 0
        
        final_parse = map(urllib.unquote_plus, final_parse)
        working_backend = final_parse[0]
        path = final_parse [1:]
        
        if working_backend in [b.NAME for b in self.enabled_backends]:
            if working_backend in [b.NAME for b in self.weboob.iter_backends(caps=ICapCollection)]:
                backend = [b for b in self.enabled_backends if b.NAME == working_backend][0]
            else:
                print >>sys.stderr, "Error backend %s not implement Collection" % working_backend
                return 1
        else:
            print >>sys.stderr, "Error backend %s unknow" % working_backend
            return 1
        
        
        if not path:
            self.working_dir = [working_backend,]
            backend.working_coll = []
            self.prompt = '%s:%s> ' % (self.APPNAME, '/' + '/'.join(self.working_dir))
            return 0
        try:
            path = backend.change_working_collection(path)
        except NotImplementedError:
            print >>sys.stderr, "Error backend %s not implement collection" % working_backend
            return 1
        except CollectionNotFound:
            print >>sys.stderr, "Path: %s not found" % ('/'+'/'.join(final_parse))
        
        escape = lambda s: s.replace('/', '%2F')
        path = map(escape, path)
        self.working_dir =  [working_backend,]+path
        self.prompt = '%s:%s> ' % (self.APPNAME, '/' + '/'.join(self.working_dir))
        
    def complete_cd(self, text, line, begidx, endidx):
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        
        if len(self.working_dir) == 0:
            tmp = [b.NAME for b in self.weboob.iter_backends(caps=ICapCollection)]
        else:
            backend = [b for b in self.enabled_backends if b.NAME == self.working_dir[0]][0]
            tmp = [rep for rep in backend.iter_resources(self.working_dir[1:])]
        
        return [s[offs:] for s in tmp if s.startswith(mline)]
