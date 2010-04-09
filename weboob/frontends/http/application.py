# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import os

from mako.lookup import TemplateLookup
import wee
from wsgiref.simple_server import make_server

from weboob.capabilities.messages import ICapMessages, ICapMessagesReply
from weboob.tools.application import BaseApplication

class HTTPApplication(BaseApplication):
    APPNAME = 'http'
    CONFIG = dict(host='localhost', port=8080)

    template_lookup = TemplateLookup(directories=['%s/templates' % os.path.dirname(__file__)],
                                     output_encoding='utf-8', encoding_errors='replace')


    def main(self, argv):
        self.load_config()
        self.weboob.load_backends()
        self.srv = make_server(self.config.get('host'), self.config.get('port'), wee.make_app())
        self.srv.serve_forever()

    @wee.get('/')
    def index(self, request):
        template = self.template_lookup.get_template('index.mako')
        return template.render().strip()

    @wee.get('/messages')
    def messages(self, request):
        template = self.template_lookup.get_template('messages.mako')
        backends = list(self.weboob.iter_backends(ICapMessages))
        return template.render(backends=backends).strip()
