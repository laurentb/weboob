## -*- coding: utf-8 -*-

<%inherit file="base.mako"/>

<%def name="title()" filter="trim">
weboob / messages
</%def>

<%def name="body()">
    % for (name, backend) in backends:
<h1>${name}</h1>
<ul>
        % for message in backend.iter_messages():
    <li>
        ${message.get_title()}
        <p>${message.get_content()[:80]}</p>
    </li>
        % endfor
</ul>
    % endfor
</%def>
