# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Hébert
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


from weboob.capabilities.travel import ICapTravel
from weboob.tools.application import BaseApplication

import conic
import gtk
import hildon
from logging import debug


__all__ = ['Masstransit']


class MasstransitHildon():
    "hildon interface"

    def connect_event(self, connection, event=None, c=None, d=None):
        debug("DBUS-DEBUG a: %s,  b:%s, c:%s,d: %s" % (connection, event, c, d))
        status = event.get_status()
        if status == conic.STATUS_CONNECTED:
            self.connected = True
            if self.touch_selector_entry_filled == False:
                debug("connected, now fill")
                self.fill_touch_selector_entry()
            if self.refresh_in_progress:
                self.refresh()
        elif status == conic.STATUS_DISCONNECTED:
            self.connected = False

    def __init__(self, weboob):
        self.touch_selector_entry_filled = False
        self.refresh_in_progress = False
        self.connected = False
        self.weboob = weboob
        self.connection = conic.Connection()
        self.connection.connect("connection-event", self.connect_event)
        self.connection.set_property("automatic-connection-events", True)
        self.connection.request_connection(conic.CONNECT_FLAG_NONE)

        main_window = hildon.Window()
        main_window.set_title("Horaires des Prochains Trains")
        main_window.connect("destroy", self.on_main_window_destroy)

        self.refresh_button = hildon.Button(
            gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            hildon.BUTTON_ARRANGEMENT_HORIZONTAL,
            "Actualiser"
            )

        self.refresh_button.set_sensitive(False)
        self.refresh_button.connect("clicked", self.on_refresh_button_clicked)
       
        self.retour_button = hildon.Button(
            gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            hildon.BUTTON_ARRANGEMENT_HORIZONTAL,
            "Retour"
            )

        self.retour_button.set_sensitive(False)
        self.retour_button.connect("clicked", self.on_retour_button_clicked)

        self.treestore = gtk.TreeStore(str, str, str, str, str)
        treeview = gtk.TreeView(self.treestore)


        treeview.append_column(
            gtk.TreeViewColumn(
                'Train',
                gtk.CellRendererText(),
                text=0
            ))

        treeview.append_column(
            gtk.TreeViewColumn(
                'Horaire',
                gtk.CellRendererText(),
                text=1
            ))

        treeview.append_column(
            gtk.TreeViewColumn(
                'Destination',
                gtk.CellRendererText(),
                text=2
            ))
        treeview.append_column(
            gtk.TreeViewColumn(
                'Voie',
                gtk.CellRendererText(),
                text=3
            ))
       
        treeview.append_column(
            gtk.TreeViewColumn(
                'Information',
                gtk.CellRendererText(),
                text=4
            ))

   
        self.combo_source = hildon.TouchSelectorEntry(text=True)
        self.combo_dest = hildon.TouchSelectorEntry(text=True)

        self.picker_button_source = hildon.PickerButton(
            gtk.HILDON_SIZE_AUTO,
            hildon.BUTTON_ARRANGEMENT_VERTICAL)

        self.picker_button_dest = hildon.PickerButton(
            gtk.HILDON_SIZE_AUTO,
            hildon.BUTTON_ARRANGEMENT_VERTICAL
            )

        self.picker_button_source.set_sensitive(False)
        self.picker_button_dest.set_sensitive(False)

        self.picker_button_source.set_title("Gare de Depart")
        self.picker_button_dest.set_title("Gare d'arrivee")

        self.picker_button_source.set_selector(self.combo_source)
        self.picker_button_dest.set_selector(self.combo_dest)

        vertical_box = gtk.VBox()
        horizontal_box = gtk.HBox()
        vertical_box.pack_start(horizontal_box)
        horizontal_box.pack_start(self.picker_button_source)
        horizontal_box.pack_start(self.picker_button_dest)
        horizontal_box.pack_start(self.retour_button)
        vertical_box.pack_start(treeview)
        vertical_box.pack_start(self.refresh_button)

        main_window.add(vertical_box)
        main_window.show_all()

        self.picker_button_source.connect("value-changed",
                                          self.check_station_input,
                                          self.picker_button_source)
        self.picker_button_dest.connect("value-changed",
                                        self.check_station_input,
                                        self.picker_button_dest)

    def fill_touch_selector_entry(self):
        liste = []
       
        for backend in self.weboob.iter_backends():
            for station in backend.iter_station_search(""):
                liste.append(station.name.capitalize())

        liste.sort()

        for station in liste:
            self.combo_source.append_text(station)
            self.combo_dest.append_text(station)

        self.touch_selector_entry_filled = True
        self.picker_button_source.set_sensitive(True)

    def on_main_window_destroy(self, widget):
        "exit application at the window close"
        gtk.main_quit()

    def on_main_window_show(self, param):
        self.fill_touch_selector_entry()

    def on_retour_button_clicked(self, widget):
        "the button is clicked"
        self.refresh_in_progress = True
        col_source = self.combo_source.get_active(0)
        col_dest = self.combo_dest.get_active(0)
        self.combo_source.set_active(0, col_dest)
        self.combo_dest.set_active(0, col_source)
        self.refresh()

    def on_refresh_button_clicked(self, widget):
        "the refresh button is clicked"
        self.refresh_in_progress = True
        self.connection.request_connection(conic.CONNECT_FLAG_NONE)

    def check_station_input(self, widget, user_data):
        if self.combo_source.get_current_text() is None :
            self.picker_button_dest.set_sensitive(False)
            self.refresh_button.set_sensitive(False)
            self.retour_button.set_sensitive(False)
        else:
            self.picker_button_dest.set_sensitive(True)
            if self.combo_dest.get_current_text() is None:
                self.refresh_button.set_sensitive(False)
                self.retour_button.set_sensitive(False)
            else:
                self.refresh_button.set_sensitive(True)
                self.retour_button.set_sensitive(True)

    def refresh(self):
        "update departures"
        self.treestore.clear()
        for backend in self.weboob.iter_backends():
            for station in \
            backend.iter_station_search(self.combo_source.get_current_text()):
                for arrival in \
                backend.iter_station_search(self.combo_dest.get_current_text()):
                    for departure in \
                    backend.iter_station_departures(station.id, arrival.id):
                        self.treestore.append(None,
                                             [departure.type,
                                             departure.time,
                                             departure.arrival_station,
                                             departure.plateform,
                                             departure.information])

        self.refresh_in_progress = False


class Masstransit(BaseApplication):
    "Application Class"
    APPNAME = 'masstransit'
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Julien Hébert'

    def main(self, argv):
        "main fonction"
        self.load_modules(ICapTravel)
        MasstransitHildon(self.weboob)
        gtk.main()
