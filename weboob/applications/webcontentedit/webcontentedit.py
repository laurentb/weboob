# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


# python2.5 compatibility
from __future__ import with_statement

import os
import sys
import tempfile

from weboob.core.bcall import CallErrors
from weboob.capabilities.content import ICapContent
from weboob.tools.application.repl import ReplApplication


__all__ = ['WebContentEdit']


class WebContentEdit(ReplApplication):
    APPNAME = 'webcontentedit'
    VERSION = '0.e'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to display and edit contents on various websites.'
    CAPS = ICapContent

    def do_edit(self, line):
        """
        edit ID [ID...]

        Edit a content with $EDITOR, then push it on the website.
        """
        contents = []
        for id in line.split():
            _id, backend_name = self.parse_id(id, unique_backend=True)
            backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

            contents += [content for backend, content in self.do('get_content', _id, backends=backend_names) if content]

        if len(contents) == 0:
            print >>sys.stderr, 'No contents found'
            return 3

        paths = {}
        for content in contents:
            tmpdir = os.path.join(tempfile.gettempdir(), "weboob")
            if not os.path.isdir(tmpdir):
                os.makedirs(tmpdir)
            fd, path = tempfile.mkstemp(prefix='%s_' % content.id.replace(os.path.sep, '_'), dir=tmpdir)
            with os.fdopen(fd, 'w') as f:
                data = content.content
                if isinstance(data, unicode):
                    data = data.encode('utf-8')
                elif data is None:
                    content.content = u''
                    data = ''
                f.write(data)
            paths[path.encode('utf-8')] = content

        params = ''
        editor = os.environ.get('EDITOR', 'vim')
        if editor == 'vim':
            params = '-p'
        os.system("%s %s %s" % (editor, params, ' '.join(['"%s"' % path.replace('"', '\\"') for path in paths.iterkeys()])))

        for path, content in paths.iteritems():
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
            print >>sys.stderr, 'No changes. Abort.'
            return 1

        print 'Contents changed:\n%s' % ('\n'.join(' * %s' % content.id for content in contents))

        message = self.ask('Enter a commit message', default='')
        minor = self.ask('Is this a minor edit?', default=False)
        if not self.ask('Do you want to push?', default=True):
            return

        errors = CallErrors([])
        for content in contents:
            path = [path for path, c in paths.iteritems() if c == content][0]
            sys.stdout.write('Pushing %s...' % content.id.encode('utf-8'))
            sys.stdout.flush()
            try:
                self.do('push_content', content, message, minor=minor, backends=[content.backend]).wait()
            except CallErrors, e:
                errors.errors += e.errors
                sys.stdout.write(' error (content saved in %s)\n' % path)
            else:
                sys.stdout.write(' done\n')
                os.unlink(path)

        if len(errors.errors) > 0:
            raise errors

    def do_log(self, line):
        """
        log ID

        Display log of a page
        """
        if not line:
            print >>sys.stderr, 'Error: please give a page ID'
            return 2

        _id, backend_name = self.parse_id(line)
        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

        _id = _id.encode('utf-8')

        self.start_format()
        for backend, revision in self.do('iter_revisions', _id, max_results=self.options.count, backends=backend_names):
            self.format(revision)
        self.flush()
