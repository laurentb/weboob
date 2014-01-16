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




import os
import sys
import codecs
import locale
import re
from random import choice

from weboob.capabilities.paste import ICapPaste, PasteNotFound
from weboob.tools.application.repl import ReplApplication


__all__ = ['Pastoob']


class Pastoob(ReplApplication):
    APPNAME = 'pastoob'
    VERSION = '0.i'
    COPYRIGHT = 'Copyright(C) 2011-2013 Laurent Bachelier'
    DESCRIPTION = "Console application allowing to post and get pastes from pastebins."
    SHORT_DESCRIPTION = "post and get pastes from pastebins"
    CAPS = ICapPaste

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def do_get(self, line):
        """
        get ID

        Get a paste contents.
        """
        return self._get_op(line, binary=False, command='get')

    def do_get_bin(self, line):
        """
        get_bin ID

        Get a paste contents.
        File will be downloaded from binary services.
        """
        return self._get_op(line, binary=True, command='get_bin')

    def _get_op(self, _id, binary, command='get'):
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help(command, short=True)
            return 2

        try:
            paste = self.get_object(_id, 'get_paste', ['contents'])
        except PasteNotFound:
            print >>sys.stderr, 'Paste not found: %s' % _id
            return 3
        if not paste:
            print >>sys.stderr, 'Unable to handle paste: %s' % _id
            return 1

        if binary:
            if self.interactive:
                if not self.ask('The console may become messed up. Are you sure you want to show a binary file on your terminal?', default=False):
                    print >>sys.stderr, 'Aborting.'
                    return 1
            output = sys.stdout
            output.write(paste.contents.decode('base64'))
        else:
            output = codecs.getwriter(sys.stdout.encoding or locale.getpreferredencoding())(sys.stdout)
            output.write(paste.contents)
            # add a newline unless we are writing
            # in a file or in a pipe
            if os.isatty(output.fileno()):
                output.write('\n')

    def do_post(self, line):
        """
        post [FILENAME]

        Submit a new paste.
        The filename can be '-' for reading standard input (pipe).
        If 'bin' is passed, file will be uploaded to binary services.
        """
        return self._post(line, binary=False)

    def do_post_bin(self, line):
        """
        post_bin [FILENAME]

        Submit a new paste.
        The filename can be '-' for reading standard input (pipe).
        File will be uploaded to binary services.
        """
        return self._post(line, binary=True)

    def _post(self, filename, binary):
        use_stdin = (not filename or filename == '-')
        if use_stdin:
            if binary:
                contents = sys.stdin.read()
            else:
                contents = self.acquire_input()
            if not len(contents):
                print >>sys.stderr, 'Empty paste, aborting.'
                return 1

        else:
            try:
                if binary:
                    m = open(filename)
                else:
                    m = codecs.open(filename, encoding=locale.getpreferredencoding())
                with m as fp:
                    contents = fp.read()
            except IOError as e:
                print >>sys.stderr, 'Unable to open file "%s": %s' % (filename, e.strerror)
                return 1

        if binary:
            contents = contents.encode('base64')

        # get and sort the backends able to satisfy our requirements
        params = self.get_params()
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
        p.public = params['public']
        if self.options.title is not None:
            p.title = self.options.title
        else:
            p.title = os.path.basename(filename)
        p.contents = contents
        backend.post_paste(p, max_age=params['max_age'])
        print 'Successfuly posted paste: %s' % p.page_url

    def get_params(self):
        return {'public': self.options.public,
                'max_age': self.str_to_duration(self.options.max_age),
                'title': self.options.title}

    def str_to_duration(self, s):
        if s.strip().lower() == 'never':
            return False

        parts = re.findall(r'(\d*(?:\.\d+)?)\s*([A-z]+)', s)
        argsmap = {'Y|y|year|years|yr|yrs': 365.25 * 24 * 3600,
                   'M|o|month|months': 30.5 * 24 * 3600,
                   'W|w|week|weeks': 7 * 24 * 3600,
                   'D|d|day|days': 24 * 3600,
                   'H|h|hours|hour|hr|hrs': 3600,
                   'm|i|minute|minutes|min|mins': 60,
                   'S|s|second|seconds|sec|secs': 1}

        seconds = 0
        for number, unit in parts:
            for rx, secs in argsmap.iteritems():
                if re.match('^(%s)$' % rx, unit):
                    seconds += float(number) * float(secs)

        return int(seconds)

    def add_application_options(self, group):
        group.add_option('-p', '--public',  action='store_true',
                         help='Make paste public.')
        group.add_option('-t', '--title', action='store',
                         help='Paste title',
                         type='string')
        group.add_option('-m', '--max-age', action='store',
                         help='Maximum age (duration), default "1 month", "never" for infinite',
                         type='string', default='1 month')
