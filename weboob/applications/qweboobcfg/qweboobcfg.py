#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ft=python et softtabstop=4 cinoptions=4 shiftwidth=4 ts=4 ai

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


from weboob.tools.application.qt import BackendCfg, QtApplication


class QWeboobCfg(QtApplication):
    APPNAME = 'qweboobcfg'
    VERSION = '0.5.1'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = "weboob-config-qt is a graphical application to add/edit/remove backends, " \
                  "and to register new website accounts."

    def main(self, argv):
        self.load_backends()

        self.dlg = BackendCfg(self.weboob)
        self.dlg.show()

        return self.weboob.loop()
