# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from PyQt4.QtCore import SIGNAL

from weboob.capabilities.cinema import ICapCinema
from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg

from weboob.applications.qcineoob.ui.main_window_ui import Ui_MainWindow

from .minimovie import MiniMovie
from .miniperson import MiniPerson
from .movie import Movie
from .person import Person

class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.minimovies = []
        self.minipersons = []
        self.current_movie_widget = None
        self.current_person_widget = None

        self.history = {'last_action':None,'action_list':[]}
        self.connect(self.ui.backButton, SIGNAL("clicked()"), self.doBack)
        self.ui.backButton.setDisabled(True)

        self.connect(self.ui.searchEdit, SIGNAL("returnPressed()"), self.search)

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)

        self.loadBackendsList()

        if self.ui.backendEdit.count() == 0:
            self.backendsConfig()

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapCinema,), self)
        if bckndcfg.run():
            self.loadBackendsList()

    def loadBackendsList(self):
        self.ui.backendEdit.clear()
        for i, backend in enumerate(self.weboob.iter_backends()):
            if i == 0:
                self.ui.backendEdit.addItem('All backends', '')
            self.ui.backendEdit.addItem(backend.name, backend.name)
            if backend.name == self.config.get('settings', 'backend'):
                self.ui.backendEdit.setCurrentIndex(i+1)

        if self.ui.backendEdit.count() == 0:
            self.ui.searchEdit.setEnabled(False)
        else:
            self.ui.searchEdit.setEnabled(True)

    def doAction(self, fun, args):
        if self.history['last_action'] != None:
            self.history['action_list'].append(self.history['last_action'])
            self.ui.backButton.setDisabled(False)
        self.history['last_action'] = {'function':fun,'args':args}
        return fun(*args)

    def doBack(self):
        if len(self.history['action_list']) > 0:
            todo = self.history['action_list'].pop()
            self.history['last_action'] = todo
            if len(self.history['action_list']) == 0:
                self.ui.backButton.setDisabled(True)
            return todo['function'](*todo['args'])

    def castingAction(self, id, role):
        self.ui.stackedWidget.setCurrentWidget(self.ui.person_list_page)
        for miniperson in self.minipersons:
            self.ui.person_list_content.layout().removeWidget(miniperson)
            miniperson.hide()
            miniperson.deleteLater()

        self.minipersons = []
        self.ui.searchEdit.setEnabled(False)

        backend_name = str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addPerson)
        self.process.do('iter_movie_persons', id, role, backends=backend_name)

    def search(self):
        tosearch = self.ui.typeCombo.currentText()
        if tosearch == 'person':
            self.searchPerson()
        elif tosearch == 'movie':
            self.searchMovie()

    def searchMovie(self):
        pattern = unicode(self.ui.searchEdit.text())
        if not pattern:
            return
        self.doAction(self.searchMovieAction,[pattern])

    def searchMovieAction(self,pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.movie_list_page)
        for minimovie in self.minimovies:
            self.ui.movie_list_content.layout().removeWidget(minimovie)
            minimovie.hide()
            minimovie.deleteLater()

        self.minimovies = []
        self.ui.searchEdit.setEnabled(False)

        backend_name = str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addMovie)
        self.process.do('iter_movies', pattern, backends=backend_name)

    def addMovie(self, backend, movie):
        if not backend:
            self.ui.searchEdit.setEnabled(True)
            self.process = None
            return
        minimovie = MiniMovie(self.weboob, backend, movie, self)
        self.ui.movie_list_content.layout().addWidget(minimovie)
        self.minimovies.append(minimovie)

    def displayMovie(self, movie):
        self.ui.stackedWidget.setCurrentWidget(self.ui.movie_info_page)
        if self.current_movie_widget != None:
            self.ui.movie_info_content.layout().removeWidget(self.current_movie_widget)
            self.current_movie_widget.hide()
            self.current_movie_widget.deleteLater()
        wmovie = Movie(movie,self)
        self.ui.movie_info_content.layout().addWidget(wmovie)
        self.current_movie_widget = wmovie

    def searchPerson(self):
        pattern = unicode(self.ui.searchEdit.text())
        if not pattern:
            return
        self.doAction(self.searchPersonAction,[pattern])

    def searchPersonAction(self,pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.person_list_page)
        for miniperson in self.minipersons:
            self.ui.person_list_content.layout().removeWidget(miniperson)
            miniperson.hide()
            miniperson.deleteLater()

        self.minipersons = []
        self.ui.searchEdit.setEnabled(False)

        backend_name = str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addPerson)
        self.process.do('iter_persons', pattern, backends=backend_name)

    def addPerson(self, backend, person):
        if not backend:
            self.ui.searchEdit.setEnabled(True)
            self.process = None
            return
        miniperson = MiniPerson(self.weboob, backend, person, self)
        self.ui.person_list_content.layout().addWidget(miniperson)
        self.minipersons.append(miniperson)

    def displayPerson(self, person):
        self.ui.stackedWidget.setCurrentWidget(self.ui.person_info_page)
        if self.current_person_widget != None:
            self.ui.person_info_content.layout().removeWidget(self.current_person_widget)
            self.current_person_widget.hide()
            self.current_person_widget.deleteLater()
        wperson = Person(person,self)
        self.ui.person_info_content.layout().addWidget(wperson)
        self.current_person_widget = wperson

    def closeEvent(self, ev):
        self.config.set('settings', 'backend', str(self.ui.backendEdit.itemData(self.ui.backendEdit.currentIndex()).toString()))
        self.config.save()
        ev.accept()
