# -*- coding: utf-8 -*-

# Copyright(C) 2013 Sébastien Monel
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

from __future__ import unicode_literals

from weboob.capabilities.bugtracker import CapBugTracker
from weboob.tools.application.qt5 import QtApplication
from weboob.tools.config.yamlconfig import YamlConfig

from .main_window import MainWindow


class QBoobTracker(QtApplication):
    APPNAME = 'qboobtracker'
    VERSION = '1.5'
    COPYRIGHT = 'Copyright(C) 2018-YEAR Vincent A'
    DESCRIPTION = "Qt application to search for bugs and tasks."
    SHORT_DESCRIPTION = "search for bugs/tasks"
    CAPS = CapBugTracker
    CONFIG = {'queries': {}}
    STORAGE = {'bookmarks': [], 'read': [], 'notes': {}}

    def main(self, argv):
        self.load_backends(CapBugTracker)
        self.create_storage()
        self.load_config(klass=YamlConfig)

        main_window = MainWindow(self.config, self.storage, self.weboob)
        main_window.show()
        return self.weboob.loop()
