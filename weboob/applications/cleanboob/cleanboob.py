# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hébert
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


from weboob.capabilities.messages import ICapMessages
from weboob.tools.application.repl import ReplApplication


__all__ = ['CleanBoob']


class CleanBoob(ReplApplication):
    APPNAME = 'CleanBoob'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2011-2012 Julien Hébert'
    DESCRIPTION = "CleanBoob is a console application to extract article from website."
    CAPS = ICapMessages

    def main(self, argv):
        for backend, content in self.do('get_thread', argv[1]):
            #self.format(content)
            self.format(content.root)
        return 0
