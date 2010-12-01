# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


import os

import gtk
import webkit

from weboob.tools.application.javascript import get_javascript
from ..table import HTMLTableFormatter


__all__ = ['WebkitGtkFormatter']


class WebBrowser(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.connect('destroy', gtk.main_quit)
        self.set_default_size(800, 600)
        self.web_view = webkit.WebView()
        sw = gtk.ScrolledWindow() 
        sw.add(self.web_view) 
        self.add(sw) 
        self.show_all()


class WebkitGtkFormatter(HTMLTableFormatter):
    def __init__(self):
        HTMLTableFormatter.__init__(self, return_only=True)

    def flush(self):
        table_string = HTMLTableFormatter.flush(self)
        js_filepaths = []
        js_filepaths.append(get_javascript('jquery'))
        js_filepaths.append(get_javascript('tablesorter'))
        scripts = ['<script type="text/javascript" src="%s"></script>' % js_filepath for js_filepath in js_filepaths]
        html_string_params = dict(table=table_string)
        if scripts:
            html_string_params['scripts'] = ''.join(scripts)
        html_string = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        %(scripts)s
    </head>
    <body>
        <style type="text/css">
*
{
    font-size: 10pt;
}
        </style>
        <script type="text/javascript">
$(function() {
    var $table = $("table");
    $table
        .prepend(
            $("<thead>")
                .append(
                    $table.find("tr:first")
                )
        )
        .tablesorter();
});
        </script>
        %(table)s
    </body>
</html>
""" % html_string_params
        web_browser = WebBrowser()
        web_browser.web_view.load_html_string(html_string, 'file://%s' % os.path.abspath(os.getcwd()))
        gtk.main()
