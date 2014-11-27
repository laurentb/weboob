# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

import os
import codecs

from PyQt4.QtCore import SIGNAL, Qt, QStringList
from PyQt4.QtGui import QApplication, QCompleter, QFrame, QShortcut, QKeySequence

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.cinema import CapCinema
from weboob.capabilities.torrent import CapTorrent
from weboob.capabilities.subtitle import CapSubtitle
from weboob.tools.application.qt import QtMainWindow, QtDo
from weboob.tools.application.qt.backendcfg import BackendCfg

from weboob.applications.suboob.suboob import LANGUAGE_CONV
from weboob.applications.qcineoob.ui.main_window_ui import Ui_MainWindow
from weboob.applications.qcineoob.ui.result_ui import Ui_Result

from .minimovie import MiniMovie
from .miniperson import MiniPerson
from .minitorrent import MiniTorrent
from .minisubtitle import MiniSubtitle
from .movie import Movie
from .person import Person
from .torrent import Torrent
from .subtitle import Subtitle


class Result(QFrame):
    def __init__(self, weboob, app, parent=None):
        QFrame.__init__(self, parent)
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
        self.connect(self.ui.backButton, SIGNAL("clicked()"), self.doBack)
        self.ui.backButton.hide()

    def doAction(self, description, fun, args):
        ''' Call fun with args as arguments
        and save it in the action history
        '''
        self.ui.currentActionLabel.setText(description)
        if self.action_history['last_action'] is not None:
            self.action_history['action_list'].append(self.action_history['last_action'])
            self.ui.backButton.setToolTip(self.action_history['last_action']['description'])
            self.ui.backButton.show()
        self.action_history['last_action'] = {'function': fun, 'args': args, 'description': description}
        return fun(*args)

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
            return todo['function'](*todo['args'])

    def castingAction(self, backend_name, id, role):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.process = QtDo(self.weboob, self.addPerson, fb=self.processFinished)
        self.process.do('iter_movie_persons', id, role, backends=backend_name, caps=CapCinema)
        self.parent.ui.stopButton.show()

    def moviesInCommonAction(self, backend_name, id1, id2):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        for a_backend in self.weboob.iter_backends():
            if (backend_name and a_backend.name == backend_name):
                backend = a_backend
                person1 = backend.get_person(id1)
                person2 = backend.get_person(id2)

        lid1 = []
        for p in backend.iter_person_movies_ids(id1):
            lid1.append(p)
        lid2 = []
        for p in backend.iter_person_movies_ids(id2):
            lid2.append(p)

        inter = list(set(lid1) & set(lid2))

        chrono_list = []
        for common in inter:
            movie = backend.get_movie(common)
            movie.backend = backend_name
            role1 = movie.get_roles_by_person_id(person1.id)
            role2 = movie.get_roles_by_person_id(person2.id)
            if (movie.release_date != NotAvailable):
                year = movie.release_date.year
            else:
                year = '????'
            movie.short_description = '(%s) %s as %s ; %s as %s'%(year , person1.name, ', '.join(role1), person2.name, ', '.join(role2))
            i = 0
            while (i<len(chrono_list) and movie.release_date != NotAvailable and
                  (chrono_list[i].release_date == NotAvailable or year > chrono_list[i].release_date.year)):
                i += 1
            chrono_list.insert(i, movie)

        for movie in chrono_list:
            self.addMovie(movie)

        self.processFinished()

    def personsInCommonAction(self, backend_name, id1, id2):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        for a_backend in self.weboob.iter_backends():
            if (backend_name and a_backend.name == backend_name):
                backend = a_backend
                movie1 = backend.get_movie(id1)
                movie2 = backend.get_movie(id2)

        lid1 = []
        for p in backend.iter_movie_persons_ids(id1):
            lid1.append(p)
        lid2 = []
        for p in backend.iter_movie_persons_ids(id2):
            lid2.append(p)

        inter = list(set(lid1) & set(lid2))

        for common in inter:
            person = backend.get_person(common)
            person.backend = backend_name
            role1 = movie1.get_roles_by_person_id(person.id)
            role2 = movie2.get_roles_by_person_id(person.id)
            person.short_description = '%s in %s ; %s in %s'%(', '.join(role1), movie1.original_title, ', '.join(role2), movie2.original_title)
            self.addPerson(person)

        self.processFinished()

    def filmographyAction(self, backend_name, id, role):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.process = QtDo(self.weboob, self.addMovie, fb=self.processFinished)
        self.process.do('iter_person_movies', id, role, backends=backend_name, caps=CapCinema)
        self.parent.ui.stopButton.show()

    def search(self, tosearch, pattern, lang):
        if tosearch == 'person':
            self.searchPerson(pattern)
        elif tosearch == 'movie':
            self.searchMovie(pattern)
        elif tosearch == 'torrent':
            self.searchTorrent(pattern)
        elif tosearch == 'subtitle':
            self.searchSubtitle(lang, pattern)

    def searchMovie(self, pattern):
        if not pattern:
            return
        self.doAction(u'Search movie "%s"' % pattern, self.searchMovieAction, [pattern])

    def searchMovieAction(self, pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        backend_name = str(self.parent.ui.backendEdit.itemData(self.parent.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addMovie, fb=self.processFinished)
        #self.process.do('iter_movies', pattern, backends=backend_name, caps=CapCinema)
        self.process.do(self.app._do_complete, self.parent.getCount(), ('original_title'), 'iter_movies', pattern, backends=backend_name, caps=CapCinema)
        self.parent.ui.stopButton.show()

    def stopProcess(self):
        self.process.process.finish_event.set()

    def addMovie(self, movie):
        minimovie = MiniMovie(self.weboob, self.weboob[movie.backend], movie, self)
        self.ui.list_content.layout().insertWidget(self.ui.list_content.layout().count()-1,minimovie)
        self.minis.append(minimovie)

    def displayMovie(self, movie, backend):
        self.ui.stackedWidget.setCurrentWidget(self.ui.info_page)
        if self.current_info_widget is not None:
            self.ui.info_content.layout().removeWidget(self.current_info_widget)
            self.current_info_widget.hide()
            self.current_info_widget.deleteLater()
        wmovie = Movie(movie, backend, self)
        self.ui.info_content.layout().addWidget(wmovie)
        self.current_info_widget = wmovie
        QApplication.restoreOverrideCursor()

    def searchPerson(self, pattern):
        if not pattern:
            return
        self.doAction(u'Search person "%s"' % pattern, self.searchPersonAction, [pattern])

    def searchPersonAction(self, pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        backend_name = str(self.parent.ui.backendEdit.itemData(self.parent.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addPerson, fb=self.processFinished)
        #self.process.do('iter_persons', pattern, backends=backend_name, caps=CapCinema)
        self.process.do(self.app._do_complete, self.parent.getCount(), ('name'), 'iter_persons', pattern, backends=backend_name, caps=CapCinema)
        self.parent.ui.stopButton.show()

    def addPerson(self, person):
        miniperson = MiniPerson(self.weboob, self.weboob[person.backend], person, self)
        self.ui.list_content.layout().insertWidget(self.ui.list_content.layout().count()-1,miniperson)
        self.minis.append(miniperson)

    def displayPerson(self, person, backend):
        self.ui.stackedWidget.setCurrentWidget(self.ui.info_page)
        if self.current_info_widget is not None:
            self.ui.info_content.layout().removeWidget(self.current_info_widget)
            self.current_info_widget.hide()
            self.current_info_widget.deleteLater()
        wperson = Person(person, backend, self)
        self.ui.info_content.layout().addWidget(wperson)
        self.current_info_widget = wperson
        QApplication.restoreOverrideCursor()

    def searchTorrent(self, pattern):
        if not pattern:
            return
        self.doAction(u'Search torrent "%s"' % pattern, self.searchTorrentAction, [pattern])

    def searchTorrentAction(self, pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        backend_name = str(self.parent.ui.backendEdit.itemData(self.parent.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addTorrent, fb=self.processFinished)
        #self.process.do('iter_torrents', pattern, backends=backend_name, caps=CapTorrent)
        self.process.do(self.app._do_complete, self.parent.getCount(), ('name'), 'iter_torrents', pattern, backends=backend_name, caps=CapTorrent)
        self.parent.ui.stopButton.show()

    def processFinished(self):
        self.parent.ui.searchEdit.setEnabled(True)
        QApplication.restoreOverrideCursor()
        self.process = None
        self.parent.ui.stopButton.hide()

    def addTorrent(self, torrent):
        minitorrent = MiniTorrent(self.weboob, self.weboob[torrent.backend], torrent, self)
        self.ui.list_content.layout().insertWidget(self.ui.list_content.layout().count()-1,minitorrent)
        self.minis.append(minitorrent)

    def displayTorrent(self, torrent, backend):
        self.ui.stackedWidget.setCurrentWidget(self.ui.info_page)
        if self.current_info_widget is not None:
            self.ui.info_content.layout().removeWidget(self.current_info_widget)
            self.current_info_widget.hide()
            self.current_info_widget.deleteLater()
        wtorrent = Torrent(torrent, backend, self)
        self.ui.info_content.layout().addWidget(wtorrent)
        self.current_info_widget = wtorrent

    def searchSubtitle(self, lang, pattern):
        if not pattern:
            return
        self.doAction(u'Search subtitle "%s" (lang:%s)' % (pattern, lang), self.searchSubtitleAction, [lang, pattern])

    def searchSubtitleAction(self, lang, pattern):
        self.ui.stackedWidget.setCurrentWidget(self.ui.list_page)
        for mini in self.minis:
            self.ui.list_content.layout().removeWidget(mini)
            mini.hide()
            mini.deleteLater()

        self.minis = []
        self.parent.ui.searchEdit.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        backend_name = str(self.parent.ui.backendEdit.itemData(self.parent.ui.backendEdit.currentIndex()).toString())

        self.process = QtDo(self.weboob, self.addSubtitle, fb=self.processFinished)
        #self.process.do('iter_subtitles', lang, pattern, backends=backend_name, caps=CapSubtitle)
        self.process.do(self.app._do_complete, self.parent.getCount(), ('name'), 'iter_subtitles', lang, pattern, backends=backend_name, caps=CapSubtitle)
        self.parent.ui.stopButton.show()

    def addSubtitle(self, subtitle):
        minisubtitle = MiniSubtitle(self.weboob, self.weboob[subtitle.backend], subtitle, self)
        self.ui.list_content.layout().insertWidget(self.ui.list_content.layout().count()-1,minisubtitle)
        self.minis.append(minisubtitle)

    def displaySubtitle(self, subtitle, backend):
        self.ui.stackedWidget.setCurrentWidget(self.ui.info_page)
        if self.current_info_widget is not None:
            self.ui.info_content.layout().removeWidget(self.current_info_widget)
            self.current_info_widget.hide()
            self.current_info_widget.deleteLater()
        wsubtitle = Subtitle(subtitle, backend, self)
        self.ui.info_content.layout().addWidget(wsubtitle)
        self.current_info_widget = wsubtitle

    def searchId(self, id, stype):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        title_field = 'name'
        if stype == 'movie':
            cap = CapCinema
            title_field = 'original_title'
        elif stype == 'person':
            cap = CapCinema
        elif stype == 'torrent':
            cap = CapTorrent
        elif stype == 'subtitle':
            cap = CapSubtitle
        if '@' in id:
            backend_name = id.split('@')[1]
            id = id.split('@')[0]
        else:
            backend_name = None
        for backend in self.weboob.iter_backends():
            if backend.has_caps(cap) and ((backend_name and backend.name == backend_name) or not backend_name):
                exec('object = backend.get_%s(id)' % (stype))
                if object:
                    func_display = 'self.display' + stype[0].upper() + stype[1:]
                    exec("self.doAction('Details of %s \"%%s\"' %% object.%s, %s, [object, backend])" %
                            (stype, title_field, func_display))
        QApplication.restoreOverrideCursor()


class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, app, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob
        self.app = app

        # search history is a list of patterns which have been searched
        self.search_history = self.loadSearchHistory()
        self.updateCompletion()

        self.connect(self.ui.searchEdit, SIGNAL("returnPressed()"), self.search)
        self.connect(self.ui.idEdit, SIGNAL("returnPressed()"), self.searchId)
        self.connect(self.ui.typeCombo, SIGNAL("currentIndexChanged(QString)"), self.typeComboChanged)

        count = self.config.get('settings', 'maxresultsnumber')
        self.ui.countSpin.setValue(int(count))
        showT = self.config.get('settings', 'showthumbnails')
        self.ui.showTCheck.setChecked(showT == '1')

        self.connect(self.ui.stopButton, SIGNAL("clicked()"), self.stopProcess)
        self.ui.stopButton.hide()

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)
        q = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Q), self)
        self.connect(q, SIGNAL("activated()"), self.close)
        n = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageDown), self)
        self.connect(n, SIGNAL("activated()"), self.nextTab)
        p = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageUp), self)
        self.connect(p, SIGNAL("activated()"), self.prevTab)
        w = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_W), self)
        self.connect(w, SIGNAL("activated()"), self.closeCurrentTab)

        l = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_L), self)
        self.connect(l, SIGNAL("activated()"), self.ui.searchEdit.setFocus)
        self.connect(l, SIGNAL("activated()"), self.ui.searchEdit.selectAll)

        self.connect(self.ui.resultsTab, SIGNAL("tabCloseRequested(int)"), self.closeTab)

        self.loadBackendsList()

        if self.ui.backendEdit.count() == 0:
            self.backendsConfig()

        langs = sorted(LANGUAGE_CONV.keys())
        for lang in langs:
            self.ui.langCombo.addItem(lang)
        self.ui.langCombo.hide()
        self.ui.langLabel.hide()

    def stopProcess(self):
        self.ui.resultsTab.currentWidget().stopProcess()

    def closeTab(self, index):
        if self.ui.resultsTab.widget(index) != 0:
            tabToClose = self.ui.resultsTab.widget(index)
            self.ui.resultsTab.removeTab(index)
            del(tabToClose)

    def closeCurrentTab(self):
        self.closeTab(self.ui.resultsTab.currentIndex())

    def prevTab(self):
        index = self.ui.resultsTab.currentIndex() - 1
        size = self.ui.resultsTab.count()
        if size != 0:
            self.ui.resultsTab.setCurrentIndex(index % size)

    def nextTab(self):
        index = self.ui.resultsTab.currentIndex() + 1
        size = self.ui.resultsTab.count()
        if size != 0:
            self.ui.resultsTab.setCurrentIndex(index % size)

    def newTab(self, txt, backend, person=None, movie=None, torrent=None, subtitle=None):
        id = ''
        if person is not None:
            id = person.id
            stype = 'person'
        elif movie is not None:
            id = movie.id
            stype = 'movie'
        elif subtitle is not None:
            id = subtitle.id
            stype = 'subtitle'
        elif torrent is not None:
            id = torrent.id
            stype = 'torrent'
        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, txt)
        new_res.searchId(id, stype)

    def search(self):
        pattern = unicode(self.ui.searchEdit.text())
        # arbitrary max number of completion word
        if len(self.search_history) > 50:
            self.search_history.pop(0)
        if pattern not in self.search_history:
            self.search_history.append(pattern)
            self.updateCompletion()

        tosearch = unicode(self.ui.typeCombo.currentText())
        lang = unicode(self.ui.langCombo.currentText())
        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, pattern)
        self.ui.resultsTab.setCurrentWidget(new_res)
        new_res.search(tosearch, pattern, lang)

    def searchId(self):
        id = unicode(self.ui.idEdit.text())
        stype = unicode(self.ui.idTypeCombo.currentText())
        new_res = Result(self.weboob, self.app, self)
        self.ui.resultsTab.addTab(new_res, id)
        self.ui.resultsTab.setCurrentWidget(new_res)
        new_res.searchId(id, stype)

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapCinema, CapTorrent, CapSubtitle,), self)
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

    def loadSearchHistory(self):
        ''' Return search string history list loaded from history file
        '''
        result = []
        history_path = os.path.join(self.weboob.workdir, 'qcineoob_history')
        if os.path.exists(history_path):
            f = codecs.open(history_path, 'r', 'utf-8')
            conf_hist = f.read()
            f.close()
            if conf_hist is not None and conf_hist.strip() != '':
                result = conf_hist.strip().split('\n')
        return result

    def saveSearchHistory(self):
        ''' Save search history in history file
        '''
        if len(self.search_history) > 0:
            history_path = os.path.join(self.weboob.workdir, 'qcineoob_history')
            f = codecs.open(history_path, 'w', 'utf-8')
            f.write('\n'.join(self.search_history))
            f.close()

    def updateCompletion(self):
        qc = QCompleter(QStringList(self.search_history), self)
        qc.setCaseSensitivity(Qt.CaseInsensitive)
        self.ui.searchEdit.setCompleter(qc)

    def typeComboChanged(self, value):
        if unicode(value) == 'subtitle':
            self.ui.langCombo.show()
            self.ui.langLabel.show()
        else:
            self.ui.langCombo.hide()
            self.ui.langLabel.hide()

    def getCount(self):
        num = self.ui.countSpin.value()
        if num == 0:
            return None
        else:
            return num

    def closeEvent(self, ev):
        self.config.set('settings', 'backend', str(self.ui.backendEdit.itemData(
            self.ui.backendEdit.currentIndex()).toString()))
        self.saveSearchHistory()
        self.config.set('settings', 'maxresultsnumber', self.ui.countSpin.value())
        self.config.set('settings', 'showthumbnails', '1' if self.ui.showTCheck.isChecked() else '0')

        self.config.save()
        ev.accept()
