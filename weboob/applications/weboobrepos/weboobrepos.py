# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from datetime import datetime
import tarfile
import os
import shutil
import sys
from copy import copy

from weboob.core.repositories import Repository

from weboob.tools.application.repl import ReplApplication


__all__ = ['WeboobRepos']


class WeboobRepos(ReplApplication):
    APPNAME = 'weboob-repos'
    VERSION = '0.a'
    COPYRIGHT = 'Copyright(C) 2012 Romain Bignon'
    DESCRIPTION = "Weboob-repos is a console application to manage a Weboob Repository."
    COMMANDS_FORMATTERS = {'backends':    'table',
                           'list':        'table',
                           }
    DISABLE_REPL = True

    weboob_commands = copy(ReplApplication.weboob_commands)
    weboob_commands.remove('backends')

    def load_default_backends(self):
        pass

    def do_create(self, line):
        """
        create NAME [PATH]

        Create a new repository. If PATH is missing, create repository
        on the current directory.
        """
        name, path = self.parse_command_args(line, 2, 1)
        if not path:
            path = os.getcwd()
        else:
            path = os.path.realpath(path)

        if not os.path.exists(path):
            os.mkdir(path)
        elif not os.path.isdir(path):
            print u'"%s" is not a directory' % path
            return 1

        r = Repository('http://')
        r.name = name
        r.maintainer = self.ask('Enter maintainer of the repository')
        r.save(os.path.join(path, r.INDEX))
        print u'Repository "%s" created.' % path

    def do_build(self, line):
        """
        build SOURCE REPOSITORY

        Build backends contained in SOURCE to REPOSITORY.

        Example:
        $ weboob-repos build $HOME/src/weboob/modules /var/www/updates.weboob.org/0.a/
        """
        source_path, repo_path = self.parse_command_args(line, 2, 2)
        index_file = os.path.join(repo_path, Repository.INDEX)

        r = Repository('http://')
        try:
            with open(index_file, 'r') as fp:
                r.parse_index(fp)
        except IOError, e:
            print >>sys.stderr, 'Unable to open repository: %s' % e
            print >>sys.stderr, 'Use the "create" command before.'
            return 1

        r.build_index(source_path, index_file)

        for name, module in r.modules.iteritems():
            tarname = os.path.join(repo_path, '%s.tar.gz' % name)
            module_path = os.path.join(source_path, name)
            if os.path.exists(tarname):
                tar_mtime = int(datetime.fromtimestamp(os.path.getmtime(tarname)).strftime('%Y%m%d%H%M'))
                if tar_mtime >= module.version:
                    continue

            print 'Create archive for %s' % name
            tar = tarfile.open(tarname, 'w:gz')
            tar.add(module_path, arcname=name, exclude=self._archive_excludes)
            tar.close()

            # Copy icon.
            icon_path = os.path.join(module_path, 'favicon.png')
            if os.path.exists(icon_path):
                shutil.copy(icon_path, os.path.join(repo_path, '%s.png' % name))

    def _archive_excludes(self, filename):
        # Skip *.pyc files in tarballs.
        if filename.endswith('.pyc'):
            return True
        # Don't include *.png files in tarball
        if filename.endswith('.png'):
            return True
        return False

