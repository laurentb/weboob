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


import logging

from weboob.capabilities.video import ICapVideo
from weboob.tools.application.repl import ReplApplication


__all__ = ['Videoob']


class Videoob(ReplApplication):
    APPNAME = 'videoob'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz, Romain Bignon, John Obbele'

    def load_default_backends(self):
        self.load_backends(caps=ICapVideo)

    def add_application_options(self, group):
        group.add_option('--nsfw', action='store_true', help='enable non-suitable for work videos')

    def handle_application_options(self):
        if self.options.backends:
            self.options.nsfw = True

    def do_info(self, _id):
        """
        info ID

        Get information about a video.
        """
        if not _id:
            logging.error(u'This command takes an argument: %s' % self.get_command_help('info', short=True))
            return
        _id, backend_name = self.parse_id(_id)
        names = (backend_name,) if backend_name is not None else None
        for backend, video in self.do('get_video', _id):
            if video is None:
                continue
            self.format(video)
    
    def do_search(self, pattern=None):
        """
        search [PATTERN]

        Search for videos matching a PATTERN.

        If PATTERN is not given, this command will search for the latest videos.
        """
        self.set_formatter_header(u'Search pattern: %s' % pattern if pattern else u'Latest videos')
        for backend, video in self.do('iter_search_results', pattern=pattern, nsfw=self.options.nsfw,
                                      max_results=self.options.count):
            self.format(video)
