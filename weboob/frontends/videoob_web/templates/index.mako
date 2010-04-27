## -*- coding: utf-8 -*-

<%inherit file="base.mako"/>

<%def name="body()">
<h1>Videoob Web</h1>
<div id="search">
  <form action="/" method="get">
    <label for="q">Search pattern:</label>
    <input id="q" type="text" name="q" value="${form_data['q']}" />
    <input type="submit" value="Search" />
  </form>
</div>
<div id="results">
  % for backend, items in results.iteritems():
    <h2>${backend}</h2>
    <ul>
      % for item in items:
        <li>
          <a href="${item['page_url']}">${item['title']}</a>
##          (<a href="${item['url']}"><em>download</em></a>)
        </li>
      % endfor
    </ul>
  % endfor
</div>
</%def>
