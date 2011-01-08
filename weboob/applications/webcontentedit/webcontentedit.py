# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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
    VERSION = '0.6'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    DESCRIPTION = "Webcontentedit is a console application to display and " \
                  "edit contents on supported websites."
    CAPS = ICapContent

    def do_edit(self, line):
        """
        edit ID

        Edit a content with $EDITOR, then push it on the website.
        """
        contents = []
        for id in line.split():
            _id, backend_name = self.parse_id(id)
            backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

            contents += [content for backend, content in self.do('get_content', _id, backends=backend_names) if content]

        if len(contents) == 0:
            print >>sys.stderr, 'No contents found'
            return 1

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
                f.write(data)
            paths[path] = content

        params = ''
        if os.environ['EDITOR'] == 'vim':
            params = '-p'
        os.system("$EDITOR %s %s" % (params, ' '.join(paths.iterkeys())))

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
            print 'No changes. Abort.'
            return

        print 'Contents changed:\n%s' % ('\n'.join(' * %s' % content.id for content in contents))

        message = self.ask('Enter a commit message', default='')

        if not self.ask('Do you want to push?', default=True):
            return

        errors = CallErrors([])
        for content in contents:
            path = [path for path, c in paths.iteritems() if c == content][0]
            sys.stdout.write('Pushing %s...' % content.id)
            sys.stdout.flush()
            try:
                self.do('push_content', content, message, backends=[content.backend]).wait()
            except CallErrors, e:
                errors.errors += e.errors
                sys.stdout.write(' error (content saved in %s)\n' % path)
            else:
                sys.stdout.write(' done\n')
                os.unlink(path)

        if len(errors.errors) > 0:
            raise errors
