# -*- coding: utf-8 -*-

# Copyright(C) 2012  Lucien Loiseau
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


import sys

import os
import sys
import codecs
import locale

from weboob.capabilities.translate import ICapTranslate
from weboob.tools.application.repl import ReplApplication

__all__ = ['Translaboob']

class Translaboob(ReplApplication):
    APPNAME = 'translaboob'
    VERSION = '0.c'
    COPYRIGHT = 'Copyright(C) 2012 Lucien Loiseau'
    DESCRIPTION = 'Console application to translate text from one language to another'
    CAPS = ICapTranslate
    
    def main(self, argv):
        return ReplApplication.main(self, argv)

    def do_translate(self, line):
        lan_from, lan_to, text = self.parse_command_args(line, 3, 1)
        """
        translate <FROM> <TO> <TEXT>
        translate from one language to another, 
        <FROM> : source language
        <TO>   : destination language
        <TEXT> : language to translate, standart input if - is given
        """
        if not text or text == '-':
            text = self.acquire_input()

        print "from : "+lan_from+" to : "+lan_to 
        print "<source>"
        print text
        print "</source>"

        for backend, translation  in self.do('translate', lan_from, lan_to, text):
          print "<translation "+backend.name+">"
          print translation
          print "</translation>"
          







