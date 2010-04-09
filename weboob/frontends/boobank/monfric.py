#!/usr/bin/env python

from weboob import Weboob
from weboob.capabilities.bank import ICapBank
from weboob.tools.application import BaseApplication
from weboob.tools.config.yamlconfig import YamlConfig

class MonFric(BaseApplication):
    APPNAME = 'monfric'
    CONFIG = dict(backend='', account='')

    def main(self, argv):
        self.load_config()
        requested_backend = self.config.get('backend')
        requested_account = self.config.get('account')
        if not requested_backend or not requested_account :
            raise Exception(u'Please provide backend and account keys in config file "%s"' % self.config.path)
        self.weboob.load_backends(ICapBank)
        for account in self.weboob.backends[requested_backend].iter_accounts():
            if account.label == requested_account:
                print account.balance
