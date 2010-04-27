## -*- coding: utf-8 -*-

<%inherit file="base.mako"/>

<%def name="video_link(item)">
  <a href="${item['page_url']}">${item['title']}</a>
  ## (<a href="${item['url']}"><em>download</em></a>)
</%def>

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
  % if merge:
    <ul>
      % for item in results:
        <li>${video_link(item)}</li>
      % endfor
    </ul>
  % else:
    % for backend, items in sorted(results.iteritems()):
      <h2>${backend}</h2>
      <ul>
        % for item in items:
          <li>${video_link(item)}</li>
        % endfor
      </ul>
    % endfor
  % endif
</div>
</%def>
