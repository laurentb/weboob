# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from __future__ import print_function

import sys
import logging
import re
import gc
from threading import Event
from traceback import print_exc
from copy import copy

from PyQt5.QtCore import QTimer, QObject, QSize, QVariant, QMutex, Qt
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtWidgets import QApplication, QCheckBox, QComboBox, QInputDialog, \
                            QLineEdit, QMainWindow, QMessageBox, QSpinBox, \
                            QStyle, QStyledItemDelegate, QStyleOptionViewItem
from PyQt5.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette

from weboob.core.ouiboube import Weboob, VersionsMismatchError
from weboob.core.scheduler import IScheduler
from weboob.tools.compat import range, unicode
from weboob.tools.config.iconfig import ConfigError
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword, BrowserForbidden, ModuleInstallError
from weboob.tools.value import ValueInt, ValueBool, ValueBackendPassword
from weboob.tools.misc import to_unicode
from weboob.capabilities import UserError

from ..base import Application, MoreResultsAvailable


__all__ = ['QtApplication', 'QtMainWindow', 'QtDo', 'HTMLDelegate']


class QtScheduler(QObject, IScheduler):
    def __init__(self, app):
        super(QtScheduler, self).__init__(parent=app)
        self.params = {}

    def schedule(self, interval, function, *args):
        timer = QTimer()
        timer.setInterval(interval * 1000)
        timer.setSingleShot(True)

        self.params[timer] = (None, function, args)

        timer.timeout.connect(self.timeout)
        timer.start()

    def repeat(self, interval, function, *args):
        timer = QTimer()
        timer.setSingleShot(False)

        self.params[timer] = (interval, function, args)

        timer.start(0)
        timer.timeout.connect(self.timeout, Qt.QueuedConnection)

    @Slot()
    def timeout(self):
        timer = self.sender()
        interval, function, args = self.params[timer]

        function(*args)
        if interval is None:
            self.timers.pop(timer)
        else:
            timer.setInterval(interval * 1000)

    def want_stop(self):
        QApplication.instance().quit()

    def run(self):
        return QApplication.instance().exec_()


class QCallbacksManager(QObject):
    class Request(object):
        def __init__(self):
            self.event = Event()
            self.answer = None

        def __call__(self):
            raise NotImplementedError()

    class LoginRequest(Request):
        def __init__(self, backend_name, value):
            super(QCallbacksManager.LoginRequest, self).__init__()
            self.backend_name = backend_name
            self.value = value

        def __call__(self):
            password, ok = QInputDialog.getText(None,
                '%s request' % self.value.label,
                'Please enter %s for %s' % (self.value.label,
                                            self.backend_name),
                                                QLineEdit.Password)
            return password

    new_request = Signal()

    def __init__(self, weboob, parent=None):
        super(QCallbacksManager, self).__init__(parent)
        self.weboob = weboob
        self.weboob.requests.register('login', self.callback(self.LoginRequest))
        self.mutex = QMutex()
        self.requests = []
        self.new_request.connect(self.do_request)

    def callback(self, klass):
        def cb(*args, **kwargs):
            return self.add_request(klass(*args, **kwargs))
        return cb

    @Slot()
    def do_request(self):
        self.mutex.lock()
        request = self.requests.pop()
        request.answer = request()
        request.event.set()
        self.mutex.unlock()

    def add_request(self, request):
        self.mutex.lock()
        self.requests.append(request)
        self.mutex.unlock()
        self.new_request.emit()
        request.event.wait()
        return request.answer


class QtApplication(QApplication, Application):
    def __init__(self):
        super(QtApplication, self).__init__(sys.argv)
        self.setApplicationName(self.APPNAME)

        self.cbmanager = QCallbacksManager(self.weboob, self)

    def create_weboob(self):
        return Weboob(scheduler=QtScheduler(self))

    def load_backends(self, *args, **kwargs):
        while True:
            last_exc = None
            try:
                return Application.load_backends(self, *args, **kwargs)
            except VersionsMismatchError as e:
                msg = 'Versions of modules mismatch with version of weboob.'
                last_exc = e
            except ConfigError as e:
                msg = unicode(e)
                last_exc = e

            res = QMessageBox.question(None, 'Configuration error', u'%s\n\nDo you want to update repositories?' % msg, QMessageBox.Yes|QMessageBox.No)
            if res == QMessageBox.No:
                raise last_exc

            # Do not import it globally, it causes circular imports
            from .backendcfg import ProgressDialog
            pd = ProgressDialog('Update of repositories', "Cancel", 0, 100)
            pd.setWindowModality(Qt.WindowModal)
            try:
                self.weboob.update(pd)
            except ModuleInstallError as err:
                QMessageBox.critical(None, self.tr('Update error'),
                                     self.tr('Unable to update repositories: %s' % err),
                                     QMessageBox.Ok)
            pd.setValue(100)
            QMessageBox.information(None, self.tr('Update of repositories'),
                                    self.tr('Repositories updated!'), QMessageBox.Ok)

    def deinit(self):
        super(QtApplication, self).deinit()
        gc.collect()


class QtMainWindow(QMainWindow):
    pass


class QtDo(QObject):
    gotResponse = Signal(object)
    gotError = Signal(object, object, object)
    finished = Signal()

    def __init__(self, weboob, cb, eb=None, fb=None, retain=False):
        super(QtDo, self).__init__()

        if not eb:
            eb = self.default_eb

        self.weboob = weboob
        self.process = None
        self.cb = cb
        self.eb = eb
        self.fb = fb

        self.gotResponse.connect(self.local_cb)
        self.gotError.connect(self.local_eb)
        self.finished.connect(self.local_fb)

        if not retain:
            QApplication.instance().aboutToQuit.connect(self.stop)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            print_exc()

    def do(self, *args, **kwargs):
        assert self.process is None
        self.process = self.weboob.do(*args, **kwargs)
        self.process.callback_thread(self.thread_cb, self.thread_eb, self.thread_fb)

    @Slot()
    def stop(self, wait=False):
        if self.process is not None:
            self.process.stop(wait)

    @Slot(object, object, object)
    def default_eb(self, backend, error, backtrace):
        if isinstance(error, MoreResultsAvailable):
            # This is not an error, ignore.
            return

        msg = unicode(error)
        if isinstance(error, BrowserIncorrectPassword):
            if not msg:
                msg = 'Invalid login/password.'
        elif isinstance(error, BrowserUnavailable):
            if not msg:
                msg = 'Website is unavailable.'
        elif isinstance(error, BrowserForbidden):
            if not msg:
                msg = 'This action is forbidden.'
        elif isinstance(error, NotImplementedError):
            msg = u'This feature is not supported by this backend.\n\n' \
                  u'To help the maintainer of this backend implement this feature, please contact: %s <%s>' % (backend.MAINTAINER, backend.EMAIL)
        elif isinstance(error, UserError):
            if not msg:
                msg = type(error).__name__
        elif logging.root.level <= logging.DEBUG:
            msg += u'<br />'
            ul_opened = False
            for line in backtrace.split('\n'):
                m = re.match('  File (.*)', line)
                if m:
                    if not ul_opened:
                        msg += u'<ul>'
                        ul_opened = True
                    else:
                        msg += u'</li>'
                    msg += u'<li><b>%s</b>' % m.group(1)
                else:
                    msg += u'<br />%s' % to_unicode(line)
            if ul_opened:
                msg += u'</li></ul>'
            print(error, file=sys.stderr)
            print(backtrace, file=sys.stderr)
        QMessageBox.critical(None, self.tr('Error with backend %s') % backend.name,
                             msg, QMessageBox.Ok)

    @Slot(object)
    def local_cb(self, data):
        if self.cb:
            self.cb(data)

    @Slot(object, object, object)
    def local_eb(self, backend, error, backtrace):
        if self.eb:
            self.eb(backend, error, backtrace)

    @Slot()
    def local_fb(self):
        if self.fb:
            self.fb()

        self.gotResponse.disconnect(self.local_cb)
        self.gotError.disconnect(self.local_eb)
        self.finished.disconnect(self.local_fb)
        self.process = None

    def thread_cb(self, data):
        self.gotResponse.emit(data)

    def thread_eb(self, backend, error, backtrace):
        self.gotError.emit(backend, error, backtrace)

    def thread_fb(self):
        self.finished.emit()


class HTMLDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option = QStyleOptionViewItem(option) # copy option
        self.initStyleOption(option, index)

        style = option.widget.style() if option.widget else QApplication.style()

        doc = QTextDocument()
        doc.setHtml(option.text)

        # painting item without text
        option.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, option, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        # Hilight text if item is selected
        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, option)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)

        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.setTextWidth(option.rect.width())

        return QSize(doc.idealWidth(), max(doc.size().height(), option.decorationSize.height()))


class _QtValueStr(QLineEdit):
    def __init__(self, value):
        super(_QtValueStr, self).__init__()
        self._value = value
        if value.default:
            self.setText(unicode(value.default))
        if value.masked:
            self.setEchoMode(self.Password)

    def set_value(self, value):
        self._value = value
        self.setText(self._value.get())

    def get_value(self):
        self._value.set(self.text())
        return self._value


class _QtValueBackendPassword(_QtValueStr):
    def get_value(self):
        self._value._domain = None
        return _QtValueStr.get_value(self)


class _QtValueBool(QCheckBox):
    def __init__(self, value):
        super(_QtValueBool, self).__init__()
        self._value = value
        if value.default:
            self.setChecked(True)

    def set_value(self, value):
        self._value = value
        self.setChecked(self._value.get())

    def get_value(self):
        self._value.set(self.isChecked())
        return self._value


class _QtValueInt(QSpinBox):
    def __init__(self, value):
        super(_QtValueInt, self).__init__()
        self._value = value
        if value.default:
            self.setValue(int(value.default))

    def set_value(self, value):
        self._value = value
        self.setValue(self._value.get())

    def get_value(self):
        self._value.set(self.getValue())
        return self._value


class _QtValueChoices(QComboBox):
    def __init__(self, value):
        super(_QtValueChoices, self).__init__()
        self._value = value
        for k, l in value.choices.items():
            self.addItem(l, QVariant(k))
            if value.default == k:
                self.setCurrentIndex(self.count()-1)

    def set_value(self, value):
        self._value = value
        for i in range(self.count()):
            if self.itemData(i) == self._value.get():
                self.setCurrentIndex(i)
                return

    def get_value(self):
        self._value.set(self.itemData(self.currentIndex()))
        return self._value


def QtValue(value):
    if isinstance(value, ValueBool):
        klass = _QtValueBool
    elif isinstance(value, ValueInt):
        klass = _QtValueInt
    elif isinstance(value, ValueBackendPassword):
        klass = _QtValueBackendPassword
    elif value.choices is not None:
        klass = _QtValueChoices
    else:
        klass = _QtValueStr

    return klass(copy(value))


# if the default excepthook is used, PyQt 5.5 *aborts* the app when an unhandled exception occurs
# see http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
# as this behaviour is questionable, we restore the old one

if sys.excepthook is sys.__excepthook__:
    sys.excepthook = lambda *args: sys.__excepthook__(*args)
