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

import os
import sys
import tempfile

from weboob.capabilities.content import ICapContent
from weboob.tools.application.repl import ReplApplication


__all__ = ['WebContentEdit']


class WebContentEdit(ReplApplication):
    APPNAME = 'webcontentedit'
    VERSION = '0.3'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    CAPS = ICapContent

    def do_edit(self, id):
        _id, backend_name = self.parse_id(id)
        backend_names = (backend_name,) if backend_name is not None else self.enabled_backends

        contents = [content for backend, content in self.do('get_content', _id, backends=backend_names) if content]

        if len(contents) == 0:
            print >>sys.stderr, 'No content for the ID "%s"' % id
            return 1
        elif len(contents) > 1:
            print >>sys.stderr, 'Too much replies'
            return 1

        content = contents[0]

        tmpdir = os.path.join(tempfile.gettempdir(), "weboob")
        if not os.path.isdir(tmpdir):
            os.makedirs(tmpdir)
        fd, path = tempfile.mkstemp(prefix="webcontentedit", dir=tmpdir)
        with os.fdopen(fd, 'w') as f:
            data = content.content
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            f.write(data)
        os.system("$EDITOR %s" % path)

        with open(path, 'r') as f:
            data = f.read().decode('utf-8')

        if data == content.content:
            print 'No changes. Abort.'
            return

        if not self.ask('Do you want to push?', default=True):
            return

        message = self.ask('Enter a commit message', default='')

        content.content = data
        backend = self.weboob.get_backend(content.backend)
        backend.push_content(content, message)
