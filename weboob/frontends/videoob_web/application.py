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
from mako.runtime import Context
from routes import Mapper
from StringIO import StringIO
from webob.dec import wsgify
from webob import exc
from webob import Response
from wsgiref.simple_server import make_server

from weboob.capabilities.video import ICapVideoProvider
from weboob.tools.application import BaseApplication


__all__ = ['VideoobWeb']


template_lookup = TemplateLookup(directories=['%s/templates' % os.path.dirname(__file__)],
                                 output_encoding='utf-8', encoding_errors='replace')


class VideoobWeb(BaseApplication):
    APPNAME = 'videoob-web'
    CONFIG = dict(host='localhost', port=8080)

    @wsgify
    def make_app(self, req):
        map = Mapper()
        map.connect('index', '/', method='index')

        results = map.routematch(environ=req.environ)
        if not results:
            return exc.HTTPNotFound()
        match, route = results
        req.urlvars = ((), match)
        kwargs = match.copy()
        method = kwargs.pop('method')
        return getattr(self, method)(req, **kwargs)

    def main(self, argv):
        self.load_config()
        self.weboob.load_modules(ICapVideoProvider)
        print 'Web server created. Listening on http://%s:%s' % (
            self.config.get('host'), int(self.config.get('port')))
        srv = make_server(self.config.get('host'), int(self.config.get('port')), self.make_app)
        srv.serve_forever()

    def index(self, req):
        c = {}
        nsfw = req.params.get('nsfw')
        nsfw = False if not nsfw or nsfw == '0' else True
        q = req.params.get('q', u'')
        c['form_data'] = dict(q=q)
        c['results'] = {}
        if q:
            for backend in self.weboob.iter_backends():
                items = [dict(title=video.title,
                              page_url=video.page_url,
                              url=video.url if video.url else '/download?id=%s' % video.id
                             ) \
                         for video in backend.iter_search_results(pattern=q, nsfw=nsfw)]
                if items:
                    c['results'][backend.name] = items
        template = template_lookup.get_template('index.mako')
        buf = StringIO()
        ctx = Context(buf, **c)
        template.render_context(ctx)
        return buf.getvalue().strip()
