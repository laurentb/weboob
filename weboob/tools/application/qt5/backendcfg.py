# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon
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


from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QLabel, QFormLayout, \
                            QMessageBox, QHeaderView, \
                            QListWidgetItem, QVBoxLayout, \
                            QDialogButtonBox, QProgressDialog
from PyQt5.QtGui import QTextDocument, QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QVariant, QUrl, QThread
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

from collections import OrderedDict
import re
import os
from logging import warning

from weboob.core.repositories import IProgress
from weboob.core.backendscfg import BackendAlreadyExists
from weboob.capabilities.account import CapAccount, Account, AccountRegisterError
from weboob.exceptions import ModuleInstallError, ModuleLoadError
from .backendcfg_ui import Ui_BackendCfg
from .reposdlg_ui import Ui_RepositoriesDlg
from weboob.tools.misc import to_unicode
from weboob.tools.compat import unicode
from .qt import QtValue


class RepositoriesDialog(QDialog):
    def __init__(self, filename, parent=None):
        super(RepositoriesDialog, self).__init__(parent)
        self.filename = filename
        self.ui = Ui_RepositoriesDlg()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self.save)

        with open(self.filename, 'r') as fp:
            self.ui.reposEdit.setPlainText(fp.read())

    @Slot()
    def save(self):
        with open(self.filename, 'w') as fp:
            fp.write(self.ui.reposEdit.toPlainText())
        self.accept()


class IconFetcher(QThread):
    retrieved = Signal()

    def __init__(self, weboob, item, minfo):
        super(IconFetcher, self).__init__()
        self.weboob = weboob
        self.items = [item]
        self.minfo = minfo

    def run(self):
        self.weboob.repositories.retrieve_icon(self.minfo)
        self.retrieved.emit()


class ProgressDialog(IProgress, QProgressDialog):
    def __init__(self, *args, **kwargs):
        super(ProgressDialog, self).__init__(*args, **kwargs)

    def progress(self, percent, message):
        self.setValue(int(percent * 100))
        self.setLabelText(message)

    def error(self, message):
        QMessageBox.critical(self, self.tr('Error'), '%s' % message, QMessageBox.Ok)

    def prompt(self, message):
        reply = QMessageBox.question(self, '', unicode(message), QMessageBox.Yes|QMessageBox.No)

        return reply == QMessageBox.Yes


class BackendCfg(QDialog):
    def __init__(self, weboob, caps=None, parent=None):
        super(BackendCfg, self).__init__(parent)
        self.ui = Ui_BackendCfg()
        self.ui.setupUi(self)

        self.ui.backendsList.sortByColumn(0, Qt.AscendingOrder)

        self.to_unload = set()
        self.to_load = set()

        self.weboob = weboob
        self.caps = caps
        self.config_widgets = {}

        # This attribute is set when itemChanged it called, because when
        # a backend is enabled/disabled, we don't want to display its config
        # frame, and the itemClicked event is always emit just after a
        # itemChanged event.
        # is_enabling is a counter to prevent race conditions.
        self.is_enabling = 0

        self.ui.backendsList.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.configFrame.hide()

        self.icon_cache = {}
        self.icon_threads = {}

        self.loadModules()
        self.loadBackendsList()

        self.ui.updateButton.clicked.connect(self.updateModules)
        self.ui.repositoriesButton.clicked.connect(self.editRepositories)
        self.ui.backendsList.itemClicked.connect(self.backendClicked)
        self.ui.backendsList.itemChanged.connect(self.backendEnabled)
        self.ui.modulesList.itemSelectionChanged.connect(self.moduleSelectionChanged)
        self.ui.proxyBox.toggled.connect(self.proxyEditEnabled)
        self.ui.addButton.clicked.connect(self.addEvent)
        self.ui.removeButton.clicked.connect(self.removeEvent)
        self.ui.registerButton.clicked.connect(self.registerEvent)
        self.ui.configButtonBox.accepted.connect(self.acceptBackend)
        self.ui.configButtonBox.rejected.connect(self.rejectBackend)

    def get_icon_cache(self, path):
        if path not in self.icon_cache:
            img = QImage(path)
            self.icon_cache[path] = QIcon(QPixmap.fromImage(img))
        return self.icon_cache[path]

    def set_icon(self, item, minfo):
        icon_path = self.weboob.repositories.get_module_icon_path(minfo)

        icon = self.icon_cache.get(icon_path, None)
        if icon is None and not os.path.exists(icon_path):
            if minfo.name in self.icon_threads:
                self.icon_threads[minfo.name].items.append(item)
            else:
                thread = IconFetcher(self.weboob, item, minfo)
                thread.retrieved.connect(self._set_icon_slot)
                self.icon_threads[minfo.name] = thread
                thread.start()
            return

        self._set_icon([item], minfo)

    @Slot()
    def _set_icon_slot(self):
        thread = self.sender()
        self._set_icon(thread.items, thread.minfo)

    def _set_icon(self, items, minfo):
        icon_path = self.weboob.repositories.get_module_icon_path(minfo)
        icon = self.get_icon_cache(icon_path)

        if icon is None:
            return

        for item in items:
            try:
                item.setIcon(icon)
            except TypeError:
                item.setIcon(0, icon)

        self.icon_threads.pop(minfo.name, None)

    @Slot()
    def updateModules(self):
        self.ui.configFrame.hide()
        pd = ProgressDialog('Update of modules', "Cancel", 0, 100, self)
        pd.setWindowModality(Qt.WindowModal)
        try:
            self.weboob.repositories.update(pd)
        except ModuleInstallError as err:
            QMessageBox.critical(self, self.tr('Update error'),
                                 self.tr('Unable to update modules: %s' % (err)),
                                 QMessageBox.Ok)
        pd.setValue(100)
        self.loadModules()
        QMessageBox.information(self, self.tr('Update of modules'),
                                self.tr('Modules updated!'), QMessageBox.Ok)

    @Slot()
    def editRepositories(self):
        if RepositoriesDialog(self.weboob.repositories.sources_list).exec_():
            self.updateModules()

    def loadModules(self):
        self.ui.modulesList.clear()
        for name, module in sorted(self.weboob.repositories.get_all_modules_info(self.caps).items()):
            item = QListWidgetItem(name.capitalize())
            self.set_icon(item, module)
            self.ui.modulesList.addItem(item)

    def askInstallModule(self, minfo):
        reply = QMessageBox.question(self, self.tr('Install a module'),
            self.tr("Module %s is not installed. Do you want to install it?") % minfo.name,
            QMessageBox.Yes|QMessageBox.No)

        if reply != QMessageBox.Yes:
            return False

        return self.installModule(minfo)

    def installModule(self, minfo):
        pd = ProgressDialog('Installation of %s' % minfo.name, "Cancel", 0, 100, self)
        pd.setWindowModality(Qt.WindowModal)

        try:
            self.weboob.repositories.install(minfo, pd)
        except ModuleInstallError as err:
            QMessageBox.critical(self, self.tr('Install error'),
                                 self.tr('Unable to install module %s: %s' % (minfo.name, err)),
                                 QMessageBox.Ok)
        pd.setValue(100)
        return True

    def loadBackendsList(self):
        self.ui.backendsList.clear()
        for backend_name, module_name, params in self.weboob.backends_config.iter_backends():
            info = self.weboob.repositories.get_module_info(module_name)
            if not info or (self.caps and not info.has_caps(self.caps)):
                continue

            item = QTreeWidgetItem(None, [backend_name, module_name])
            item.setCheckState(0, Qt.Checked if params.get('_enabled', '1').lower() in ('1', 'y', 'true', 'on', 'yes')
                else Qt.Unchecked)

            self.set_icon(item, info)

            self.ui.backendsList.addTopLevelItem(item)

    @Slot(QTreeWidgetItem, int)
    def backendEnabled(self, item, col):
        self.is_enabling += 1

        backend_name = item.text(0)
        if item.checkState(0) == Qt.Checked:
            self.to_load.add(backend_name)
            enabled = 'true'
        else:
            self.to_unload.add(backend_name)
            try:
                self.to_load.remove(backend_name)
            except KeyError:
                pass
            enabled = 'false'

        self.weboob.backends_config.edit_backend(backend_name, {'_enabled': enabled})

    @Slot(QTreeWidgetItem, int)
    def backendClicked(self, item, col):
        if self.is_enabling:
            self.is_enabling -= 1
            return

        backend_name = item.text(0)

        self.editBackend(backend_name)

    @Slot()
    def addEvent(self):
        self.editBackend()

    @Slot()
    def removeEvent(self):
        item = self.ui.backendsList.currentItem()
        if not item:
            return

        backend_name = item.text(0)
        reply = QMessageBox.question(self, self.tr('Remove a backend'),
            self.tr("Are you sure you want to remove the backend '%s'?") % backend_name,
            QMessageBox.Yes|QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        self.weboob.backends_config.remove_backend(backend_name)
        self.to_unload.add(backend_name)
        try:
            self.to_load.remove(backend_name)
        except KeyError:
            pass
        self.ui.configFrame.hide()
        self.loadBackendsList()

    def editBackend(self, backend_name=None):
        self.ui.registerButton.hide()
        self.ui.configFrame.show()

        if backend_name is not None:
            module_name, params = self.weboob.backends_config.get_backend(backend_name)

            items = self.ui.modulesList.findItems(module_name, Qt.MatchFixedString)
            if not items:
                warning('Backend not found')
            else:
                self.ui.modulesList.setCurrentItem(items[0])
                self.ui.modulesList.setEnabled(False)

            self.ui.nameEdit.setText(backend_name)
            self.ui.nameEdit.setEnabled(False)

            if '_proxy' in params:
                self.ui.proxyBox.setChecked(True)
                self.ui.proxyEdit.setText(params.pop('_proxy'))
            else:
                self.ui.proxyBox.setChecked(False)
                self.ui.proxyEdit.clear()

            params.pop('_enabled', None)

            info = self.weboob.repositories.get_module_info(module_name)
            if info and (info.is_installed() or self.installModule(info)):
                module = self.weboob.modules_loader.get_or_load_module(module_name)
                for key, value in module.config.load(self.weboob, module_name, backend_name, params, nofail=True).items():
                    try:
                        l, widget = self.config_widgets[key]
                    except KeyError:
                        warning('Key "%s" is not found' % key)
                    else:
                        # Do not prompt user for value (for example a password if it is empty).
                        value.noprompt = True
                        widget.set_value(value)
                return

        self.ui.nameEdit.clear()
        self.ui.nameEdit.setEnabled(True)
        self.ui.proxyBox.setChecked(False)
        self.ui.proxyEdit.clear()
        self.ui.modulesList.setEnabled(True)
        self.ui.modulesList.setCurrentRow(-1)

    @Slot()
    def moduleSelectionChanged(self):
        for key, (label, value) in self.config_widgets.items():
            label.hide()
            value.hide()
            self.ui.configLayout.removeWidget(label)
            self.ui.configLayout.removeWidget(value)
            label.deleteLater()
            value.deleteLater()
        self.config_widgets = {}
        self.ui.moduleInfo.clear()

        selection = self.ui.modulesList.selectedItems()
        if not selection:
            return

        minfo = self.weboob.repositories.get_module_info(selection[0].text().lower())
        if not minfo:
            warning('Module not found')
            return

        if not minfo.is_installed() and not self.installModule(minfo):
            self.editBackend(None)
            return

        module = self.weboob.modules_loader.get_or_load_module(minfo.name)

        icon_path = os.path.join(self.weboob.repositories.icons_dir, '%s.png' % minfo.name)
        img = QImage(icon_path)
        self.ui.moduleInfo.document().addResource(QTextDocument.ImageResource, QUrl('mydata://logo.png'),
            QVariant(img))

        if module.name not in [n for n, ign, ign2 in self.weboob.backends_config.iter_backends()]:
            self.ui.nameEdit.setText(module.name)
        else:
            self.ui.nameEdit.setText('')

        self.ui.moduleInfo.setText(to_unicode(self.tr(
          u'<h1>%s Module %s</h1>'
           '<b>Version</b>: %s<br />'
           '<b>Maintainer</b>: %s<br />'
           '<b>License</b>: %s<br />'
           '%s'
           '<b>Description</b>: %s<br />'
           '<b>Capabilities</b>: %s<br />'))
           % ('<img src="mydata://logo.png" />',
              module.name.capitalize(),
              module.version,
              to_unicode(module.maintainer).replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;'),
              module.license,
              (self.tr('<b>Website</b>: %s<br />') % module.website) if module.website else '',
              module.description,
              ', '.join(sorted(cap.__name__.replace('Cap', '') for cap in module.iter_caps()))))

        if module.has_caps(CapAccount) and self.ui.nameEdit.isEnabled() and \
                module.klass.ACCOUNT_REGISTER_PROPERTIES is not None:
            self.ui.registerButton.show()
        else:
            self.ui.registerButton.hide()

        for key, field in module.config.items():
            label = QLabel(u'%s:' % field.label)
            qvalue = QtValue(field)
            self.ui.configLayout.addRow(label, qvalue)
            self.config_widgets[key] = (label, qvalue)

    @Slot(bool)
    def proxyEditEnabled(self, state):
        self.ui.proxyEdit.setEnabled(state)

    @Slot()
    def acceptBackend(self):
        backend_name = self.ui.nameEdit.text()
        selection = self.ui.modulesList.selectedItems()

        if not selection:
            QMessageBox.critical(self, self.tr('Unable to add a backend'),
                self.tr('Please select a module'))
            return

        try:
            module = self.weboob.modules_loader.get_or_load_module(selection[0].text().lower())
        except ModuleLoadError:
            module = None

        if not module:
            QMessageBox.critical(self, self.tr('Unable to add a backend'),
                self.tr('The selected module does not exist.'))
            return

        params = {}

        if not backend_name:
            QMessageBox.critical(self, self.tr('Missing field'), self.tr('Please specify a backend name'))
            return

        if self.ui.nameEdit.isEnabled():
            if not re.match(r'^[\w\-_]+$', backend_name):
                QMessageBox.critical(self, self.tr('Invalid value'),
                    self.tr('The backend name can only contain letters and digits'))
                return
            if self.weboob.backends_config.backend_exists(backend_name):
                QMessageBox.critical(self, self.tr('Unable to create backend'),
                         self.tr('Unable to create backend "%s": it already exists') % backend_name)
                return

        if self.ui.proxyBox.isChecked():
            params['_proxy'] = self.ui.proxyEdit.text()
            if not params['_proxy']:
                QMessageBox.critical(self, self.tr('Missing field'), self.tr('Please specify a proxy URL'))
                return

        config = module.config.load(self.weboob, module.name, backend_name, {}, nofail=True)
        for key, field in config.items():
            label, qtvalue = self.config_widgets[key]

            try:
                value = qtvalue.get_value()
            except ValueError as e:
                QMessageBox.critical(self, self.tr('Invalid value'),
                    self.tr('Invalid value for field "%s":<br /><br />%s') % (field.label, e))
                return

            field.set(value.get())

        try:
            config.save(edit=not self.ui.nameEdit.isEnabled(), params=params)
        except BackendAlreadyExists:
            QMessageBox.critical(self, self.tr('Unable to create backend'),
                     self.tr('Unable to create backend "%s": it already exists') % backend_name)
            return

        self.to_load.add(backend_name)
        self.ui.configFrame.hide()

        self.loadBackendsList()

    @Slot()
    def rejectBackend(self):
        self.ui.configFrame.hide()

    @Slot()
    def registerEvent(self):
        selection = self.ui.modulesList.selectedItems()
        if not selection:
            return

        try:
            module = self.weboob.modules_loader.get_or_load_module(selection[0].text().lower())
        except ModuleLoadError:
            module = None

        if not module:
            return

        dialog = QDialog(self)
        vbox = QVBoxLayout(dialog)
        if module.website:
            website = 'on the website <b>%s</b>' % module.website
        else:
            website = 'with the module <b>%s</b>' % module.name
        vbox.addWidget(QLabel('To create an account %s, please provide this information:' % website))
        formlayout = QFormLayout()
        props_widgets = OrderedDict()
        for key, prop in module.klass.ACCOUNT_REGISTER_PROPERTIES.items():
            widget = QtValue(prop)
            formlayout.addRow(QLabel(u'%s:' % prop.label), widget)
            props_widgets[prop.id] = widget

        vbox.addLayout(formlayout)
        buttonBox = QDialogButtonBox(dialog)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        vbox.addWidget(buttonBox)

        end = False
        while not end:
            end = True
            if dialog.exec_():
                account = Account()
                account.properties = {}
                for key, widget in props_widgets.items():
                    try:
                        v = widget.get_value()
                    except ValueError as e:
                        QMessageBox.critical(self, self.tr('Invalid value'),
                            self.tr('Invalid value for field "%s":<br /><br />%s') % (key, e))
                        end = False
                        break
                    else:
                        account.properties[key] = v
                if end:
                    try:
                        module.klass.register_account(account)
                    except AccountRegisterError as e:
                        QMessageBox.critical(self, self.tr('Error during register'),
                            self.tr('Unable to register account %s:<br /><br />%s') % (website, e))
                        end = False
                    else:
                        for key, value in account.properties.items():
                            if key in self.config_widgets:
                                self.config_widgets[key][1].set_value(value)

    def run(self):
        self.exec_()

        ret = (len(self.to_load) > 0 or len(self.to_unload) > 0)

        self.weboob.unload_backends(self.to_unload)
        self.weboob.load_backends(names=self.to_load)

        return ret
