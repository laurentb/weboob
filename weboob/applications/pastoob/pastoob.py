# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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

import os
import sys
import codecs
import locale
from random import choice

from weboob.capabilities.paste import ICapPaste, PasteNotFound
from weboob.tools.application.repl import ReplApplication


__all__ = ['Pastoob']


class Pastoob(ReplApplication):
    APPNAME = 'pastoob'
    VERSION = '0.e'
    COPYRIGHT = 'Copyright(C) 2011 Laurent Bachelier'
    DESCRIPTION = 'Console application allowing to post and get pastes from pastebins.'
    CAPS = ICapPaste

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def do_get(self, _id):
        """
        get ID

        Get a paste contents.
        """
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('get', short=True)
            return 2

        try:
            paste = self.get_object(_id, 'get_paste', ['contents'])
        except PasteNotFound:
            print >>sys.stderr, 'Paste not found: %s' %  _id
            return 3
        if not paste:
            print >>sys.stderr, 'Unable to handle paste: %s' %  _id
            return 1
        output = codecs.getwriter(sys.stdout.encoding or locale.getpreferredencoding())(sys.stdout)
        output.write(paste.contents)
        # add a newline unless we are writing
        # in a file or in a pipe
        if os.isatty(output.fileno()):
            output.write('\n')

    def do_post(self, filename):
        """
        post [FILENAME]

        Submit a new paste.
        The filename can be '-' for reading standard input (pipe).
        """
        if not filename or filename == '-':
            contents = self.acquire_input()
            if not len(contents):
                print >>sys.stderr, 'Empty paste, aborting.'
                return 1

        else:
            try:
                with codecs.open(filename, encoding=locale.getpreferredencoding()) as fp:
                    contents = fp.read()
            except IOError, e:
                print >>sys.stderr, 'Unable to open file "%s": %s' % (filename, e.strerror)
                return 1

        # get and sort the backends able to satisfy our requirements
        params = self._get_params()
        backends = {}
        for backend in self.weboob.iter_backends():
            score = backend.can_post(contents, **params)
            if score:
                backends.setdefault(score, []).append(backend)
        # select a random backend from the best scores
        if len(backends):
            backend = choice(backends[max(backends.keys())])
        else:
            print >>sys.stderr, 'No suitable backend found.'
            return 1

        p = backend.new_paste(_id=None)
        p.public = params.get('public')
        p.title = os.path.basename(filename)
        p.contents = contents
        backend.post_paste(p, max_age=params.get('max_age'))
        print 'Successfuly posted paste: %s' % p.page_url

    def _get_params(self):
        return {'public': True, 'max_age': 3600*24*3}
