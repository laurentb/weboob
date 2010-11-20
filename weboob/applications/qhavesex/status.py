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


from PyQt4.QtGui import QScrollArea, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QImage, QPixmap

from weboob.capabilities.account import ICapAccount, StatusField
from weboob.tools.application.qt import QtDo

class Account(QFrame):
    def __init__(self, weboob, backend, parent=None):
        QFrame.__init__(self, parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.weboob = weboob
        self.backend = backend
        self.setLayout(QVBoxLayout())
        self.timer = None

        head = QHBoxLayout()
        headw = QWidget()
        headw.setLayout(head)

        self.title = QLabel(u'<h1>%s — %s</h1>' % (backend.name, backend.DESCRIPTION))
        self.body = QLabel()

        if backend.ICON:
            self.icon = QLabel()
            img = QImage(backend.ICON)
            self.icon.setPixmap(QPixmap.fromImage(img))
            head.addWidget(self.icon)

        head.addWidget(self.title)
        head.addStretch()

        self.layout().addWidget(headw)

        if backend.has_caps(ICapAccount):
            self.body.setText(u'<i>Waiting...</i>')
            self.layout().addWidget(self.body)

            self.timer = self.weboob.repeat(60, self.updateStats)

    def deinit(self):
        if self.timer is not None:
            self.weboob.stop(self.timer)

    def updateStats(self):
        self.process = QtDo(self.weboob, self.updateStats_cb, self.updateStats_eb)
        self.process.body = u''
        self.process.in_p = False
        self.process.do('get_account_status', backends=self.backend)

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

class AccountsStatus(QScrollArea):
    def __init__(self, weboob, parent=None):
        QScrollArea.__init__(self, parent)

        self.weboob = weboob

        self.setFrameShadow(self.Plain)
        self.setFrameShape(self.NoFrame)
        self.setWidgetResizable(True)

        widget = QWidget(self)
        widget.setLayout(QVBoxLayout())
        widget.show()
        self.setWidget(widget)

    def load(self):
        while self.widget().layout().count() > 0:
            item = self.widget().layout().takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

        for backend in self.weboob.iter_backends():
            account = Account(self.weboob, backend)
            self.widget().layout().addWidget(account)

        self.widget().layout().addStretch()
