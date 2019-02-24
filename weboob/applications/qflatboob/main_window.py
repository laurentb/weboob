# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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

from PyQt5.QtGui import QImage, QPixmap, QIcon, QBrush, QColor
from PyQt5.QtWidgets import QLabel, QListWidgetItem
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from weboob.tools.compat import range
from weboob.tools.application.qt5 import QtMainWindow, QtDo, HTMLDelegate
from weboob.tools.application.qt5.backendcfg import BackendCfg
from weboob.capabilities.housing import CapHousing, Query, City, POSTS_TYPES
from weboob.capabilities.base import NotLoaded, NotAvailable, empty

from .ui.main_window_ui import Ui_MainWindow
from .query import QueryDialog


class HousingListWidgetItem(QListWidgetItem):
    def __init__(self, housing, *args, **kwargs):
        super(HousingListWidgetItem, self).__init__(*args, **kwargs)
        self.housing = housing
        self.read = True

    def __lt__(self, other):
        return '%s%s' % (self.read, self.housing.price_per_meter) < \
               '%s%s' % (other.read, other.housing.price_per_meter)

    def setAttrs(self, storage):
        text = u'<h2>%s</h2>' % self.housing.title

        _area = u'%.0fm²' % self.housing.area if self.housing.area else self.housing.area

        text += u'<i>%s — %s — %s%s — %.0f %s/m2 (%s)</i>' % (
            self.housing.date.strftime('%Y-%m-%d') if self.housing.date else 'Unknown',
            _area,
            self.housing.cost,
            self.housing.currency,
            self.housing.price_per_meter,
            self.housing.currency,
            self.housing.backend)
        text += u'<br />%s' % self.housing.text.strip()
        text += u'<br /><font color="#008800">%s</font>' % storage.get('notes', self.housing.fullid, default='').strip().replace('\n', '<br />')
        self.setText(text)

        if self.housing.fullid not in storage.get('read'):
            self.setBackground(QBrush(QColor(200, 200, 255)))
            self.read = False
        elif self.housing.fullid in storage.get('bookmarks'):
            self.setBackground(QBrush(QColor(255, 200, 200)))
        elif self.background().color() != QColor(0, 0, 0):
            self.setBackground(QBrush())


class MainWindow(QtMainWindow):
    def __init__(self, config, storage, weboob, app, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.storage = storage
        self.weboob = weboob
        self.app = app
        self.process = None
        self.housing = None
        self.displayed_photo_idx = 0
        self.process_photo = {}
        self.process_bookmarks = {}

        self.ui.housingsList.setItemDelegate(HTMLDelegate())
        self.ui.housingFrame.hide()

        self.ui.actionBackends.triggered.connect(self.backendsConfig)
        self.ui.queriesList.currentIndexChanged.connect(self.queryChanged)
        self.ui.addQueryButton.clicked.connect(self.addQuery)
        self.ui.editQueryButton.clicked.connect(self.editQuery)
        self.ui.removeQueryButton.clicked.connect(self.removeQuery)
        self.ui.bookmarksButton.clicked.connect(self.displayBookmarks)
        self.ui.housingsList.currentItemChanged.connect(self.housingSelected)
        self.ui.previousButton.clicked.connect(self.previousClicked)
        self.ui.nextButton.clicked.connect(self.nextClicked)
        self.ui.bookmark.stateChanged.connect(self.bookmarkChanged)

        self.reloadQueriesList()
        self.refreshHousingsList()

        if self.weboob.count_backends() == 0:
            self.backendsConfig()

        if len(self.config.get('queries')) == 0:
            self.addQuery()

    def closeEvent(self, event):
        self.setHousing(None)
        QtMainWindow.closeEvent(self, event)

    @Slot()
    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (CapHousing,), self)
        if bckndcfg.run():
            pass

    def reloadQueriesList(self, select_name=None):
        self.ui.queriesList.currentIndexChanged.disconnect(self.queryChanged)
        self.ui.queriesList.clear()
        for name in self.config.get('queries', default={}):
            self.ui.queriesList.addItem(name)
            if name == select_name:
                self.ui.queriesList.setCurrentIndex(len(self.ui.queriesList)-1)
        self.ui.queriesList.currentIndexChanged.connect(self.queryChanged)

        if select_name is not None:
            self.queryChanged()

    @Slot()
    def removeQuery(self):
        name = self.ui.queriesList.itemText(self.ui.queriesList.currentIndex())
        queries = self.config.get('queries')
        queries.pop(name, None)
        self.config.set('queries', queries)
        self.config.save()

        self.reloadQueriesList()
        self.queryChanged()

    @Slot()
    def editQuery(self):
        name = self.ui.queriesList.itemText(self.ui.queriesList.currentIndex())
        self.addQuery(name)

    @Slot()
    def addQuery(self, name=None):
        querydlg = QueryDialog(self.weboob, self)
        if name is not None:
            query = self.config.get('queries', name)
            querydlg.ui.nameEdit.setText(name)
            querydlg.ui.nameEdit.setEnabled(False)
            for c in query['cities']:
                city = City(c['id'])
                city.backend = c['backend']
                city.name = c['name']
                item = querydlg.buildCityItem(city)
                querydlg.ui.citiesList.addItem(item)

            querydlg.ui.typeBox.setCurrentIndex(int(query.get('type', 0)))
            querydlg.ui.areaMin.setValue(query['area_min'])
            querydlg.ui.areaMax.setValue(query['area_max'])
            querydlg.ui.costMin.setValue(query['cost_min'])
            querydlg.ui.costMax.setValue(query['cost_max'])
            querydlg.selectComboValue(querydlg.ui.nbRooms, query['nb_rooms'])

        if querydlg.exec_():
            name = querydlg.ui.nameEdit.text()
            query = {}
            query['type'] = querydlg.ui.typeBox.currentIndex()
            query['cities'] = []
            for i in range(len(querydlg.ui.citiesList)):
                item = querydlg.ui.citiesList.item(i)
                city = item.data(Qt.UserRole)
                query['cities'].append({'id': city.id, 'backend': city.backend, 'name': city.name})
            query['area_min'] = querydlg.ui.areaMin.value()
            query['area_max'] = querydlg.ui.areaMax.value()
            query['cost_min'] = querydlg.ui.costMin.value()
            query['cost_max'] = querydlg.ui.costMax.value()
            try:
                query['nb_rooms'] = int(querydlg.ui.nbRooms.itemText(querydlg.ui.nbRooms.currentIndex()))
            except ValueError:
                query['nb_rooms'] = 0
            self.config.set('queries', name, query)
            self.config.save()

            self.reloadQueriesList(name)

    @Slot(int)
    def queryChanged(self, i=None):
        self.refreshHousingsList()

    def refreshHousingsList(self):
        name = self.ui.queriesList.itemText(self.ui.queriesList.currentIndex())
        q = self.config.get('queries', name)

        if q is None:
            return q

        self.ui.housingsList.clear()
        self.ui.queriesList.setEnabled(False)
        self.ui.bookmarksButton.setEnabled(False)

        query = Query()
        query.type = list(POSTS_TYPES)[-q.get('type', 1)]
        query.cities = []
        for c in q['cities']:
            city = City(c['id'])
            city.backend = c['backend']
            city.name = c['name']
            query.cities.append(city)

        query.area_min = int(q['area_min']) or None
        query.area_max = int(q['area_max']) or None
        query.cost_min = int(q['cost_min']) or None
        query.cost_max = int(q['cost_max']) or None
        query.nb_rooms = int(q['nb_rooms']) or None

        self.process = QtDo(self.weboob, self.addHousing, fb=self.addHousingEnd)
        self.process.do(self.app._do_complete, 20, None, 'search_housings', query)

    @Slot()
    def displayBookmarks(self):
        self.ui.housingsList.clear()
        self.ui.queriesList.setEnabled(False)
        self.ui.queriesList.setCurrentIndex(-1)
        self.ui.bookmarksButton.setEnabled(False)

        self.processes = {}
        for id in self.storage.get('bookmarks'):
            _id, backend_name = id.rsplit('@', 1)
            self.process_bookmarks[id] = QtDo(self.weboob, self.addHousing, fb=self.addHousingEnd)
            self.process_bookmarks[id].do('get_housing', _id, backends=backend_name)

    def addHousingEnd(self):
        self.ui.queriesList.setEnabled(True)
        self.ui.bookmarksButton.setEnabled(True)
        self.process = None

    def addHousing(self, housing):
        if not housing:
            return

        item = HousingListWidgetItem(housing)
        item.setAttrs(self.storage)

        if housing.photos is NotLoaded:
            process = QtDo(self.weboob, lambda c: self.setPhoto(c, item))
            process.do('fillobj', housing, ['photos'], backends=housing.backend)
            self.process_photo[housing.id] = process
        elif housing.photos is not NotAvailable and len(housing.photos) > 0:
            if not self.setPhoto(housing, item):
                photo = housing.photos[0]
                process = QtDo(self.weboob, lambda p: self.setPhoto(housing, item))
                process.do('fillobj', photo, ['data'], backends=housing.backend)
                self.process_photo[housing.id] = process

        self.ui.housingsList.addItem(item)

        if housing.fullid in self.process_bookmarks:
            self.process_bookmarks.pop(housing.fullid)

    @Slot(QListWidgetItem, QListWidgetItem)
    def housingSelected(self, item, prev):
        if item is not None:
            housing = item.housing
            self.ui.queriesFrame.setEnabled(False)

            read = set(self.storage.get('read'))
            read.add(housing.fullid)
            self.storage.set('read', list(read))
            self.storage.save()

            self.process = QtDo(self.weboob, self.gotHousing)
            self.process.do('fillobj', housing, backends=housing.backend)

        else:
            housing = None

        self.setHousing(housing)

        if prev:
            prev.setAttrs(self.storage)

    def setPhoto(self, housing, item):
        if not housing:
            return False

        try:
            self.process_photo.pop(housing.id, None)
        except KeyError:
            pass

        if not housing.photos:
            return False

        img = None
        for photo in housing.photos:
            if photo.data:
                img = QImage.fromData(photo.data)
                break

        if img:
            item.setIcon(QIcon(QPixmap.fromImage(img)))
            return True

        return False

    def setHousing(self, housing, nottext='Loading...'):
        if self.housing is not None:
            self.saveNotes()

        self.housing = housing

        if self.housing is None:
            self.ui.housingFrame.hide()
            return

        self.ui.housingFrame.show()

        self.display_photo()

        self.ui.bookmark.setChecked(housing.fullid in self.storage.get('bookmarks'))

        self.ui.titleLabel.setText('<h1>%s</h1>' % housing.title)
        _area = u'%.2f m²' % housing.area if housing.area else housing.area
        self.ui.areaLabel.setText(u'%s' % _area)
        self.ui.costLabel.setText(u'%s %s' % (housing.cost, housing.currency))
        self.ui.pricePerMeterLabel.setText(u'%.2f %s/m²' % (housing.price_per_meter, housing.currency))
        self.ui.dateLabel.setText(housing.date.strftime('%Y-%m-%d') if housing.date else nottext)
        self.ui.phoneLabel.setText(housing.phone or nottext)
        self.ui.locationLabel.setText(housing.location or nottext)
        self.ui.stationLabel.setText(housing.station or nottext)
        self.ui.urlLabel.setText('<a href="%s">%s</a>' % (housing.url or nottext, housing.url or nottext))

        text = housing.text.replace('\n', '<br/>') if housing.text else nottext
        self.ui.descriptionEdit.setText(text)

        self.ui.notesEdit.setText(self.storage.get('notes', housing.fullid, default=''))

        while self.ui.detailsFrame.layout().count() > 0:
            child = self.ui.detailsFrame.layout().takeAt(0)
            child.widget().hide()
            child.widget().deleteLater()

        if housing.details:
            for key, value in housing.details.items():
                if empty(value):
                    continue
                label = QLabel(value)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
                self.ui.detailsFrame.layout().addRow('<b>%s:</b>' % key, label)

    def gotHousing(self, housing):
        self.setHousing(housing, nottext='')
        self.ui.queriesFrame.setEnabled(True)
        self.process = None

    @Slot(int)
    def bookmarkChanged(self, state):
        bookmarks = set(self.storage.get('bookmarks'))
        if state == Qt.Checked:
            bookmarks.add(self.housing.fullid)
        elif self.housing.fullid in bookmarks:
            bookmarks.remove(self.housing.fullid)
        self.storage.set('bookmarks', list(bookmarks))
        self.storage.save()

    def saveNotes(self):
        if not self.housing:
            return
        txt = self.ui.notesEdit.toPlainText().strip()
        if len(txt) > 0:
            self.storage.set('notes', self.housing.fullid, txt)
        else:
            self.storage.delete('notes', self.housing.fullid)
        self.storage.save()

    @Slot()
    def previousClicked(self):
        if not self.housing.photos or len(self.housing.photos) == 0:
            return
        self.displayed_photo_idx = (self.displayed_photo_idx - 1) % len(self.housing.photos)
        self.display_photo()

    @Slot()
    def nextClicked(self):
        if not self.housing.photos or len(self.housing.photos) == 0:
            return
        self.displayed_photo_idx = (self.displayed_photo_idx + 1) % len(self.housing.photos)
        self.display_photo()

    def display_photo(self):
        if not self.housing.photos:
            self.ui.photosFrame.hide()
            return

        if self.displayed_photo_idx >= len(self.housing.photos):
            self.displayed_photo_idx = len(self.housing.photos) - 1
        if self.displayed_photo_idx < 0:
            self.ui.photosFrame.hide()
            return

        self.ui.photosFrame.show()

        photo = self.housing.photos[self.displayed_photo_idx]
        if photo.data:
            data = photo.data
            if photo.id in self.process_photo:
                self.process_photo.pop(photo.id)
        else:
            self.process_photo[photo.id] = QtDo(self.weboob, lambda p: self.display_photo())
            self.process_photo[photo.id].do('fillobj', photo, ['data'], backends=self.housing.backend)

            return

        img = QImage.fromData(data)
        img = img.scaledToWidth(self.width()/3)

        self.ui.photoLabel.setPixmap(QPixmap.fromImage(img))
        if photo.url is not NotLoaded:
            text = '<a href="%s">%s</a>' % (photo.url, photo.url)
            self.ui.photoUrlLabel.setText(text)
