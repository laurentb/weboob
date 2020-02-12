# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Christophe Benz
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

from __future__ import print_function

# start with:
# set PYTHONPATH=D:\Dropbox\Projets\boomoney
# python d:\Dropbox\Projets\boomoney\scripts\boomoney -N


from threading import Thread, Lock
import copy
import sys
from io import StringIO
import os
import re
import subprocess
import datetime
from optparse import OptionGroup

import shutil
from colorama import init, Fore, Style

from weboob.tools.compat import unicode
from weboob.exceptions import BrowserUnavailable
from weboob.capabilities.bank import AccountNotFound, AccountType
from weboob.applications.boobank import Boobank
from weboob.applications.boobank.boobank import OfxFormatter
from weboob.tools.application.formatters.simple import SimpleFormatter


__all__ = ['Boomoney']

printMutex = Lock()
numMutex = Lock()
backupMutex = Lock()


class MoneyOfxFormatter(OfxFormatter):
    def start_format(self, **kwargs):
        self.seen = set()
        # MSMoney only supports CHECKING accounts
        t = kwargs['account'].type
        kwargs['account'].type = AccountType.CHECKING
        super(MoneyOfxFormatter, self).start_format(**kwargs)
        kwargs['account'].type = t

    def format_obj(self, obj, alias):
        cat = obj.category
        obj.category = obj.raw
        result = super(MoneyOfxFormatter, self).format_obj(obj, alias)
        obj.category = cat
        return result

    def output(self, formatted):
        if self.outfile != sys.stdout:
            self.outfile.write(formatted + os.linesep)
        else:
            super(MoneyOfxFormatter, self).output(formatted)


class ListFormatter(SimpleFormatter):
    def output(self, formatted):
        if self.outfile != sys.stdout:
            self.outfile.write(formatted + os.linesep)
        else:
            super(ListFormatter, self).output(formatted)


class BoobankNoBackend(Boobank):
    EXTRA_FORMATTERS = {'ops_list': MoneyOfxFormatter}
    COMMANDS_FORMATTERS = {'history': 'ops_list'}

    def load_default_backends(self):
        pass

    def bcall_error_handler(self, backend, error, backtrace):
        handled = False
        if isinstance(error, BrowserUnavailable):
            handled = True
            self.error = True
        if isinstance(error, AccountNotFound):
            handled = True
            self.error = True
        if isinstance(error, NotImplementedError):
            handled = True
            self.error = False
        if not handled:
            self.error = True
            self.weboob.logger.error("Unsupported error %s in BoobankNoBackend" % type(error))
        return super(Boobank, self).bcall_error_handler(backend, error, backtrace)


class HistoryThread(Thread):
    def __init__(self, boomoney, account):
        Thread.__init__(self)
        self.boomoney = boomoney
        self.account = account
        self.disabled = boomoney.config.get(account, 'disabled', default=False)
        self.date_min = boomoney.config.get(account, 'date_min', default='')
        self.last_date = boomoney.config.get(account, 'last_date', default='')

    @property
    def label(self):
        if self.account in self.boomoney.labels:
            return self.boomoney.labels[self.account]
        else:
            return self.boomoney.config.get(self.account, 'label', default='')

    def dumpTransaction(self, output, fields, field):
        output.write("<STMTTRN>\n")
        if "DTUSER" in field and "DTPOSTED" in field and not field["DTUSER"] == field["DTPOSTED"]:
            # the payment date is a deferred payment
            # MSMoney takes DTPOSTED, which is the payment date
            # I prefer to have the date of the operation, so I set DTPOSTED
            # as DTUSER
            field["DTPOSTED"] = field["DTUSER"]
        for f in fields.strip().split(" "):
            value = field[f]
            if f == "NAME":
                if value == "":
                    # MSMoney does not support empty NAME field
                    value = "</NAME>"
                else:
                    # MSMoney does not support NAME field longer than 64
                    value = value[:64]
            output.write("<%s>%s\n" % (f, value))
        output.write("</STMTTRN>\n")

    def run(self):

        now = datetime.datetime.now().strftime("%Y-%m-%d")

        if self.boomoney.options.force:
            from_date = self.date_min
        else:
            from_date = self.last_date

        if from_date >= now:
            self.boomoney.print(Style.BRIGHT + "%s (%s): Last import date is %s, no need to import again..." % (
                self.account, self.label, self.last_date) + Style.RESET_ALL)
            return

        boobank = self.boomoney.createBoobank(self.account)
        if boobank is None:
            with numMutex:
                self.boomoney.importIndex = self.boomoney.importIndex + 1
            return

        boobank.stderr = StringIO()
        boobank.stdout = boobank.stderr
        id, backend = self.account.split("@")
        module_name, foo = boobank.weboob.backends_config.get_backend(backend)
        moduleHandler = "%s.bat" % os.path.join(os.path.dirname(self.boomoney.getMoneyFile()), module_name)
        self.boomoney.logger.info("Starting history of %s (%s)..." % (self.account, self.label))

        MAX_RETRIES = 3
        count = 0
        found = False
        content = ''
        boobank.error = False
        while count <= MAX_RETRIES and not (found and not boobank.error):
            boobank.options.outfile = StringIO()
            boobank.error = False

            # executing history command
            boobank.onecmd("history " + self.account + " " + from_date)

            if count > 0:
                self.boomoney.logger.info("Retrying %s (%s)... %i/%i" % (self.account, self.label, count, MAX_RETRIES))
            found = re.match(r'^OFXHEADER:100', boobank.options.outfile.getvalue())
            if found and not boobank.error:
                content = boobank.options.outfile.getvalue()
            boobank.options.outfile.close()
            count = count + 1
        if content == '':
            # error occurred
            with numMutex:
                self.boomoney.importIndex = self.boomoney.importIndex + 1
                index = self.boomoney.importIndex
            self.boomoney.logger.error("(%i/%i) %s (%s): %saborting after %i retries.%s" % (
                index, len(self.boomoney.threads),
                self.account,
                self.label,
                Fore.RED + Style.BRIGHT,
                MAX_RETRIES,
                Style.RESET_ALL))
            return

        # postprocessing of the ofx content to match MSMoney expectations
        content = re.sub(r'<BALAMT>Not loaded', r'<BALAMT></BALAMT>', content)
        input = StringIO(content)
        output = StringIO()
        field = {}
        fields = ' '
        for line in input:
            if re.match(r'^OFXHEADER:100', line):
                inTransaction = False
            if re.match(r'^<STMTTRN>', line):
                inTransaction = True
            if not inTransaction:
                output.write(line)
            if re.match(r'^</STMTTRN>', line):
                # MSMoney expects CHECKNUM instead of NAME for CHECK transactions
                if "TRNTYPE" in field and field["TRNTYPE"] == "CHECK":
                    if "NAME" in field and unicode(field["NAME"]).isnumeric():
                        field["CHECKNUM"] = field["NAME"]
                        del field["NAME"]
                        fields = fields.replace(' NAME ', ' CHECKNUM ')

                # go through specific backend process if any
                IGNORE = False
                NEW = None
                origfields = fields
                origfield = field.copy()
                if os.path.exists(moduleHandler):
                    self.boomoney.logger.info("Calling backend handler %s..." % moduleHandler)
                    # apply the transformations, in the form
                    # field_NAME=...
                    # field_MEMO=...
                    # field=...

                    cmd = 'cmd /C '
                    for f in field:
                        value = field[f]
                        cmd = cmd + 'set field_%s=%s& ' % (f, value)

                    cmd = cmd + '"' + moduleHandler + '"'
                    result = subprocess.check_output(cmd.encode(sys.stdout.encoding))

                    for line in re.split(r'[\r\n]+', result):
                        if not line == "":
                            f, value = line.split("=", 1)

                            if f == "IGNORE":
                                IGNORE = True
                            elif f == "NEW":
                                NEW = value
                            elif f.startswith('field_'):
                                f = re.sub(r'^field_', '', f)
                                if value == "":
                                    if f in field:
                                        del field[f]
                                    fields = re.sub(" " + f + " ", " ", fields)
                                else:
                                    field[f] = value
                                    if f not in fields.strip().split(" "):
                                        # MSMoney does not like when CHECKNUM is after MEMO
                                        if f == "CHECKNUM":
                                            fields = fields.replace("MEMO", "CHECKNUM MEMO")
                                        else:
                                            fields = fields + f + " "

                if not IGNORE:
                    # dump transaction
                    self.dumpTransaction(output, fields, field)

                    if NEW is not None:
                        for n in NEW.strip().split(" "):
                            fields = origfields
                            field = origfield.copy()
                            field["FITID"] = origfield["FITID"] + "_" + n
                            for line in re.split(r'[\r\n]+', result):
                                if not line == "":
                                    f, value = line.split("=", 1)

                                    if f.startswith(n + '_field_'):
                                        f = re.sub(r'^.*_field_', '', f)
                                        field[f] = value
                                        if f not in fields.strip().split(" "):
                                            fields = fields + f + " "
                            # dump secondary transaction
                            self.dumpTransaction(output, fields, field)

                inTransaction = False
            if inTransaction:
                if re.match(r'^<STMTTRN>', line):
                    field = {}
                    fields = ' '
                else:
                    t = line.split(">", 1)
                    v = re.split(r'[\r\n]', t[1])
                    field[t[0][1:]] = v[0]
                    fields = fields + t[0][1:] + ' '

        ofxcontent = output.getvalue()
        stderrcontent = boobank.stderr.getvalue()
        input.close()
        output.close()
        boobank.stderr.close()

        if self.boomoney.options.display:
            self.boomoney.print(Style.BRIGHT + ofxcontent + Style.RESET_ALL)

        nbTransactions = ofxcontent.count('<STMTTRN>')

        # create ofx file
        fname = re.sub(r'[^\w@\. ]', '_', self.account + " " + self.label)
        ofxfile = os.path.join(self.boomoney.getDownloadsPath(), fname + ".ofx")
        with open(ofxfile, "w") as ofx_file:
            ofx_file.write(re.sub(r'\r\n', r'\n', ofxcontent.encode(sys.stdout.encoding)))

        with numMutex:
            self.boomoney.write(stderrcontent)
            self.boomoney.importIndex = self.boomoney.importIndex + 1
            index = self.boomoney.importIndex
        if not (self.boomoney.options.noimport or nbTransactions == 0):
            self.boomoney.backupIfNeeded()
        with printMutex:
            if self.boomoney.options.noimport or nbTransactions == 0:
                if nbTransactions == 0:
                    print(Style.BRIGHT + '(%i/%i) %s (%s) (no transaction).' % (
                        index, len(self.boomoney.threads),
                        self.account,
                        self.label
                    ) + Style.RESET_ALL)
                else:
                    print(Fore.GREEN + Style.BRIGHT + '(%i/%i) %s (%s) (%i transaction(s)).' % (
                        index, len(self.boomoney.threads),
                        self.account,
                        self.label,
                        nbTransactions
                    ) + Style.RESET_ALL)
            else:
                # import into money
                print(Fore.GREEN + Style.BRIGHT + '(%i/%i) Importing "%s" into MSMoney (%i transaction(s))...' % (
                    index, len(self.boomoney.threads),
                    ofxfile,
                    nbTransactions
                ) + Style.RESET_ALL)
        if not self.boomoney.options.noimport:
            if nbTransactions > 0:
                subprocess.check_call('"%s" %s' % (
                    os.path.join(self.boomoney.getMoneyPath(), "mnyimprt.exe"),
                    ofxfile))
            self.last_date = now


class Boomoney(Boobank):
    APPNAME = 'boomoney'
    VERSION = '2.0'
    COPYRIGHT = 'Copyright(C) 2018-YEAR Bruno Chabrier'
    DESCRIPTION = "Console application that imports bank accounts into Microsoft Money"
    SHORT_DESCRIPTION = "import bank accounts into Microsoft Money"

    EXTRA_FORMATTERS = {'list': ListFormatter}
    COMMANDS_FORMATTERS = {'list': 'list'}

    def __init__(self):
        super(Boobank, self).__init__()
        self.importIndex = 0
        application_options = OptionGroup(self._parser, 'Boomoney Options')
        application_options.add_option('-F', '--force', action='store_true', help='forces the retrieval of transactions (10 maximum), otherwise retrieves only the transactions newer than the previous retrieval date')
        application_options.add_option('-A', '--account', help='retrieves only the specified account. By default, all accounts are retrieved')
        application_options.add_option('-N', '--noimport', action='store_true', help='no import. Generates the files, but they are not imported in MSMoney. Last import dates are not modified')
        application_options.add_option('-D', '--display', action='store_true', help='displays the generated OFX file')
        application_options.add_option('-P', '--parallel', action='store_true', help='retrieves all accounts in parallel instead of one by one (experimental)')
        self._parser.add_option_group(application_options)
        self.labels = dict()

    def print(self, *args):
        with printMutex:
            print(*args)

    def write(self, *args):
        with printMutex:
            sys.stdout.write(*args)

    def createBoobank(self, account):
        accountId, backendName = account.split("@")

        if not self.weboob.backends_config.backend_exists(backendName):
            self.logger.warning("Unknown backend '%s' of account '%s' (not found in backends)" % (backendName, account))
            return None

        # create a Boobank instance
        boobank = BoobankNoBackend()
        boobank.options = copy.copy(self.options)

        moduleName = self.weboob.backends_config._read_config().get(backendName, "_module")
        module = self.weboob.modules_loader.loaded[moduleName]
        backend = self.weboob.backend_instances[backendName]

        params = {}
        for param in backend.config:
            params[param] = backend.config[param].get()
        dedicatedBackendInstanceName = "backend instance for " + account
        boobank.APP_NAME = "boobank app for " + account
        instance = module.create_instance(self.weboob, dedicatedBackendInstanceName, params, storage=boobank.create_storage())

        boobank.enabled_backends = set()
        boobank.enabled_backends.add(instance)
        boobank.weboob.backend_instances[dedicatedBackendInstanceName] = instance

        boobank.selected_fields = ["$full"]
        boobank.formatter = self.formatter

        boobank._interactive = False
        return boobank

    def getHistory(self, account):
        t = HistoryThread(self, account)
        return t

    def getDownloadsPath(self):
        if not hasattr(self, '_downloadsPath'):
            s = subprocess.check_output(
                'reg query "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders" /v "{374DE290-123F-4565-9164-39C4925E467B}"')
            t = re.sub(r'^(.|\r|\n)+REG_EXPAND_SZ\s+([^\n\r]+)(.|\r|\n)*$', r'\2', s)
            self._downloadsPath = os.path.expandvars(t).decode('CP850')
        return self._downloadsPath

    def getMoneyPath(self):
        if not hasattr(self, '_moneyPath'):
            s = subprocess.check_output('reg query HKEY_CLASSES_ROOT\\money\\Shell\\Open\\Command /ve')
            t = re.sub(r'^(.|\r|\n)+REG_SZ\s+([^\n\r]+)(.|\r|\n)*$', r'\2', s)
            self._moneyPath = os.path.expandvars(os.path.dirname(t)).decode('CP850')
        return self._moneyPath

    def getMoneyFile(self):
        if not hasattr(self, '_moneyFile'):
            s = subprocess.check_output('reg query HKEY_CURRENT_USER\\Software\\Microsoft\\Money\\14.0 /v CurrentFile')
            t = re.sub(r'^(.|\r|\n)+REG_SZ\s+([^\n\r]+)(.|\r|\n)*$', r'\2', s)
            self._moneyFile = os.path.expandvars(t).decode('CP850')
        return self._moneyFile

    def backupIfNeeded(self):
        if not (hasattr(self, '_backupDone') and self._backupDone):
            with backupMutex:
                # redo the test in mutual exclusion
                if not (hasattr(self, '_backupDone') and self._backupDone):
                    file = self.getMoneyFile()
                    filename = os.path.splitext(os.path.basename(file))[0]
                    dir = os.path.dirname(file)
                    self.print(Fore.YELLOW + Style.BRIGHT + "Creating backup of %s..." % file + Style.RESET_ALL)
                    target = os.path.join(dir, filename + datetime.datetime.now().strftime("_%Y_%m_%d_%H%M%S.mny"))
                    shutil.copy2(file, target)
                    self._backupDone = True

    def save_config(self):
        for t in self.threads:
            self.config.set(t.account, 'label', t.label)
            self.config.set(t.account, 'disabled', t.disabled)
            self.config.set(t.account, 'date_min', t.date_min)
            self.config.set(t.account, 'last_date', t.last_date)

        self.config.save()

    def getList(self):
        self.onecmd("select id label")
        self.options.outfile = StringIO()
        self.onecmd("list")
        listContent = self.options.outfile.getvalue()
        self.options.outfile.close()
        self.print(Style.BRIGHT + "Accounts:%s----------%s%s----------" % (
            os.linesep,
            os.linesep,
            listContent) + Style.RESET_ALL)
        for line in listContent.split(os.linesep):
            if not line == "":
                idspec, labelspec = line.split("\t")
                notusedid, id = idspec.split("=")
                notusedlabel, label = labelspec.split("=")
                self.labels[id] = label

    def checkNew(self):
        new = set()
        for account in self.labels:
            if account not in self.config.config.sections():
                new.add(HistoryThread(self, account))
        return new

    def main(self, argv):

        init()

        self.load_config()

        self._interactive = False

        self.threads = set()

        self.logger.info(self.config.config.sections())
        for account in self.config.config.sections():
            if self.options.account == None or account == self.options.account:
                if self.config.config.getboolean(account, "disabled") == False:
                    # time.sleep(3)
                    self.threads.add(self.getHistory(account))

        if self.options.parallel:
            self.print(Fore.MAGENTA + Style.BRIGHT + "Starting %i history threads..." % len(self.threads) + Style.RESET_ALL)
            for t in self.threads:
                t.start()
            self.getList()
            for t in self.checkNew():
                t.start()
                self.threads.add(t)
            self.print(Fore.MAGENTA + Style.BRIGHT + "Waiting for %i threads to complete..." % len(self.threads) + Style.RESET_ALL)
            for t in self.threads:
                t.join()
        else:
            self.getList()
            for t in self.checkNew():
                self.threads.add(t)
            for t in self.threads:
                t.start()
                t.join()

        self.save_config()
        return
