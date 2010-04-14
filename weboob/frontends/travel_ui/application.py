# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Julien Hébert

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.capabilities.travel import ICapTravel
from weboob.tools.application import BaseApplication

try:
    import hildon
except ImportError:
    raise ImportError("Unable to import hildon http://maemo.org/packages/view/python-hildon/")

import gtk

class TransilienUI():
    "hildon interface"
    def __init__(self, weboob):
        self.weboob = weboob
        self.main_window = hildon.Window()
        self.main_window.set_title("Horaires des Prochains Trains")
        self.main_window.connect("destroy", self.on_main_window_destroy)


        refresh_button = hildon.Button(
            gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            hildon.BUTTON_ARRANGEMENT_HORIZONTAL,
            "Actualiser"
            )
        retour_button = hildon.Button(
            gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            hildon.BUTTON_ARRANGEMENT_HORIZONTAL,
            "Retour"
            )
        refresh_button.connect("clicked", self.on_refresh_button_clicked)
        retour_button.connect("clicked", self.on_retour_button_clicked)

        self.treestore = gtk.TreeStore(str, str, str, str)
        self.treeview = gtk.TreeView(self.treestore)


        self.treeview.append_column(
            gtk.TreeViewColumn(
                'Train',
                gtk.CellRendererText(),
                text=0
            ))

        self.treeview.append_column(
            gtk.TreeViewColumn(
                'Horaire',
                gtk.CellRendererText(),
                text=1
            ))

        self.treeview.append_column(
            gtk.TreeViewColumn(
                'Destination',
                gtk.CellRendererText(),
                text=2
            ))
        self.treeview.append_column(
            gtk.TreeViewColumn(
                'Voie',
                gtk.CellRendererText(),
                text=3
            ))

        self.combo_source = hildon.TouchSelectorEntry(text=True)
        self.combo_dest = hildon.TouchSelectorEntry(text=True)

        liste = []

        #liste = ConfFile('/opt/masstransit/masstransit.cfg').config.items('ListeDesGares')
        for name, backend in self.weboob.iter_backends():
            for station in backend.iter_station_search(""):
                liste.append(station)

        for station in liste:
            self.combo_source.append_text(station.name.capitalize())
            self.combo_dest.append_text(station.name.capitalize())

        picker_button_source = hildon.PickerButton(
            gtk.HILDON_SIZE_AUTO,
            hildon.BUTTON_ARRANGEMENT_VERTICAL)

        picker_button_dest = hildon.PickerButton(
            gtk.HILDON_SIZE_AUTO,
            hildon.BUTTON_ARRANGEMENT_VERTICAL
            )

        picker_button_source.set_title("Gare de Depart")
        picker_button_dest.set_title("Gare d'arrivee")

        picker_button_source.set_selector(self.combo_source)
        picker_button_dest.set_selector(self.combo_dest)

        vertical_box = gtk.VBox()
        horizontal_box = gtk.HBox()
        vertical_box.pack_start(horizontal_box)
        horizontal_box.pack_start(picker_button_source)
        horizontal_box.pack_start(picker_button_dest)
        horizontal_box.pack_start(retour_button)
        vertical_box.pack_start(self.treeview)
        vertical_box.pack_start(refresh_button)

        self.main_window.add(vertical_box)
        self.main_window.show_all()

    def on_main_window_destroy(self, widget):
        "exit application at the window close"
        gtk.main_quit()

    def on_retour_button_clicked(self, widget):
        "the button is clicked"
        col_source = self.combo_source.get_active(0)
        col_dest = self.combo_dest.get_active(0)
        self.combo_source.set_active(0, col_dest)
        self.combo_dest.set_active(0, col_source)
        self.refresh()

    def on_refresh_button_clicked(self, widget):
        "the refresh button is clicked"
        self.refresh()

    def refresh(self):
        "update departures"
        self.treestore.clear()
        for name, backend in self.weboob.iter_backends():
            for station in backend.iter_station_search(self.combo_source.get_current_text()):
                for name, backend in self.weboob.iter_backends():
                    for arrival in backend.iter_station_search(self.combo_dest.get_current_text()):
                        for name, backend, in self.weboob.iter_backends():
                            for departure in backend.iter_station_departures(station.id, arrival.id):
                                self.treestore.append(None, [departure.type, departure.time, departure.arrival_station, departure.information])

class Travel(BaseApplication):
    APPNAME = 'travel'

    def main(self, argv):
        self.weboob.load_modules(ICapTravel)
        TransilienUI(self.weboob)
        gtk.main()
