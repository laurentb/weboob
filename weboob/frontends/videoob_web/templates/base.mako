## -*- coding: utf-8 -*-

<%def name="title()" filter="trim">
Videoob Web
</%def>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
    <head>
        <title>${self.title()}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${next.css()}
    </head>
    <body>
      ${next.body()}
    </body>
</html>
