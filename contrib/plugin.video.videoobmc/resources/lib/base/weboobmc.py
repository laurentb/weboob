#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import re
import subprocess
import simplejson as json

if hasattr(sys.modules["__main__"], "common_xbmc"):
    common_xbmc = sys.modules["__main__"].common_xbmc
else:
    import common_xbmc


class Weboobmc():
    def __init__(self, count=10):
        self.count = count

    def update(self):
        #weboob-config update
        self._call_weboob('weboob-config', 'update')

    def _call_weboob(self, application, command, options={}, argument=""):
        if '-n' not in options.keys():
            options['-n'] = self.count
        _opt = " ".join(["%s %s " % (k, v) for k, v in options.items()])
        _cmd = "%s %s %s %s" % (application, _opt, command, argument)
        #print _cmd.encode('utf-8')
        return subprocess.check_output(_cmd, shell=True)

    def _json_call_weboob(self, application, command, options={}, argument=""):
        options['-f'] = 'json'
        try:
            result = self._call_weboob(application, command, options, argument)
            m = re.search(r"(\[{.+\}])", result)
            if m:
                result = u'%s' % m.group(1)
                #print result
                return json.loads(result) if result else []
        except subprocess.CalledProcessError as e:
            common_xbmc.display_error(" Error while calling weboob : %s " % e)

    def get_loaded_backends(self, caps):
        #weboob-config list ICapVideo -f json
        backends = self._json_call_weboob('weboob-config', 'list', argument=caps)
        for backend in backends:
            if "_enabled=0" not in backend['Configuration']:
                yield backend['Name'] #  , self.get_backend_icon(backend['Module'])

    def get_backend_icon(self, module):
        if 'WEBOOB_DATADIR' in os.environ:
            datadir = os.environ['WEBOOB_DATADIR']
        elif 'WEBOOB_WORKDIR' in os.environ:
            datadir = os.environ['WEBOOB_WORKDIR']
        else:
            datadir = os.path.join(os.environ.get('XDG_DATA_HOME',
                                                  os.path.join(os.path.expanduser('~'), '.local', 'share')
                                                  ), 'weboob')
        icons_dir = os.path.join(datadir, 'icons')

        return os.path.join(icons_dir, '%s.png' % module)

    def is_category(self, obj):
        return 'split_path' in obj.keys()
