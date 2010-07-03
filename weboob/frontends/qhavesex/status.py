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

from __future__ import with_statement

from PyQt4.QtGui import QWidget, QVBoxLayout, QFrame, QLabel
from PyQt4.QtCore import SIGNAL, QTimer

from weboob.capabilities.dating import StatusField

class Account(QFrame):
    def __init__(self, backend, parent=None):
        QFrame.__init__(self, parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.backend = backend
        self.setLayout(QVBoxLayout())

        self.title = QLabel(u'<h1>%s — %s</h1>' % (backend.name, backend.DESCRIPTION))
        self.body = QLabel()

        self.layout().addWidget(self.title)
        self.layout().addWidget(self.body)

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.setInterval(60)
        self.connect(self.timer, SIGNAL('timeout()'), self.updateStats)

        self.updateStats()

    def updateStats(self):
        with self.backend:
            body = u''
            in_p = False
            for field in self.backend.get_status():
                if field.flags & StatusField.FIELD_HTML:
                    value = field.value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                else:
                    value = '%s' % field.value

                if field.flags & StatusField.FIELD_TEXT:
                    if in_p:
                        body += '</p>'
                    body += '<p>%s</p>' % value
                    in_p = False
                else:
                    if not in_p:
                        body += "<p>"
                        in_p = True
                    else:
                        body += "<br />"

                    body += '<b>%s</b>: %s' % (field.label, field.value)
            if in_p:
                body += "</p>"

            self.body.setText(body)

class AccountsStatus(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)

        self.weboob = weboob

        self.setLayout(QVBoxLayout())

        for backend in self.weboob.iter_backends():
            account = Account(backend)
            self.layout().addWidget(account)

        self.layout().addStretch()
