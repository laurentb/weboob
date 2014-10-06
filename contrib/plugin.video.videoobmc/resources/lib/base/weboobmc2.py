#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

from weboob.tools.application.base import Application
import os
import re
import subprocess


class Weboobmc(Application):
    def __init__(self, count=10):
        Application.__init__(self)
        self.count = int(count)
        self._is_default_count = False

    def update(self):
        self.weboob.update()

    def get_backend_icon(self, module):
        minfo = self.weboob.repositories.get_module_info(module)
        return self.weboob.repositories.get_module_icon_path(minfo)

    def obj_to_filename(self, obj, dest=None, default=None):
        """
        This method can be used to get a filename from an object, using a mask
        filled by information of this object.
        All patterns are braces-enclosed, and are name of available fields in
        the object.
        :param obj: object type obj: BaseObject param dest: dest given by user (default None)
        type dest: str param default: default file mask (if not given, this is
        :'{id}-{title}.{ext}') type default: str rtype: str
        """

        if default is None:
            default = '{id}-{title}.{ext}'
        if dest is None:
            dest = '.'
        if os.path.isdir(dest):
            dest = os.path.join(dest, default)

        def repl(m):
            field = m.group(1)
            if hasattr(obj, field):
                return re.sub('[?:/]', '-', '%s' % getattr(obj, field))
            else:
                return m.group(0)

        return re.sub(r'\{(.+?)\}', repl, dest)

    def download_obj(self, obj, dest):

        def check_exec(executable):
            with open('/dev/null', 'w') as devnull:
                process = subprocess.Popen(['which', executable], stdout=devnull)
                if process.wait() != 0:
                    print('Please install "%s"' % executable)
                    return False
            return True

        dest = self.obj_to_filename(obj, dest)
        if obj.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                return 1
            args = ('rtmpdump', '-e', '-r', obj.url, '-o', dest)
        elif obj.url.startswith('mms'):
            if not check_exec('mimms'):
                return 1
            args = ('mimms', '-r', obj.url, dest)
        elif u'm3u8' == obj.ext:
            _dest, _ = os.path.splitext(dest)
            dest = u'%s.%s' % (_dest, 'mp4')
            args = ('wget',) + tuple(line for line in self.read_url(obj.url) if not line.startswith('#')) + ('-O', dest)
        else:
            if check_exec('wget'):
                args = ('wget', '-c', obj.url, '-O', dest)
            elif check_exec('curl'):
                args = ('curl', '-C', '-', obj.url, '-o', dest)
            else:
                return 1
        os.spawnlp(os.P_WAIT, args[0], *args)
