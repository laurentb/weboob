#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright(C) 2012 Alexandre Flament
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import subprocess
import requests
import os
import re

import ConfigParser

from weboob.core import Weboob
from weboob.capabilities.video import CapVideo

# hack to workaround bash redirection and encoding problem
import sys
import codecs
import locale

if sys.stdout.encoding is None:
    (lang, enc) = locale.getdefaultlocale()
    if enc is not None:
        (e, d, sr, sw) = codecs.lookup(enc)
        # sw will encode Unicode data to the locale-specific character set.
        sys.stdout = sw(sys.stdout)

# end of hack


def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)

rx = re.compile(u'[ \\/\\?\\:\\>\\<\\!\\\\\\*]+', re.UNICODE)


def removeSpecial(s):
    return rx.sub(u' ', u'%s' % s)

DOWNLOAD_DIRECTORY = ".files"


class Downloadboob(object):

    def __init__(self, backend_name, download_directory, links_directory):
        self.download_directory = download_directory
        self.links_directory = links_directory
        self.backend_name = backend_name
        self.backend = None
        self.weboob = Weboob()
        self.weboob.load_backends(modules=[self.backend_name])
        self.backend = self.weboob.get_backend(self.backend_name)

    def purge(self):
        if not os.path.isdir(self.links_directory):
            return
        dirList = os.listdir(self.links_directory)
        for local_link_name in dirList:
            link_name = self.links_directory + "/" + local_link_name
            if not self.check_link(link_name):
                print(u"Remove %s" % link_name)
                os.remove(link_name)
            else:
                print(u"Keep %s" % link_name)

    def check_link(self, link_name):
        if os.path.islink(link_name):
            file_name = os.readlink(link_name)
            absolute_file_name = os.path.join(self.links_directory, file_name)
            if os.path.isfile(absolute_file_name):
                return True
            return False
        else:
            return True

    def download(self, pattern=None, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None, title_exclude=[], id_regexp=None):
        print("For backend %s, search for '%s'" % (backend_name, pattern))

        # create directory for links
        if not os.path.isdir(self.links_directory):
            print("  create link to %s" % self.links_directory)
            os.makedirs(self.links_directory)

        # search for videos
        videos = []
        for i, video in enumerate(self.backend.search_videos(pattern, sortby, nsfw)):
            if i == max_results:
                break

            self.backend.fillobj(video, ('url', 'title', 'url', 'duration', 'ext'))
            if not self.is_downloaded(video):
                if not(self.is_excluded(video.title, title_exclude)) and self.id_regexp_matched(video.id, id_regexp):
                    print("  %s\n    Id:%s\n    Duration:%s" % (video.title, video.id, video.duration))
                    videos.append(video)
            else:
                print("Already downloaded, check %s" % video.id)
                linkname = self.get_linkname(video)
                if not os.path.exists(linkname):
                    self.remove_download(video)

        # download videos
        print("Downloading...")
        for video in videos:
            self.do_download(video)

    def is_excluded(self, title, title_exclude):
        for exclude in title_exclude:
            if title.find(exclude) > -1:
                return True
        return False

    def id_regexp_matched(self, video_id, id_regexp):
        if id_regexp:
            return re.search(id_regexp, video_id) is not None
        return True

    def get_downloaded_ext(self, video):
        ext = video.ext
        if not ext:
            ext = 'avi'
        elif ext == u'm3u8':
            ext = 'mp4'
        return ext

    def get_filename(self, video, relative=False):
        if relative:
            directory = os.path.join("..", DOWNLOAD_DIRECTORY, self.backend_name)
        else:
            directory = os.path.join(self.download_directory, self.backend_name)
            if not os.path.exists(directory):
                os.makedirs(directory)

        ext = self.get_downloaded_ext(video)

        return u"%s/%s.%s" % (directory, removeNonAscii(video.id), ext)

    def get_linkname(self, video):
        if not os.path.exists(self.links_directory):
            os.makedirs(self.links_directory)

        ext = self.get_downloaded_ext(video)

        misc = video.date
        if not misc:
            misc = video.id

        return u"%s/%s (%s).%s" % (self.links_directory, removeSpecial(video.title), removeSpecial(misc), ext)

    def is_downloaded(self, video):
        # check if the file is 0 byte
        return os.path.isfile(self.get_filename(video))

    def remove_download(self, video):
        path = self.get_filename(video)
        if os.stat(path).st_size == 0:
            # already empty
            return

        print('Remove video %s' % video.title)

        # Empty it to keep information we have already downloaded it.
        with open(path, 'w'):
            pass

    def set_linkname(self, video):
        linkname = self.get_linkname(video)
        idname = self.get_filename(video, relative=True)
        absolute_idname = self.get_filename(video, relative=False)
        if not os.path.islink(linkname) and os.path.isfile(absolute_idname):
            print("%s -> %s" % (linkname, idname))
            os.symlink(idname, linkname)

    def do_download(self, video):
        if not video:
            print('Video not found: %s' % video, file=sys.stderr)
            return 3

        if not video.url:
            print('Error: the direct URL is not available.', file=sys.stderr)
            return 4

        def check_exec(executable):
            with open(os.devnull, 'w') as devnull:
                process = subprocess.Popen(['which', executable], stdout=devnull)
                if process.wait() != 0:
                    print('Please install "%s"' % executable, file=sys.stderr)
                    return False
            return True

        dest = self.get_filename(video)

        if video.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                return 1
            args = ('rtmpdump', '-e', '-r', video.url, '-o', dest)
        elif video.url.startswith('mms'):
            if not check_exec('mimms'):
                return 1
            args = ('mimms', video.url, dest)
        elif u'm3u8' == video.ext:
            _dest, _ = os.path.splitext(dest)
            dest = u'%s.%s' % (_dest, 'mp4')
            content = tuple()
            baseurl = video.url.rpartition('/')[0]
            for line in self.read_url(video.url):
                if not line.startswith('#'):
                    if not line.startswith('http'):
                        line = u'%s/%s' % (baseurl, line)
                    content += (line,)
            args = ('wget', '-nv',) + content + ('-O', dest)
        else:
            if check_exec('wget'):
                args = ('wget', '-c', video.url, '-O', dest)
            elif check_exec('curl'):
                args = ('curl', '-C', '-', video.url, '-o', dest)
            else:
                return 1

        os.spawnlp(os.P_WAIT, args[0], *args)
        self.set_linkname(video)

    def read_url(self, url):
        r = requests.get(url, stream=True)
        return r.iter_lines()


config_file = 'downloadboob.conf'
sections = None
if len(sys.argv) >= 3:
    sections = sys.argv[2:]
if len(sys.argv) >= 2:
    config_file = sys.argv[1]

config = ConfigParser.ConfigParser()
config.read(['/etc/downloadboob.conf', os.path.expanduser('~/downloadboob.conf'), config_file])
if sections is None:
    sections = config.sections()

try:
    links_directory = os.path.expanduser(config.get('main', 'directory', '.'))
except ConfigParser.NoSectionError:
    print("Please create a documentation file (see the README file and the downloadboob.conf example file)")
    sys.exit(2)

links_directory = links_directory.decode('utf-8')

download_directory = os.path.join(links_directory, DOWNLOAD_DIRECTORY)

print("Downloading to %s" % (links_directory))

for section in config.sections():
    if section != "main" and section in sections:
        backend_name = config.get(section, "backend")
        pattern = config.get(section, "pattern")
        if config.has_option(section, "title_exclude"):
            title_exclude = config.get(section, "title_exclude").decode('utf-8').split('|')
        else:
            title_exclude = []
        if config.has_option(section, "id_regexp"):
            id_regexp = config.get(section, "id_regexp")
        else:
            id_regexp = None
        max_result = config.getint(section, "max_results")
        section_sublinks_directory = config.get(section, "directory")
        section_links_directory = os.path.join(links_directory, section_sublinks_directory)

        downloadboob = Downloadboob(backend_name, download_directory, section_links_directory)
        downloadboob.purge()
        # FIXME sortBy, title.match
        downloadboob.download(pattern, CapVideo.SEARCH_DATE, False, max_result, title_exclude, id_regexp)
