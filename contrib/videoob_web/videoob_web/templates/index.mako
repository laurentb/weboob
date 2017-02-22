## -*- coding: utf-8 -*-

<%inherit file="base.mako"/>

<%def name="css()" filter="trim">
  <link rel="stylesheet" type="text/css" href="style.css"/>
</%def>

<%def name="video_item(item)">
  <div class="video-item">
    <a href="${item['page_url']}">
      <img src="${item['thumbnail_url']}" alt="${item['title']}"/>
      <br/>
      ${item['title']}
    </a>
    ## (<a href="${item['url']}"><em>download</em></a>)
  </div>
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
    % for item in results:
      ${video_item(item)}
    % endfor
  % else:
    % for backend, items in sorted(results.items()):
      <h2>${backend}</h2>
      % for item in items:
        ${video_item(item)}
      % endfor
    % endfor
  % endif
</div>
</%def>
