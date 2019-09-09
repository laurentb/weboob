#!/usr/bin/env python3

import logging
import os
from signal import SIG_DFL, SIGINT, signal
from threading import Thread

from gi.repository import AppIndicator3 as appindicator
from gi.repository import GObject, Gtk, Notify
from pkg_resources import resource_filename

from weboob.capabilities import UserError
from weboob.capabilities.bank import Account, CapBank
from weboob.core import CallErrors, Weboob
from weboob.exceptions import BrowserForbidden, BrowserIncorrectPassword, BrowserSSLError, BrowserUnavailable
from weboob.tools.application.base import MoreResultsAvailable
from weboob.tools.compat import unicode

PING_FREQUENCY = 3600  # seconds
APPINDICATOR_ID = "boobank_indicator"
PATH = os.path.realpath(__file__)


def create_image_menu_item(label, image):
    item = Gtk.ImageMenuItem()
    img = Gtk.Image()
    img.set_from_file(os.path.abspath(resource_filename('boobank_indicator.data', image)))
    item.set_image(img)
    item.set_label(label)
    item.set_always_show_image(True)
    return item


class BoobankTransactionsChecker(Thread):
    def __init__(self, weboob, menu, account):
        Thread.__init__(self)
        self.weboob = weboob
        self.menu = menu
        self.account = account

    def run(self):
        account_history_menu = Gtk.Menu()

        for tr in self.weboob.do('iter_history', self.account, backends=self.account.backend):
            label = u'%s - %s: %s%s' % (tr.date, tr.label, tr.amount, self.account.currency_text)
            image = "green_light.png" if tr.amount > 0 else "red_light.png"
            transaction_item = create_image_menu_item(label, image)
            account_history_menu.append(transaction_item)
            transaction_item.show()

        self.menu.set_submenu(account_history_menu)


class BoobankChecker():
    def __init__(self):
        self.ind = appindicator.Indicator.new(APPINDICATOR_ID,
                                              os.path.abspath(resource_filename('boobank_indicator.data',
                                                                                'indicator-boobank.png')),
                                              appindicator.IndicatorCategory.APPLICATION_STATUS)

        self.menu = Gtk.Menu()
        self.ind.set_menu(self.menu)

        logging.basicConfig()
        if 'weboob_path' in os.environ:
            self.weboob = Weboob(os.environ['weboob_path'])
        else:
            self.weboob = Weboob()

        self.weboob.load_backends(CapBank)

    def clean_menu(self, menu):
        for i in menu.get_children():
            submenu = i.get_submenu()
            if submenu:
                self.clean_menu(i)
            menu.remove(i)

    def check_boobank(self):
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.clean_menu(self.menu)

        total = 0
        currency = ''
        threads = []

        try:
            for account in self.weboob.do('iter_accounts'):

                balance = account.balance
                if account.coming:
                    balance += account.coming

                if account.type != Account.TYPE_LOAN:
                    total += balance
                    image = "green_light.png" if balance > 0 else "red_light.png"
                else:
                    image = "personal-loan.png"

                currency = account.currency_text
                label = "%s: %s%s" % (account.label, balance, account.currency_text)
                account_item = create_image_menu_item(label, image)
                thread = BoobankTransactionsChecker(self.weboob, account_item, account)
                thread.start()
                threads.append(thread)

        except CallErrors as errors:
            self.bcall_errors_handler(errors)

        for thread in threads:
            thread.join()

        for thread in threads:
            self.menu.append(thread.menu)
            thread.menu.show()

        if len(self.menu.get_children()) == 0:
            Notify.Notification.new('<b>Boobank</b>',
                                    'No Bank account found\n Please configure one by running boobank',
                                    'notification-message-im').show()

        sep = Gtk.SeparatorMenuItem()
        self.menu.append(sep)
        sep.show()

        total_item = Gtk.MenuItem("%s: %s%s" % ("Total", total, currency))
        self.menu.append(total_item)
        total_item.show()

        sep = Gtk.SeparatorMenuItem()
        self.menu.append(sep)
        sep.show()

        btnQuit = Gtk.ImageMenuItem()
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_QUIT, Gtk.IconSize.BUTTON)
        btnQuit.set_image(image)
        btnQuit.set_label('Quit')
        btnQuit.set_always_show_image(True)
        btnQuit.connect("activate", self.quit)
        self.menu.append(btnQuit)
        btnQuit.show()

    def quit(self, widget):
        Gtk.main_quit()

    def bcall_errors_handler(self, errors):
        """
        Handler for the CallErrors exception.
        """
        self.ind.set_status(appindicator.IndicatorStatus.ATTENTION)
        for backend, error, backtrace in errors.errors:
            notify = True
            if isinstance(error, BrowserIncorrectPassword):
                msg = 'invalid login/password.'
            elif isinstance(error, BrowserSSLError):
                msg = '/!\ SERVER CERTIFICATE IS INVALID /!\\'
            elif isinstance(error, BrowserForbidden):
                msg = unicode(error) or 'Forbidden'
            elif isinstance(error, BrowserUnavailable):
                msg = unicode(error)
                if not msg:
                    msg = 'website is unavailable.'
            elif isinstance(error, NotImplementedError):
                notify = False
            elif isinstance(error, UserError):
                msg = unicode(error)
            elif isinstance(error, MoreResultsAvailable):
                notify = False
            else:
                msg = unicode(error)

            if notify:
                Notify.Notification.new('<b>Error Boobank: %s</b>' % backend.name,
                                        msg,
                                        'notification-message-im').show()

    def main(self):
        self.check_boobank()
        GObject.timeout_add(PING_FREQUENCY * 1000, self.check_boobank)
        Gtk.main()


def main():
    signal(SIGINT, SIG_DFL)
    GObject.threads_init()
    Notify.init('boobank_indicator')
    BoobankChecker().main()


if __name__ == "__main__":
    main()
