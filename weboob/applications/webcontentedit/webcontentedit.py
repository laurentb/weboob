# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import tempfile
import codecs
from distutils.spawn import find_executable

from weboob.core.bcall import CallErrors
from weboob.capabilities.content import CapContent, Revision
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.compat import unicode


__all__ = ['WebContentEdit']


class WebContentEdit(ReplApplication):
    APPNAME = 'webcontentedit'
    VERSION = '2.0'
    COPYRIGHT = 'Copyright(C) 2010-YEAR Romain Bignon'
    DESCRIPTION = "Console application allowing to display and edit contents on various websites."
    SHORT_DESCRIPTION = "manage websites content"
    CAPS = CapContent

    def do_edit(self, line):
        """
        edit ID [ID...]

        Edit a content with $EDITOR, then push it on the website.
        """
        contents = []
        for id in line.split():
            _id, backend_name = self.parse_id(id, unique_backend=True)
            backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

            contents += [content for content in self.do('get_content', _id, backends=backend_names) if content]

        if len(contents) == 0:
            print('No contents found', file=self.stderr)
            return 3

        if self.stdin.isatty():
            paths = {}
            for content in contents:
                tmpdir = os.path.join(tempfile.gettempdir(), "weboob")
                if not os.path.isdir(tmpdir):
                    os.makedirs(tmpdir)
                with tempfile.NamedTemporaryFile(prefix='%s_' % content.id.replace(os.path.sep, '_'), dir=tmpdir, delete=False) as f:
                    data = content.content
                    if isinstance(data, unicode):
                        data = data.encode('utf-8')
                    elif data is None:
                        content.content = u''
                        data = ''
                    f.write(data)
                paths[f.name.encode('utf-8')] = content

            params = ''
            editor = os.environ.get('EDITOR', 'vim')
            # check cases where /usr/bin/vi is a symlink to vim
            if 'vim' in (os.path.basename(editor), os.path.basename(os.path.realpath(find_executable(editor) or '/')).replace('.nox', '')):
                params = '-p'
            os.system("%s %s %s" % (editor, params, ' '.join('"%s"' % path.replace('"', '\\"') for path in paths)))

            for path, content in paths.items():
                with open(path, 'r') as f:
                    data = f.read()
                    try:
                        data = data.decode('utf-8')
                    except UnicodeError:
                        pass
                if content.content != data:
                    content.content = data
                else:
                    contents.remove(content)

            if len(contents) == 0:
                print('No changes. Abort.', file=self.stderr)
                return 1

            print('Contents changed:\n%s' % ('\n'.join(' * %s' % content.id for content in contents)))

            message = self.ask('Enter a commit message', default='')
            minor = self.ask('Is this a minor edit?', default=False)
            if not self.ask('Do you want to push?', default=True):
                return

            errors = CallErrors([])
            for content in contents:
                path = [path for path, c in paths.items() if c == content][0]
                self.stdout.write('Pushing %s...' % content.id.encode('utf-8'))
                self.stdout.flush()
                try:
                    self.do('push_content', content, message, minor=minor, backends=[content.backend]).wait()
                except CallErrors as e:
                    errors.errors += e.errors
                    self.stdout.write(' error (content saved in %s)\n' % path)
                else:
                    self.stdout.write(' done\n')
                    os.unlink(path)
        else:
            # stdin is not a tty

            if len(contents) != 1:
                print("Multiple ids not supported with pipe", file=self.stderr)
                return 2

            message, minor = '', False
            data = self.stdin.read()
            contents[0].content = data.decode(self.guess_encoding(self.stdin))

            errors = CallErrors([])
            for content in contents:
                self.stdout.write('Pushing %s...' % content.id.encode(self.encoding))
                self.stdout.flush()
                try:
                    self.do('push_content', content, message, minor=minor, backends=[content.backend]).wait()
                except CallErrors as e:
                    errors.errors += e.errors
                    self.stdout.write(' error\n')
                else:
                    self.stdout.write(' done\n')

        if len(errors.errors) > 0:
            raise errors

    @defaultcount(10)
    def do_log(self, line):
        """
        log ID

        Display log of a page
        """
        if not line:
            print('Error: please give a page ID', file=self.stderr)
            return 2

        _id, backend_name = self.parse_id(line)
        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

        _id = _id.encode('utf-8')

        self.start_format()
        for revision in self.do('iter_revisions', _id, backends=backend_names):
            self.format(revision)

    def do_get(self, line):
        """
        get ID [-r revision]

        Get page contents
        """
        if not line:
            print('Error: please give a page ID', file=self.stderr)
            return 2

        _part_line = line.strip().split(' ')
        revision = None
        if '-r' in _part_line:
            r_index = _part_line.index('-r')
            if len(_part_line) -1 > r_index:
                revision = Revision(_part_line[r_index+1])
                _part_line.remove(revision.id)
            _part_line.remove('-r')

            if not _part_line:
                print('Error: please give a page ID', file=self.stderr)
                return 2

        _id, backend_name = self.parse_id(" ".join(_part_line))

        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

        _id = _id.encode('utf-8')

        output = codecs.getwriter(self.encoding)(self.stdout)
        for contents in [content for content in self.do('get_content', _id, revision, backends=backend_names) if content]:
            output.write(contents.content)

        # add a newline unless we are writing
        # in a file or in a pipe
        if output.isatty():
            output.write('\n')
