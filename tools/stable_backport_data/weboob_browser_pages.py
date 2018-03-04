
from weboob.browser.pages import *

from .weboob_browser_exceptions import LoggedOut


class LoginPage(object):
    def on_load(self):
        if not self.browser.logging_in:
            raise LoggedOut()

        super(LoginPage, self).on_load()

