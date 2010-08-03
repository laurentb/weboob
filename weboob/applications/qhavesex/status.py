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

from PyQt4.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QImage, QPixmap

from weboob.capabilities.dating import StatusField
from weboob.tools.application.qt import QtDo

class Account(QFrame):
    def __init__(self, weboob, backend, parent=None):
        QFrame.__init__(self, parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.weboob = weboob
        self.backend = backend
        self.setLayout(QVBoxLayout())

        head = QHBoxLayout()
        headw = QWidget()
        headw.setLayout(head)

        self.title = QLabel(u'<h1>%s — %s</h1>' % (backend.name, backend.DESCRIPTION))

        if backend.ICON:
            self.icon = QLabel()
            img = QImage(backend.ICON)
            self.icon.setPixmap(QPixmap.fromImage(img))
            head.addWidget(self.icon)

        head.addWidget(self.title)
        head.addStretch()

        self.body = QLabel(u'<i>Waiting...</i>')

        self.layout().addWidget(headw)
        self.layout().addWidget(self.body)

        self.weboob.repeat(60, self.updateStats)

    def updateStats(self):
        self.process = QtDo(self.weboob, self.updateStats_cb, self.updateStats_eb)
        self.process.body = u''
        self.process.in_p = False
        self.process.do('get_status', backends=self.backend)

    def updateStats_cb(self, backend, field):
        if not field:
            if self.process.in_p:
                self.process.body += u"</p>"

            self.body.setText(self.process.body)

            self.process = None
            return

        if field.flags & StatusField.FIELD_HTML:
            value = u'%s' % field.value
        else:
            value = (u'%s' % field.value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        if field.flags & StatusField.FIELD_TEXT:
            if self.process.in_p:
                self.process.body += u'</p>'
            self.process.body += u'<p>%s</p>' % value
            self.process.in_p = False
        else:
            if not self.process.in_p:
                self.process.body += u"<p>"
                self.process.in_p = True
            else:
                self.process.body += u"<br />"

            self.process.body += u'<b>%s</b>: %s' % (field.label, field.value)

    def updateStats_eb(self, backend, err, backtrace):
        self.body.setText(u'<b>Unable to connect:</b> %s' % unicode(err))
        self.title.setText(u'<font color=#ff0000>%s</font>' % unicode(self.title.text()))

class AccountsStatus(QWidget):
    def __init__(self, weboob, parent=None):
        QWidget.__init__(self, parent)

        self.weboob = weboob

        self.setLayout(QVBoxLayout())

    def load(self):
        while self.layout().count() > 0:
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

        for backend in self.weboob.iter_backends():
            account = Account(self.weboob, backend)
            self.layout().addWidget(account)

        self.layout().addStretch()
