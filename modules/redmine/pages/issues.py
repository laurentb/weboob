# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import datetime
import re

from weboob.capabilities.bugtracker import IssueError
from weboob.tools.date import parse_french_date
from weboob.tools.json import json
from weboob.tools.misc import to_unicode
from weboob.browser.filters.standard import CleanText

from .index import BaseHTMLPage


class BaseIssuePage(BaseHTMLPage):
    def parse_datetime(self, text):
        m = re.match('(\d+)/(\d+)/(\d+) (\d+):(\d+) (\w+)', text)
        if m:
            date = datetime.datetime(int(m.group(3)),
                                     int(m.group(1)),
                                     int(m.group(2)),
                                     int(m.group(4)),
                                     int(m.group(5)))
            if m.group(6) == 'pm':
                date += datetime.timedelta(0,12*3600)
            return date

        m = re.match('(\d+)-(\d+)-(\d+) (\d+):(\d+)', text)
        if m:
            return datetime.datetime(int(m.group(1)),
                                     int(m.group(2)),
                                     int(m.group(3)),
                                     int(m.group(4)),
                                     int(m.group(5)))

        m = re.match('(\d+) (\w+) (\d+) (\d+):(\d+)', text)
        if m:
            return parse_french_date(text)

        self.logger.warning('Unable to parse "%s"' % text)
        return text

    PROJECT_FIELDS = {'members':    'values_assigned_to_id',
                      'categories': 'values_category_id',
                      'versions':   'values_fixed_version_id',
                      'statuses':   'values_status_id',
                     }

    def iter_choices(self, name):
        try:
            select, = self.doc.xpath('//select[@id=$id]', id=name)
        except ValueError:
            try:
                select, = self.doc.xpath('//select[@id="%s_1"]' % name)
            except ValueError:
                return
        for option in select.findall('option'):
            if option.attrib['value'].isdigit():
                yield (option.attrib['value'], option.text)

    def get_project(self, project_name):
        project = {}
        project['name'] = project_name
        for field, elid in self.PROJECT_FIELDS.items():
            project[field] = list(self.iter_choices(elid))
        return project

    def get_authenticity_token(self):
        tokens = self.doc.xpath('//input[@name="authenticity_token"]')
        if len(tokens) == 0:
            tokens = self.doc.xpath('//meta[@name="csrf-token"]')
        if len(tokens) == 0:
            raise IssueError("You don't have rights to remove this issue.")

        try:
            token = tokens[0].attrib['value']
        except KeyError:
            token = tokens[0].attrib['content']
        return token

    def get_errors(self):
        errors = []
        for li in self.doc.xpath('//div[@id="errorExplanation"]//li'):
            errors.append(li.text.strip())
        return ', '.join(errors)

    def get_value_from_label(self, name, label):
        for option in self.doc.xpath('//select[@name=$name]/option', name=name):
            if option.text.strip().lower() == label.lower():
                return option.attrib['value']
        return label


class IssuesPage(BaseIssuePage):
    PROJECT_FIELDS = {'members':    'values_assigned_to_id',
                      'categories': 'values_category_id',
                      'versions':   'values_fixed_version_id',
                      'statuses':   'values_status_id',
                     }

    def get_from_js(self, pattern, end, is_list=False):
        """
        find a pattern in any javascript text
        """
        value = None
        for script in self.doc.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            start = txt.find(pattern)
            if start < 0:
                continue

            while True:
                if value is None:
                    value = ''
                else:
                    value += ','
                value += txt[start+len(pattern):start+txt[start+len(pattern):].find(end)+len(pattern)]

                if not is_list:
                    break

                txt = txt[start+len(pattern)+txt[start+len(pattern):].find(end):]

                start = txt.find(pattern)
                if start < 0:
                    break
            return value


    def get_project(self, project_name):
        project = super(IssuesPage, self).get_project(project_name)
        if len(project['statuses']) > 0:
            return project

        args = self.get_from_js('var availableFilters = ', ';')
        if args is None:
            return project

        args = json.loads(args)

        def get_values(key):
            values = []
            if key not in args:
                return values
            for key, value in args[key]['values']:
                if value.isdigit():
                    values.append((value, key))
            return values

        project['members'] = get_values('assigned_to_id')
        project['categories'] = get_values('category_id')
        project['versions'] = get_values('fixed_version_id')
        project['statuses'] = get_values('status_id')
        return project

    def get_query_method(self):
        return self.doc.xpath('//form[@id="query_form"]')[0].attrib['method'].upper()

    def iter_issues(self):
        try:
            issues, = self.doc.xpath('//table[has-class("issues")]')
        except ValueError:
            # No results.
            return

        for tr in issues.getiterator('tr'):
            if not tr.attrib.get('id', '').startswith('issue-'):
                continue
            issue = {'id': tr.attrib['id'].replace('issue-', '')}
            for td in tr.getiterator('td'):
                field = td.attrib.get('class', '')
                if field in ('checkbox','todo',''):
                    continue

                a = td.find('a')
                if a is not None:
                    if a.attrib['href'].startswith('/users/') or \
                       a.attrib['href'].startswith('/versions/'):
                        text = (int(a.attrib['href'].split('/')[-1]), a.text)
                    else:
                        text = a.text
                else:
                    text = td.text

                if field.endswith('_on'):
                    text = self.parse_datetime(text)
                elif field.endswith('_date') and text is not None:
                    m = re.match('(\d+)-(\d+)-(\d+)', text)
                    if m:
                        text = datetime.datetime(int(m.group(1)),
                                                 int(m.group(2)),
                                                 int(m.group(3)))

                if isinstance(text, str):
                    text = to_unicode(text)
                issue[field] = text

            if len(issue) != 0:
                yield issue


class NewIssuePage(BaseIssuePage):
    PROJECT_FIELDS = {'members':    'issue_assigned_to_id',
                      'categories': 'issue_category_id',
                      'versions':   'issue_fixed_version_id',
                      'statuses':   'issue_status_id',
                     }

    form = None

    def get_project_name(self):
        m = re.search('/projects/([^/]+)/', self.url)
        return m.group(1)

    def iter_custom_fields(self):
        for div in self.doc.xpath('//form//input[starts-with(@id, "issue_custom_field")]|//form//select[starts-with(@id, "issue_custom_field")]'):
            if 'type' in div.attrib and div.attrib['type'] == 'hidden':
                continue
            label = self.doc.xpath('//label[@for="%s"]' % div.attrib['id'])[0]
            yield CleanText('.')(label), div

    def set_title(self, title):
        self.form['issue[subject]'] = title

    def set_body(self, body):
        self.form['issue[description]'] = body

    def set_assignee(self, member):
        if member:
            self.form['issue[assigned_to_id]'] = [str(member)]
        else:
            self.form['issue[assigned_to_id]'] = ['']

    def set_version(self, version):
        if version:
            self.form['issue[fixed_version_id]'] = [str(version)]
        else:
            self.form['issue[fixed_version_id]'] = ['']

    def set_tracker(self, tracker):
        if tracker:
            select, = self.doc.xpath('//select[@id="issue_tracker_id"]')
            for option in select.findall('option'):
                if option.text and option.text.strip() == tracker:
                    self.browser['issue[tracker_id]'] = [option.attrib['value']]
                    return
            # value = None
            # if len(self.document.xpath('//a[@title="New tracker"]')) > 0:
            #     value = self.browser.create_tracker(self.get_project_name(), tracker, self.get_authenticity_token())
            # if value:
            #     control = self.browser.find_control('issue[tracker_id]')
            #     mechanize.Item(control, {'name': tracker, 'value': value})
            #     self.browser['issue[tracker_id]'] = [value]
            # else:
            #     self.logger.warning('Tracker "%s" not found' % tracker)
            self.logger.warning('Tracker "%s" not found' % tracker)
        else:
            self.form['issue[tracker_id]'] = ['']

    def set_category(self, category):
        if category:
            select = self.doc.xpath('//select[@id="issue_category_id"]')
            for option in select.findall('option'):
                if option.text and option.text.strip() == category:
                    self.form['issue[category_id]'] = [option.attrib['value']]
                    return
            value = None
            if len(self.doc.xpath('//a[@title="New category"]')) > 0:
                value = self.browser.create_category(self.get_project_name(), category, self.get_authenticity_token())
            if value:
                self.form[category] = value
                self.form['issue[category_id]'] = [value]
            else:
                self.logger.warning('Category "%s" not found' % category)
        else:
            self.form['issue[category_id]'] = ['']

    def set_status(self, status):
        assert status is not None
        self.form['issue[status_id]'] = [str(status)]

    def set_priority(self, priority):
        if priority:
            select, = self.doc.xpath('//select[@id="issue_priority_id"]')
            for option in select.findall('option'):
                if option.text and option.text.strip() == priority:
                    self.form['issue[priority_id]'] = [option.attrib['value']]
                    return
            # value = None
            # if len(self.document.xpath('//a[@title="New priority"]')) > 0:
            #     value = self.browser.create_priority(self.get_project_name(), priority, self.get_authenticity_token())
            # if value:
            #     control = self.browser.find_control('issue[priority_id]')
            #     mechanize.Item(control, {'name': priority, 'value': value})
            #     self.browser['issue[priority_id]'] = [value]
            # else:
            #     self.logger.warning('Priority "%s" not found' % priority)
            self.logger.warning('Priority "%s" not found' % priority)
        else:
            self.form['issue[priority_id]'] = ['']

    def set_start(self, start):
        if start is not None:
            self.form['issue[start_date]'] = start.strftime("%Y-%m-%d")
        #XXX: else set to "" ?

    def set_due(self, due):
        if due is not None:
            self.form['issue[due_date]'] = due.strftime("%Y-%m-%d")
        #XXX: else set to "" ?

    def set_note(self, message):
        if 'notes' in self.form:
            self.form['notes'] = message
        else:
            self.form['issue[notes]'] = message

    def set_fields(self, fields):
        for key, div in self.iter_custom_fields():
            try:
                self.form[div.attrib['name']] = fields[key]
            except KeyError:
                continue

    def fill_form(self, **kwargs):
        self.form = self.get_form(id='issue-form')
        for key, value in kwargs.items():
            if value is not None:
                getattr(self, 'set_%s' % key)(value)
        self.form.submit()


class IssuePage(NewIssuePage):
    def _parse_selection(self, id):
        try:
            select, = self.doc.xpath('//select[@id=$id]', id=id)
        except ValueError:
            # not available for this project
            return ('', None)
        else:
            options = select.findall('option')
            for option in options:
                if 'selected' in option.attrib:
                    return (int(option.attrib['value']), to_unicode(option.text))
            return ('', None)

    def get_params(self):
        params = {}
        content, = self.doc.xpath('//div[@id="content"]')
        issue, = content.xpath('.//div[has-class("issue")]')

        params['project'] = self.get_project(CleanText('(//h1)[1]')(self.doc))
        params['subject'] = issue.xpath('.//div[has-class("subject")]/div/h3')[0].text.strip()
        params['body'] = self.doc.xpath('//textarea[@id="issue_description"]')[0].text.strip()
        author, = issue.xpath('.//p[has-class("author")]')

        # check issue 666 on symlink.me
        i = 0
        alist = author.findall('a')
        if 'title' not in alist[i].attrib:
            params['author'] = (int(alist[i].attrib['href'].split('/')[-1]),
                                to_unicode(alist[i].text))
            i += 1
        else:
            params['author'] = (0, 'Anonymous')
        params['created_on'] = self.parse_datetime(alist[i].attrib['title'])
        if len(alist) > i+1:
            params['updated_on'] = self.parse_datetime(alist[i+1].attrib['title'])
        else:
            params['updated_on'] = None

        params['status'] = self._parse_selection('issue_status_id')
        params['priority'] = self._parse_selection('issue_priority_id')
        params['assignee'] = self._parse_selection('issue_assigned_to_id')
        params['tracker'] = self._parse_selection('issue_tracker_id')
        params['category'] = self._parse_selection('issue_category_id')
        params['version'] = self._parse_selection('issue_fixed_version_id')
        div, = self.doc.xpath('//input[@id="issue_start_date"]')
        if 'value' in div.attrib:
            params['start_date'] = datetime.datetime.strptime(div.attrib['value'], "%Y-%m-%d")
        else:
            params['start_date'] = None
        div, = self.doc.xpath('//input[@id="issue_due_date"]')
        if 'value' in div.attrib:
            params['due_date'] = datetime.datetime.strptime(div.attrib['value'], "%Y-%m-%d")
        else:
            params['due_date'] = None

        params['fields'] = {}
        for key, div in self.iter_custom_fields():
            value = ''
            if 'value' in div.attrib:
                value = div.attrib['value']
            else:
                # XXX: use _parse_selection()?
                olist = div.xpath('.//option[@selected="selected"]')
                value = ', '.join([opt.attrib['value'] for opt in olist])
            params['fields'][key] = value

        params['attachments'] = []
        for p in content.xpath('//div[has-class("attachments")]/p'):
            attachment = {}
            a = p.find('a')
            attachment['id'] = int(a.attrib['href'].split('/')[-2])
            attachment['filename'] = p.find('a').text
            attachment['url'] = '%s%s' % (self.browser.BASEURL, p.find('a').attrib['href'])
            params['attachments'].append(attachment)

        params['updates'] = []
        for div in content.xpath('.//div[has-class("journal")]'):
            update = {}
            update['id'] = div.xpath('.//h4//a')[0].text[1:]
            user_link = div.xpath('.//h4//a[contains(@href, "/users/")]')
            if len(user_link) > 0:
                update['author'] = (int(user_link[0].attrib['href'].split('/')[-1]),
                                    to_unicode(user_link[0].text))
            else:
                for txt in div.xpath('.//h4//text()'):
                    m = re.search('Updated by (.*)', txt.strip())
                    if m:
                        update['author'] = (0, to_unicode(m.group(1)))
            update['date'] = self.parse_datetime(div.xpath('.//h4//a[last()]')[0].attrib['title'])

            comments = div.xpath('.//div[starts-with(@id, "journal-")]')
            if len(comments) > 0:
                comment = comments[0]
                subdiv = comment.find('div')
                if subdiv is not None:
                    # a subdiv which contains changes is found, move the tail text
                    # of this div to comment text, and remove it.
                    comment.text = (comment.text or '') + (subdiv.tail or '')
                    comment.remove(comment.find('div'))
                update['message'] = self.parser.tostring(comment).strip()
            else:
                update['message'] = None

            changes = []
            try:
                details, = div.xpath('.//ul[has-class("details")]')
            except ValueError:
                pass
            else:
                for li in details.findall('li'):
                    field = li.find('strong').text#.decode('utf-8')
                    i = li.findall('i')
                    new = None
                    last = None
                    if len(i) > 0:
                        if len(i) == 2:
                            last = i[0].text.decode('utf-8')
                        new = i[-1].text#.decode('utf-8')
                    elif li.find('strike') is not None:
                        last = li.find('strike').find('i').text.decode('utf-8')
                    elif li.find('a') is not None:
                        new = li.find('a').text.decode('utf-8')
                    else:
                        self.logger.warning('Unable to handle change for %s' % field)
                    changes.append((field, last, new))
            update['changes'] = changes

            params['updates'].append(update)

        return params


class IssueLogTimePage(BaseHTMLPage):
    def logtime(self, hours, message):
        self.browser.select_form(predicate=lambda form: form.attrs.get('action', '').endswith('/edit'))
        self.browser['time_entry[hours]'] = '%.2f' % hours
        self.browser['time_entry[comments]'] = message.encode('utf-8')
        self.browser['time_entry[activity_id]'] = ['8']
        self.browser.submit()


class IssueTimeEntriesPage(BaseHTMLPage):
    pass
