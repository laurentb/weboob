# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon
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


from PyQt4.QtGui import QDialog, QTreeWidgetItem, QLabel, QFormLayout, \
                        QMessageBox, QPixmap, QImage, QIcon, QHeaderView, \
                        QListWidgetItem, QTextDocument, QVBoxLayout, \
                        QDialogButtonBox, QProgressDialog
from PyQt4.QtCore import SIGNAL, Qt, QVariant, QUrl, QThread

import re
import os
from logging import warning

from weboob.core.modules import ModuleLoadError
from weboob.core.repositories import IProgress, ModuleInstallError
from weboob.core.backendscfg import BackendAlreadyExists
from weboob.capabilities.account import CapAccount, Account, AccountRegisterError
from weboob.tools.application.qt.backendcfg_ui import Ui_BackendCfg
from weboob.tools.application.qt.reposdlg_ui import Ui_RepositoriesDlg
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.misc import to_unicode
from .qt import QtValue


class RepositoriesDialog(QDialog):
    def __init__(self, filename, parent=None):
        QDialog.__init__(self, parent)
        self.filename = filename
        self.ui = Ui_RepositoriesDlg()
        self.ui.setupUi(self)

        self.connect(self.ui.buttonBox, SIGNAL('accepted()'), self.save)

        with open(self.filename, 'r') as fp:
            self.ui.reposEdit.setPlainText(fp.read())

    def save(self):
        with open(self.filename, 'w') as fp:
            fp.write(self.ui.reposEdit.toPlainText())
        self.accept()


class IconFetcher(QThread):
    def __init__(self, weboob, item, minfo):
        QThread.__init__(self)
        self.weboob = weboob
        self.items = [item]
        self.minfo = minfo

    def run(self):
        self.weboob.repositories.retrieve_icon(self.minfo)
        self.emit(SIGNAL('retrieved'), self)


class ProgressDialog(IProgress, QProgressDialog):
    def __init__(self, *args, **kwargs):
        QProgressDialog.__init__(self, *args, **kwargs)

    def progress(self, percent, message):
        self.setValue(int(percent * 100))
        self.setLabelText(message)

    def error(self, message):
        QMessageBox.critical(self, self.tr('Error'), '%s' % message, QMessageBox.Ok)


class BackendCfg(QDialog):
    def __init__(self, weboob, caps=None, parent=None):
        QDialog.__init__(self, parent)
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

        self.ui.backendsList.header().setResizeMode(QHeaderView.ResizeToContents)
        self.ui.configFrame.hide()

        self.icon_cache = {}
        self.icon_threads = {}

        self.loadModules()
        self.loadBackendsList()

        self.connect(self.ui.updateButton, SIGNAL('clicked()'), self.updateModules)
        self.connect(self.ui.repositoriesButton, SIGNAL('clicked()'), self.editRepositories)
        self.connect(self.ui.backendsList, SIGNAL('itemClicked(QTreeWidgetItem *, int)'),
                     self.backendClicked)
        self.connect(self.ui.backendsList, SIGNAL('itemChanged(QTreeWidgetItem *, int)'),
                     self.backendEnabled)
        self.connect(self.ui.modulesList, SIGNAL('itemSelectionChanged()'), self.moduleSelectionChanged)
        self.connect(self.ui.proxyBox, SIGNAL('toggled(bool)'), self.proxyEditEnabled)
        self.connect(self.ui.addButton, SIGNAL('clicked()'), self.addEvent)
        self.connect(self.ui.removeButton, SIGNAL('clicked()'), self.removeEvent)
        self.connect(self.ui.registerButton, SIGNAL('clicked()'), self.registerEvent)
        self.connect(self.ui.configButtonBox, SIGNAL('accepted()'), self.acceptBackend)
        self.connect(self.ui.configButtonBox, SIGNAL('rejected()'), self.rejectBackend)

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
                self.connect(thread, SIGNAL('retrieved'), lambda t: self._set_icon(t.items, t.minfo))
                self.icon_threads[minfo.name] = thread
                thread.start()
            return

        self._set_icon([item], minfo)

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

    def updateModules(self):
        self.ui.configFrame.hide()
        pd = ProgressDialog('Update of modules', "Cancel", 0, 100, self)
        pd.setWindowModality(Qt.WindowModal)
        try:
            self.weboob.repositories.update(pd)
        except ModuleInstallError as err:
            QMessageBox.critical(self, self.tr('Update error'),
                                 unicode(self.tr('Unable to update modules: %s' % (err))),
                                 QMessageBox.Ok)
        pd.setValue(100)
        self.loadModules()
        QMessageBox.information(self, self.tr('Update of modules'),
                                self.tr('Modules updated!'), QMessageBox.Ok)

    def editRepositories(self):
        if RepositoriesDialog(self.weboob.repositories.sources_list).exec_():
            self.updateModules()

    def loadModules(self):
        self.ui.modulesList.clear()
        for name, module in sorted(self.weboob.repositories.get_all_modules_info(self.caps).iteritems()):
            item = QListWidgetItem(name.capitalize())
            self.set_icon(item, module)
            self.ui.modulesList.addItem(item)

    def askInstallModule(self, minfo):
        reply = QMessageBox.question(self, self.tr('Install a module'),
            unicode(self.tr("Module %s is not installed. Do you want to install it?")) % minfo.name,
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
                                 unicode(self.tr('Unable to install module %s: %s' % (minfo.name, err))),
                                 QMessageBox.Ok)
        pd.setValue(100)
        return True

    def loadBackendsList(self):
        self.ui.backendsList.clear()
        for instance_name, name, params in self.weboob.backends_config.iter_backends():
            info = self.weboob.repositories.get_module_info(name)
            if not info or (self.caps and not info.has_caps(self.caps)):
                continue

            item = QTreeWidgetItem(None, [instance_name, name])
            item.setCheckState(0, Qt.Checked if params.get('_enabled', '1').lower() in ('1', 'y', 'true')
                else Qt.Unchecked)

            self.set_icon(item, info)

            self.ui.backendsList.addTopLevelItem(item)

    def backendEnabled(self, item, col):
        self.is_enabling += 1

        instname = unicode(item.text(0))
        bname = unicode(item.text(1))
        if item.checkState(0) == Qt.Checked:
            self.to_load.add(instname)
            enabled = '1'
        else:
            self.to_unload.add(instname)
            try:
                self.to_load.remove(instname)
            except KeyError:
                pass
            enabled = '0'

        self.weboob.backends_config.edit_backend(instname, bname, {'_enabled': enabled})

    def backendClicked(self, item, col):
        if self.is_enabling:
            self.is_enabling -= 1
            return

        bname = unicode(item.text(0))

        self.editBackend(bname)

    def addEvent(self):
        self.editBackend()

    def removeEvent(self):
        item = self.ui.backendsList.currentItem()
        if not item:
            return

        bname = unicode(item.text(0))
        reply = QMessageBox.question(self, self.tr('Remove a backend'),
            unicode(self.tr("Are you sure you want to remove the backend '%s'?")) % bname,
            QMessageBox.Yes|QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        self.weboob.backends_config.remove_backend(bname)
        self.to_unload.add(bname)
        try:
            self.to_load.remove(bname)
        except KeyError:
            pass
        self.ui.configFrame.hide()
        self.loadBackendsList()

    def editBackend(self, name=None):
        self.ui.registerButton.hide()
        self.ui.configFrame.show()

        if name is not None:
            bname, params = self.weboob.backends_config.get_backend(name)

            items = self.ui.modulesList.findItems(bname, Qt.MatchFixedString)
            if not items:
                warning('Backend not found')
            else:
                self.ui.modulesList.setCurrentItem(items[0])
                self.ui.modulesList.setEnabled(False)

            self.ui.nameEdit.setText(name)
            self.ui.nameEdit.setEnabled(False)

            if '_proxy' in params:
                self.ui.proxyBox.setChecked(True)
                self.ui.proxyEdit.setText(params.pop('_proxy'))
            else:
                self.ui.proxyBox.setChecked(False)
                self.ui.proxyEdit.clear()

            params.pop('_enabled', None)

            info = self.weboob.repositories.get_module_info(bname)
            if info and (info.is_installed() or self.installModule(info)):
                module = self.weboob.modules_loader.get_or_load_module(bname)
                for key, value in module.config.load(self.weboob, bname, name, params, nofail=True).iteritems():
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

    def moduleSelectionChanged(self):
        for key, (label, value) in self.config_widgets.iteritems():
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

        minfo = self.weboob.repositories.get_module_info(unicode(selection[0].text()).lower())
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
              (unicode(self.tr('<b>Website</b>: %s<br />')) % module.website) if module.website else '',
              module.description,
              ', '.join(sorted(cap.__name__.replace('Cap', '') for cap in module.iter_caps()))))

        if module.has_caps(CapAccount) and self.ui.nameEdit.isEnabled() and \
                module.klass.ACCOUNT_REGISTER_PROPERTIES is not None:
            self.ui.registerButton.show()
        else:
            self.ui.registerButton.hide()

        for key, field in module.config.iteritems():
            label = QLabel(u'%s:' % field.label)
            qvalue = QtValue(field)
            self.ui.configLayout.addRow(label, qvalue)
            self.config_widgets[key] = (label, qvalue)

    def proxyEditEnabled(self, state):
        self.ui.proxyEdit.setEnabled(state)

    def acceptBackend(self):
        bname = unicode(self.ui.nameEdit.text())
        selection = self.ui.modulesList.selectedItems()

        if not selection:
            QMessageBox.critical(self, self.tr('Unable to add a backend'),
                self.tr('Please select a module'))
            return

        try:
            module = self.weboob.modules_loader.get_or_load_module(unicode(selection[0].text()).lower())
        except ModuleLoadError:
            module = None

        if not module:
            QMessageBox.critical(self, self.tr('Unable to add a backend'),
                self.tr('The selected module does not exist.'))
            return

        params = {}

        if not bname:
            QMessageBox.critical(self, self.tr('Missing field'), self.tr('Please specify a backend name'))
            return

        if self.ui.nameEdit.isEnabled():
            if not re.match(r'^[\w\-_]+$', bname):
                QMessageBox.critical(self, self.tr('Invalid value'),
                    self.tr('The backend name can only contain letters and digits'))
                return
            if self.weboob.backends_config.backend_exists(bname):
                QMessageBox.critical(self, self.tr('Unable to create backend'),
                         unicode(self.tr('Unable to create backend "%s": it already exists')) % bname)
                return

        if self.ui.proxyBox.isChecked():
            params['_proxy'] = unicode(self.ui.proxyEdit.text())
            if not params['_proxy']:
                QMessageBox.critical(self, self.tr('Missing field'), self.tr('Please specify a proxy URL'))
                return

        config = module.config.load(self.weboob, module.name, bname, {}, nofail=True)
        for key, field in config.iteritems():
            label, qtvalue = self.config_widgets[key]

            try:
                value = qtvalue.get_value()
            except ValueError as e:
                QMessageBox.critical(self, self.tr('Invalid value'),
                    unicode(self.tr('Invalid value for field "%s":<br /><br />%s')) % (field.label, e))
                return

            field.set(value.get())

        try:
            config.save(edit=not self.ui.nameEdit.isEnabled(), params=params)
        except BackendAlreadyExists:
            QMessageBox.critical(self, self.tr('Unable to create backend'),
                     unicode(self.tr('Unable to create backend "%s": it already exists')) % bname)
            return

        self.to_load.add(bname)
        self.ui.configFrame.hide()

        self.loadBackendsList()

    def rejectBackend(self):
        self.ui.configFrame.hide()

    def registerEvent(self):
        selection = self.ui.modulesList.selectedItems()
        if not selection:
            return

        try:
            module = self.weboob.modules_loader.get_or_load_module(unicode(selection[0].text()).lower())
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
        for key, prop in module.klass.ACCOUNT_REGISTER_PROPERTIES.iteritems():
            widget = QtValue(prop)
            formlayout.addRow(QLabel(u'%s:' % prop.label), widget)
            props_widgets[prop.id] = widget

        vbox.addLayout(formlayout)
        buttonBox = QDialogButtonBox(dialog)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.connect(buttonBox, SIGNAL("accepted()"), dialog.accept)
        self.connect(buttonBox, SIGNAL("rejected()"), dialog.reject)
        vbox.addWidget(buttonBox)

        end = False
        while not end:
            end = True
            if dialog.exec_():
                account = Account()
                account.properties = {}
                for key, widget in props_widgets.iteritems():
                    try:
                        v = widget.get_value()
                    except ValueError as e:
                        QMessageBox.critical(self, self.tr('Invalid value'),
                            unicode(self.tr('Invalid value for field "%s":<br /><br />%s')) % (key, e))
                        end = False
                        break
                    else:
                        account.properties[key] = v
                if end:
                    try:
                        module.klass.register_account(account)
                    except AccountRegisterError as e:
                        QMessageBox.critical(self, self.tr('Error during register'),
                            unicode(self.tr('Unable to register account %s:<br /><br />%s')) % (website, e))
                        end = False
                    else:
                        for key, value in account.properties.iteritems():
                            if key in self.config_widgets:
                                self.config_widgets[key][1].set_value(value)

    def run(self):
        self.exec_()

        ret = (len(self.to_load) > 0 or len(self.to_unload) > 0)

        self.weboob.unload_backends(self.to_unload)
        self.weboob.load_backends(names=self.to_load)

        return ret
