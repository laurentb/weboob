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


from weboob.capabilities.translate import ICapTranslate
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Translaboob']


class TranslationFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'text')

    def format_obj(self, obj, alias):
        return u'%s* %s%s\n\t%s' % (self.BOLD, obj.backend, self.NC, obj.text.replace('\n', '\n\t'))

class XmlTranslationFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'text')

    def start_format(self, **kwargs):
        if 'source' in kwargs:
            self.output('<source>\n%s\n</source>' % kwargs['source'])

    def format_obj(self, obj, alias):
        return u'<translation %s>\n%s\n</translation>' % (obj.backend, obj.text)

class Translaboob(ReplApplication):
    APPNAME = 'translaboob'
    VERSION = '0.c'
    COPYRIGHT = 'Copyright(C) 2012 Lucien Loiseau'
    DESCRIPTION = 'Console application to translate text from one language to another'
    CAPS = ICapTranslate
    EXTRA_FORMATTERS = {'translation': TranslationFormatter,
                        'xmltrans':    XmlTranslationFormatter,
                       }
    COMMANDS_FORMATTERS = {'translate': 'translation',
                          }

    def do_translate(self, line):
        """
        translate FROM TO [TEXT]

        Translate from one language to another.
        * FROM : source language
        * TO   : destination language
        * TEXT : language to translate, standart input if - is given
        """

        lan_from, lan_to, text = self.parse_command_args(line, 3, 2)

        if not text or text == '-':
            text = self.acquire_input()

        self.start_format(source=text)
        for backend, translation  in self.do('translate', lan_from, lan_to, text):
            self.format(translation)
        self.flush()
