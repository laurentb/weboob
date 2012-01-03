# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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


import tarfile
import posixpath
import shutil
import re
import sys
import os
from datetime import datetime

from .modules import Module
from weboob.tools.log import getLogger
from weboob.tools.misc import to_unicode
from weboob.tools.browser import StandardBrowser, BrowserUnavailable
from ConfigParser import RawConfigParser, DEFAULTSECT

class ModuleInfo(object):
    def __init__(self, name):
        self.name = name

        # path to the local directory containing this module.
        self.path = None
        self.url = None

        self.version = 0
        self.capabilities = ()
        self.description = u''
        self.maintainer = u''
        self.license = u''
        self.icon = u''
        self.urls = u''

    def load(self, items):
        self.version = int(items['version'])
        self.capabilities = items['capabilities'].split()
        self.description = to_unicode(items['description'])
        self.maintainer = to_unicode(items['maintainer'])
        self.license = to_unicode(items['license'])
        self.icon = items['icon']
        self.urls = items['urls']

    def has_caps(self, caps):
        if not isinstance(caps, (list,tuple)):
            caps = [caps]
        for c in caps:
            if type(c) == type:
                c = c.__name__
            if c in self.capabilities:
                return True
        return False

    def is_installed(self):
        return self.path is not None

    def is_local(self):
        return self.url is None

    def dump(self):
        return (('version', self.version),
                ('capabilities', ' '.join(self.capabilities)),
                ('description', self.description),
                ('maintainer', self.maintainer),
                ('license', self.license),
                ('icon', self.icon),
                ('urls', self.urls),
               )

class RepositoryUnavailable(Exception):
    pass

class Repository(object):
    INDEX = 'modules.list'

    def __init__(self, url):
        self.url = url
        self.name = u''
        self.update = 0
        self.maintainer = u''
        self.local = None

        self.modules = {}

        if self.url.startswith('file://'):
            self.local = True
        elif re.match('https?://.*', self.url):
            self.local = False
        else:
            # This is probably a file in ~/.weboob/repositories/, we
            # don't know if this is a local or a remote repository.
            with open(self.url, 'r') as fp:
                self.parse_index(fp)

    def localurl2path(self):
        """
        Get a local path of a file:// URL.
        """
        assert self.local == True

        if self.url.startswith('file://'):
            return self.url[len('file://'):]
        return self.url

    def retrieve_index(self, dest_path):
        """
        Retrieve the index file of this repository. It can use network
        if this is a remote repository.

        @param dest_path [str]  path to save the downloaded index file.
        """
        if self.local:
            # Repository is local, open the file.
            filename = os.path.join(self.localurl2path(), self.INDEX)
            try:
                fp = open(filename, 'r')
            except IOError, e:
                # This local repository doesn't contain a built modules.list index.
                self.name = self.url.replace(os.path.sep, '_')
                self.build_index(self.localurl2path(), filename)
                fp = open(filename, 'r')
        else:
            # This is a remote repository, download file
            browser = StandardBrowser()
            try:
                fp = browser.openurl(posixpath.join(self.url, self.INDEX))
            except BrowserUnavailable, e:
                raise RepositoryUnavailable(unicode(e))

        self.parse_index(fp)

        if self.local:
            # Always rebuild index of a local repository.
            self.build_index(self.localurl2path(), filename)

        # Save the repository index in ~/.weboob/repositories/
        self.save(dest_path, private=True)

    def parse_index(self, fp):
        """
        Parse index of a repository

        @param fp [buffer]  file descriptor to read
        """
        config = RawConfigParser()
        config.readfp(fp)

        # Read default parameters
        items = dict(config.items(DEFAULTSECT))
        try:
            self.name = items['name']
            self.update = int(items['update'])
            self.maintainer = items['maintainer']
        except KeyError, e:
            raise RepositoryUnavailable('Missing global parameters in repository: %s' % e)
        except ValueError, e:
            raise RepositoryUnavailable('Incorrect value in repository parameters: %s' % e)

        if len(self.name) == 0:
            raise RepositoryUnavailable('Name is empty')

        if 'url' in items:
            self.url = items['url']
            self.local = self.url.startswith('file://')
        elif self.local is None:
            raise RepositoryUnavailable('Missing "url" key in settings')

        # Load modules
        self.modules.clear()
        for section in config.sections():
            module = ModuleInfo(section)
            module.load(dict(config.items(section)))
            if not self.local:
                module.url = posixpath.join(self.url, '%s.tar.gz' % module.name)
            self.modules[section] = module

    def build_index(self, path, filename):
        """
        Rebuild index of modules of repository.

        @param path [str]  path of the repository
        @param filename [str]  file to save index
        """
        print 'Rebuild index'
        self.modules.clear()

        sys.path.append(path)
        for name in sorted(os.listdir(path)):
            module_path = os.path.join(path, name)
            if not os.path.isdir(module_path) or '.' in name:
                continue

            try:
                module = Module(__import__(name, fromlist=[str(name)]))
            except Exception, e:
                print 'ERROR: %s' % e
            else:
                m = ModuleInfo(module.name)
                m.version = int(datetime.fromtimestamp(os.path.getmtime(module_path)).strftime('%Y%m%d%H%M'))
                m.capabilities = [c.__name__ for c in module.iter_caps()]
                m.description = module.description
                m.maintainer = module.maintainer
                m.license = module.license
                m.icon = module.icon or ''
                self.modules[module.name] = m
        sys.path.remove(path)

        self.update = int(datetime.now().strftime('%Y%m%d%H%M'))
        self.save(filename)

    def save(self, filename, private=False):
        """
        Save repository into a file (modules.list for example).

        @param filename [str]  path to file to save repository.
        @param private [bool]  if enabled, save URL of repository.
        """
        config = RawConfigParser()
        config.set(DEFAULTSECT, 'name', self.name)
        config.set(DEFAULTSECT, 'update', self.update)
        config.set(DEFAULTSECT, 'maintainer', self.maintainer)
        if private:
            config.set(DEFAULTSECT, 'url', self.url)

        for module in self.modules.itervalues():
            config.add_section(module.name)
            for key, value in module.dump():
                config.set(module.name, key, to_unicode(value).encode('utf-8'))

        with open(filename, 'wb') as f:
            config.write(f)

class Versions(object):
    VERSIONS_LIST = 'versions.list'

    def __init__(self, path):
        self.path = path
        self.versions = {}

        try:
            with open(os.path.join(self.path, self.VERSIONS_LIST), 'r') as fp:
                config = RawConfigParser()
                config.readfp(fp)

                # Read default parameters
                for key, value in config.items(DEFAULTSECT):
                    self.versions[key] = int(value)
        except IOError:
            pass

    def get(self, name):
        return self.versions.get(name, None)

    def set(self, name, version):
        self.versions[name] = int(version)
        self.save()

    def save(self):
        config = RawConfigParser()
        for name, version in self.versions.iteritems():
            config.set(DEFAULTSECT, name, version)
        with open(os.path.join(self.path, self.VERSIONS_LIST), 'wb') as fp:
            config.write(fp)

class IProgress:
    def progress(self, percent, message):
        pass

class ModuleInstallError(Exception):
    pass

DEFAULT_SOURCES_LIST = \
"""# List of Weboob repositories

http://updates.weboob.org/%(version)s/main/
# To enable NSFW backends, uncomment the following line:
#http://updates.weboob.org/%(version)s/nsfw/

# DEVELOPMENT
# If you want to hack on Weboob backends, you may add a reference
# to sources, for example:
#file:///home/rom1/src/weboob/modules/
"""

class Repositories(object):
    SOURCES_LIST = 'sources.list'
    MODULES_DIR = 'modules'
    REPOSITORIES_DIR = 'repositories'
    ICONS_DIR = 'icons'

    def __init__(self, workdir, version):
        self.logger = getLogger('repositories')
        self.version = version
        self.workdir = workdir
        self.sources_list = os.path.join(self.workdir, self.SOURCES_LIST)
        self.modules_dir = os.path.join(self.workdir, self.MODULES_DIR)
        self.repos_dir = os.path.join(self.workdir, self.REPOSITORIES_DIR)
        self.icons_dir = os.path.join(self.workdir, self.ICONS_DIR)

        self.create_dir(self.repos_dir)
        self.create_dir(self.modules_dir)
        self.create_dir(self.icons_dir)

        self.versions = Versions(self.modules_dir)

        self.repositories = []

        if not os.path.exists(self.sources_list):
            with open(self.sources_list, 'w') as f:
                f.write(DEFAULT_SOURCES_LIST)
            self.update()
        else:
            self.load()

    def create_dir(self, name):
        if not os.path.exists(name):
            os.mkdir(name)
        elif not os.path.isdir(name):
            self.logger.warning(u'"%s" is not a directory' % name)

    def _extend_module_info(self, repos, info):
        if repos.local:
            info.path = repos.localurl2path()
        elif self.versions.get(info.name) is not None:
            info.path = self.modules_dir
        return info

    def get_all_modules_info(self, caps=None):
        """
        Get all ModuleInfo instances available.

        @param caps [list(str)]  Filter on capabilities.
        @return [dict(ModuleInfo)]
        """
        modules = {}
        for repos in reversed(self.repositories):
            for name, info in repos.modules.iteritems():
                if not name in modules and (not caps or info.has_caps(caps)):
                    modules[name] = self._extend_module_info(repos, info)
        return modules

    def get_module_info(self, name):
        """
        Get ModuleInfo object of a module.

        It tries all repositories from last to first, and set
        the 'path' attribute of ModuleInfo if it is installed.
        """
        for repos in reversed(self.repositories):
            if name in repos.modules:
                m = repos.modules[name]
                self._extend_module_info(repos, m)
                return m
        return None

    def load(self):
        """
        Load repositories from ~/.weboob/repositories/.
        """
        self.repositories = []
        for name in os.listdir(self.repos_dir):
            repository = Repository(os.path.join(self.repos_dir, name))
            self.repositories.append(repository)

    def retrieve_icon(self, module):
        """
        Retrieve the icon of a module and save it in ~/.weboob/icons/.
        """
        if not isinstance(module, ModuleInfo):
            module = self.get_module_info(module)

        dest_path = os.path.join(self.icons_dir, '%s.png' % module.name)

        if module.is_local():
            icon_path = os.path.join(module.path, module.name, 'favicon.png')
            if module.path and os.path.exists(icon_path):
                shutil.copy(icon_path, dest_path)
            return

        if module.icon:
            icon_url = module.icon
        else:
            icon_url = module.url.replace('.tar.gz', '.png')

        browser = StandardBrowser()
        try:
            icon = browser.openurl(icon_url)
        except BrowserUnavailable:
            pass # no icon, no problem
        else:
            with open(dest_path, 'wb') as fp:
                fp.write(icon.read())

    def update(self, progress=IProgress()):
        """
        Update list of repositories by downloading them
        and put them in ~/.weboob/repositories/.

        @param progress [IProgress]  observer object.
        """
        self.repositories = []
        for name in os.listdir(self.repos_dir):
            os.remove(os.path.join(self.repos_dir, name))

        with open(self.sources_list, 'r') as f:
            for line in f.xreadlines():
                line = line.strip() % {'version': self.version}
                m = re.match('(file|https?)://.*', line)
                if m:
                    print 'Getting %s' % line
                    repository = Repository(line)
                    dest_path = os.path.join(self.repos_dir, '%02d-%s' % (len(self.repositories),
                                                                          repository.url.replace(os.path.sep, '_')))
                    try:
                        repository.retrieve_index(dest_path)
                    except RepositoryUnavailable, e:
                        print 'Error: %s' % e
                    else:
                        self.repositories.append(repository)

        to_update = []
        for name, info in self.get_all_modules_info().iteritems():
            if not info.is_local() and info.is_installed():
                to_update.append(info)

        class InstallProgress(IProgress):
            def __init__(self, n):
                self.n = n

            def progress(self, percent, message):
                progress.progress(float(self.n)/len(to_update) + 1.0/len(to_update)*percent, message)

        for n, info in enumerate(to_update):
            inst_progress = InstallProgress(n)
            try:
                self.install(info, inst_progress)
            except ModuleInstallError, e:
                inst_progress.progress(1.0, unicode(e))

    def install(self, module, progress=IProgress()):
        """
        Install a module.

        @paran module [str,ModuleInfo] module to install.
        @param progress [IProgress]  observer object.
        """
        if isinstance(module, ModuleInfo):
            info = module
        elif isinstance(module, basestring):
            progress.progress(0.0, 'Looking for module %s' % module)
            info = self.get_module_info(module)
            if not info:
                raise ModuleInstallError('Module "%s" does not exist' % module)
        else:
            raise ValueError('"module" parameter might be a ModuleInfo object or a string, not %r' % module)

        if info.is_local():
            raise ModuleInstallError('%s is available on local.' % info.name)

        installed = self.versions.get(info.name)
        if installed is None:
            progress.progress(0.3, 'Module is not installed yet')
        elif info.version > installed:
            progress.progress(0.3, 'A new version of this module is available')
        else:
            raise ModuleInstallError('The last version is already installed')

        browser = StandardBrowser()
        progress.progress(0.2, 'Downloading module...')
        try:
            fp = browser.openurl(info.url)
        except BrowserUnavailable, e:
            raise ModuleInstallError('Unable to fetch module: %s' % e)

        progress.progress(0.7, 'Setting up module...')

        # Extract module from tarball.
        with tarfile.open('', 'r:gz', fp) as tar:
            tar.extractall(self.modules_dir)

        self.versions.set(info.name, info.version)

        progress.progress(0.9, 'Downloading icon...')
        self.retrieve_icon(info)

        progress.progress(1.0, 'Module %s has been installed!' % info.name)
