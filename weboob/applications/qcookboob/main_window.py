# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

import os

from PyQt5.QtCore import pyqtSlot as Slot, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QFrame, QShortcut

from weboob.capabilities.recipe import CapRecipe
from weboob.tools.application.qt5 import QtMainWindow, QtDo
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.tools.application.qt5.models import BackendListModel
from weboob.tools.application.qt5.search_history import HistoryCompleter

from weboob.applications.qcookboob.ui.main_window_ui import Ui_MainWindow
from weboob.applications.qcookboob.ui.result_ui import Ui_Result

from .minirecipe import MiniRecipe
from .recipe import Recipe

MAX_TAB_TEXT_LENGTH=30

class Result(QFrame):
    def __init__(self, weboob, app, parent=None):
        super(Result, self).__init__(parent)
        self.ui = Ui_Result()
        self.ui.setupUi(self)

        self.parent = parent
        self.weboob = weboob
        self.app = app
        self.minis = []
        self.current_info_widget = None

        # action history is composed by the last action and the action list
        # An action is a function, a list of arguments and a description string
        self.action_history = {'last_action': None, 'action_list': []}
        self.ui.backButton.clicked.connect(self.doBack)
        self.ui.backButton.setShortcut(QKeySequence('Alt+Left'))
        self.ui.backButton.hide()

    def doAction(self, description, fun, args):
        ''' Call fun with args as arguments
        and save it in the action history
        '''
        self.ui.currentActionLabel.setText(description)
        if self.action_history['last_action'] is not None:
            self.action_history['action_list'].append(self.action_history['last_action'])
            self.ui.backButton.setToolTip('%s (Alt+Left)'%self.action_history['last_action']['description'])
            self.ui.backButton.show()
        self.action_history['last_action'] = {'function': fun, 'args': args, 'description': description}
        # manage tab text
        mytabindex = self.parent.ui.resultsTab.indexOf(self)
        tabtxt = description
        if len(tabtxt) > MAX_TAB_TEXT_LENGTH:
            tabtxt = '%s...'%tabtxt[:MAX_TAB_TEXT_LENGTH]
        self.parent.ui.resultsTab.setTabText(mytabindex, tabtxt)
        self.parent.ui.resultsTab.setTabToolTip(mytabindex, description)
        return fun(*args)

    @Slot()
    def doBack(self):
        ''' Go back in action history
        Basically call previous function and update history
        '''
        if len(self.action_history['action_list']) > 0:
            todo = self.action_history['action_list'].pop()
            self.ui.currentActionLabel.setText(todo['description'])
            self.action_history['last_action'] = todo
            if len(self.action_history['action_list']) == 0:
                self.ui.backButton.hide()
            else:
                self.ui.backButton.setToolTip(self.action_history['action_list'][-1]['description'])
            # manage tab text
            mytabindex = self.parent.ui.resultsTab.indexOf(self)
            tabtxt = todo['description']
            if len(tabtxt) > MAX_TAB_TEXT_LENGTH:
                tabtxt = '%s...'%tabtxt[:MAX_TAB_TEXT_LENGTH]
            self.parent.ui.resultsTab.setTabText(mytabindex, tabtxt)
            self.parent.ui.resultsTab.setTabToolTip(mytabindex, todo['description'])

            return todo['function'](*todo['args'])

    def processFinished(self):
        self.parent.ui.searchEdit.setEnabled(True)
        QApplication.restoreOverrideCursor()
        self.process = None
        self.parent.ui.stopButton.hide()

    @Slot()
    def stopProcess(self):
        if self.process is not None:
            self.process.stop()

    def searchRecipe(self,pattern):
        if not pattern:
            return
        self.doAction(u'Search recipe "%s"' % pattern, self.searchRecipeAction, [pattern])

    def searchRecipeAction(self, pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        backend_name = self.parent.ui.backendEdit.itemData(self.parent.ui.backendEdit.currentIndex())

        self.process = QtDo(self.weboob, self.addRecipe, fb=self.processFinished)
        self.process.do(self.app._do_complete, self.parent.getCount(), ('title'), 'iter_recipes', pattern, backends=backend_name, caps=CapRecipe)
        self.parent.ui.stopButton.show()

    def addRecipe(self, recipe):
        minirecipe = MiniRecipe(self.weboob, self.weboob[recipe.backend], recipe, self)
        self.ui.list_content.layout().insertWidget(self.ui.list_content.layout().count()-1,minirecipe)
        self.minis.append(minirecipe)

    def displayRecipe(self, recipe, backend):
        self.ui.stackedWidget.setCurrentWidget(self.ui.info_page)
        if self.current_info_widget is not None:
            self.ui.info_content.layout().removeWidget(self.current_info_widget)
            self.current_info_widget.hide()
            self.current_info_widget.deleteLater()
        wrecipe = Recipe(recipe, backend, self)
        self.ui.info_content.layout().addWidget(wrecipe)
        self.current_info_widget = wrecipe
        QApplication.restoreOverrideCursor()

    def searchId(self, id):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if '@' in id:
            backend_name = id.split('@')[1]
            id = id.split('@')[0]
        else:
            backend_name = None
        for backend in self.weboob.iter_backends():
            if (backend_name and backend.name == backend_name) or not backend_name:
                recipe = backend.get_recipe(id)
                if recipe:
                    self.doAction('Recipe "%s"' % recipe.title, self.displayRecipe, [recipe, backend])
        QApplication.restoreOverrideCursor()


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, app, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.app = app
        self.minis = []
        self.current_info_widget = None

        # search history is a list of patterns which have been searched
        history_path = os.path.join(self.weboob.workdir, 'qcookboob_history')
        qc = HistoryCompleter(history_path, self)
        qc.load()
        qc.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.searchEdit.setCompleter(qc)

        self.ui.searchEdit.returnPressed.connect(self.search)
        self.ui.idEdit.returnPressed.connect(self.searchId)

        count = self.config.get('settings', 'maxresultsnumber')
        self.ui.countSpin.setValue(int(count))
        showT = self.config.get('settings', 'showthumbnails')
        self.ui.showTCheck.setChecked(showT == '1')

        self.ui.stopButton.hide()

        self.ui.actionBackends.triggered.connect(self.backendsConfig)
        q = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Q), self)
        q.activated.connect(self.close)
        n = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageDown), self)
        n.activated.connect(self.nextTab)
        p = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageUp), self)
        p.activated.connect(self.prevTab)
        w = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_W), self)
        w.activated.connect(self.closeCurrentTab)

        l = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_L), self)
        l.activated.connect(self.ui.searchEdit.setFocus)
        l.activated.connect(self.ui.searchEdit.selectAll)

        self.ui.resultsTab.tabCloseRequested.connect(self.closeTab)

        self.loadBackendsList()

        if self.ui.backendEdit.count() == 0:
            self.backendsConfig()

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapRecipe, ), self)
        if bckndcfg.run():
            self.loadBackendsList()

    def loadBackendsList(self):
        model = BackendListModel(self.weboob)
        model.addBackends()
        self.ui.backendEdit.setModel(model)

        current_backend = self.config.get('settings', 'backend')
        idx = self.ui.backendEdit.findData(current_backend)
        if idx >= 0:
            self.ui.backendEdit.setCurrentIndex(idx)

        if self.ui.backendEdit.count() == 0:
            self.ui.searchEdit.setEnabled(False)
        else:
            self.ui.searchEdit.setEnabled(True)

    def getCount(self):
        num = self.ui.countSpin.value()
        if num == 0:
            return None
        else:
            return num

    @Slot(int)
    def closeTab(self, index):
        if self.ui.resultsTab.widget(index) != 0:
            self.ui.resultsTab.removeTab(index)

    @Slot()
    def closeCurrentTab(self):
        self.closeTab(self.ui.resultsTab.currentIndex())

    @Slot()
    def prevTab(self):
        index = self.ui.resultsTab.currentIndex() - 1
        size = self.ui.resultsTab.count()
        if size != 0:
            self.ui.resultsTab.setCurrentIndex(index % size)

    @Slot()
    def nextTab(self):
        index = self.ui.resultsTab.currentIndex() + 1
        size = self.ui.resultsTab.count()
        if size != 0:
            self.ui.resultsTab.setCurrentIndex(index % size)

    def newTab(self, txt, backend, recipe=None):
        id = ''
        if recipe is not None:
            id = recipe.id
        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, txt)
        new_res.searchId('%s@%s'%(id,backend.NAME))

    @Slot()
    def search(self):
        pattern = self.ui.searchEdit.text()
        self.ui.searchEdit.completer().addString(pattern)

        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, pattern)
        self.ui.resultsTab.setCurrentWidget(new_res)
        new_res.searchRecipe(pattern)
        self.ui.stopButton.clicked.connect(new_res.stopProcess)

    @Slot()
    def searchId(self):
        id = self.ui.idEdit.text()
        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, id)
        self.ui.resultsTab.setCurrentWidget(new_res)
        new_res.searchId(id)


    def closeEvent(self, ev):
        self.config.set('settings', 'backend', self.ui.backendEdit.itemData(
            self.ui.backendEdit.currentIndex()))
        self.ui.searchEdit.completer().save()
        self.config.set('settings', 'maxresultsnumber', self.ui.countSpin.value())

        self.config.save()
        ev.accept()
