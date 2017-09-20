# -*- coding: utf-8 -*-

# Copyright(C) 2016 Vincent A
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


from weboob.capabilities.gallery import CapGallery
from weboob.capabilities.image import CapImage
from weboob.tools.application.qt5 import QtApplication
from weboob.tools.config.yamlconfig import YamlConfig

from .main_window import MainWindow


class QGalleroob(QtApplication):
    APPNAME = 'qgalleroob'
    VERSION = '1.3'
    COPYRIGHT = u'Copyright(C) 2016 Vincent A'
    DESCRIPTION = "Qt application to view image galleries."
    SHORT_DESCRIPTION = "search for images"
    #~ CONFIG = {'queries': {}}
    #~ STORAGE = {'bookmarks': [], 'read': [], 'notes': {}}

    def main(self, argv):
        self.load_backends(CapGallery)
        self.load_backends(CapImage)
        self.create_storage()
        self.load_config(klass=YamlConfig)

        main_window = MainWindow(self.config, self.storage, self.weboob)
        main_window.show()
        return self.weboob.loop()
