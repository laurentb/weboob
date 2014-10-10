# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import re
import datetime

from weboob.capabilities.bugtracker import IssueError
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.tools.date import parse_french_date
from weboob.tools.misc import to_unicode
from weboob.deprecated.mech import ClientForm
from weboob.tools.json import json


class BaseIssuePage(Page):
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
            select = self.parser.select(self.document.getroot(), 'select#%s' % name, 1)
        except BrokenPageError:
            try:
                select = self.parser.select(self.document.getroot(), 'select#%s_1' % name, 1)
            except BrokenPageError:
                return
        for option in select.findall('option'):
            if option.attrib['value'].isdigit():
                yield (option.attrib['value'], option.text)

    def get_project(self, project_name):
        project = {}
        project['name'] = project_name
        for field, elid in self.PROJECT_FIELDS.iteritems():
            project[field] = list(self.iter_choices(elid))
        return project

    def get_authenticity_token(self):
        tokens = self.parser.select(self.document.getroot(), 'input[name=authenticity_token]')
        if len(tokens) == 0:
            tokens = self.document.xpath('//meta[@name="csrf-token"]')
        if len(tokens) == 0:
            raise IssueError("You don't have rights to remove this issue.")

        try:
            token = tokens[0].attrib['value']
        except KeyError:
            token = tokens[0].attrib['content']
        return token

    def get_errors(self):
        errors = []
        for li in self.document.xpath('//div[@id="errorExplanation"]//li'):
            errors.append(li.text.strip())
        return ', '.join(errors)

    def get_value_from_label(self, name, label):
        for option in self.document.xpath('//select[@name="%s"]/option' % name):
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
        for script in self.document.xpath('//script'):
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
        return self.document.xpath('//form[@id="query_form"]')[0].attrib['method'].upper()

    def iter_issues(self):
        try:
            issues = self.parser.select(self.document.getroot(), 'table.issues', 1)
        except BrokenPageError:
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

    def get_project_name(self):
        m = re.search('/projects/([^/]+)/', self.url)
        return m.group(1)

    def iter_custom_fields(self):
        for div in self.document.xpath('//form//input[starts-with(@id, "issue_custom_field")]|//form//select[starts-with(@id, "issue_custom_field")]'):
            if 'type' in div.attrib and div.attrib['type'] == 'hidden':
                continue
            label = self.document.xpath('//label[@for="%s"]' % div.attrib['id'])[0]
            yield label.text.strip(), div

    def set_title(self, title):
        self.browser['issue[subject]'] = title.encode('utf-8')

    def set_body(self, body):
        self.browser['issue[description]'] = body.encode('utf-8')

    def set_assignee(self, member):
        if member:
            self.browser['issue[assigned_to_id]'] = [str(member)]
        else:
            self.browser['issue[assigned_to_id]'] = ['']

    def set_version(self, version):
        try:
            if version:
                self.browser['issue[fixed_version_id]'] = [str(version)]
            else:
                self.browser['issue[fixed_version_id]'] = ['']
        except ClientForm.ItemNotFoundError:
            self.logger.warning('Version not found: %s' % version)

    def set_tracker(self, tracker):
        if tracker:
            select = self.parser.select(self.document.getroot(), 'select#issue_tracker_id', 1)
            for option in select.findall('option'):
                if option.text and option.text.strip() == tracker:
                    self.browser['issue[tracker_id]'] = [option.attrib['value']]
                    return
            # value = None
            # if len(self.document.xpath('//a[@title="New tracker"]')) > 0:
            #     value = self.browser.create_tracker(self.get_project_name(), tracker, self.get_authenticity_token())
            # if value:
            #     control = self.browser.find_control('issue[tracker_id]')
            #     ClientForm.Item(control, {'name': tracker, 'value': value})
            #     self.browser['issue[tracker_id]'] = [value]
            # else:
            #     self.logger.warning('Tracker "%s" not found' % tracker)
            self.logger.warning('Tracker "%s" not found' % tracker)
        else:
            try:
                self.browser['issue[tracker_id]'] = ['']
            except ClientForm.ControlNotFoundError:
                self.logger.warning('Tracker item not found')

    def set_category(self, category):
        if category:
            select = self.parser.select(self.document.getroot(), 'select#issue_category_id', 1)
            for option in select.findall('option'):
                if option.text and option.text.strip() == category:
                    self.browser['issue[category_id]'] = [option.attrib['value']]
                    return
            value = None
            if len(self.document.xpath('//a[@title="New category"]')) > 0:
                value = self.browser.create_category(self.get_project_name(), category, self.get_authenticity_token())
            if value:
                control = self.browser.find_control('issue[category_id]')
                ClientForm.Item(control, {'name': category, 'value': value})
                self.browser['issue[category_id]'] = [value]
            else:
                self.logger.warning('Category "%s" not found' % category)
        else:
            try:
                self.browser['issue[category_id]'] = ['']
            except ClientForm.ControlNotFoundError:
                self.logger.warning('Category item not found')

    def set_status(self, status):
        assert status is not None
        self.browser['issue[status_id]'] = [str(status)]

    def set_priority(self, priority):
        if priority:
            select = self.parser.select(self.document.getroot(), 'select#issue_priority_id', 1)
            for option in select.findall('option'):
                if option.text and option.text.strip() == priority:
                    self.browser['issue[priority_id]'] = [option.attrib['value']]
                    return
            # value = None
            # if len(self.document.xpath('//a[@title="New priority"]')) > 0:
            #     value = self.browser.create_priority(self.get_project_name(), priority, self.get_authenticity_token())
            # if value:
            #     control = self.browser.find_control('issue[priority_id]')
            #     ClientForm.Item(control, {'name': priority, 'value': value})
            #     self.browser['issue[priority_id]'] = [value]
            # else:
            #     self.logger.warning('Priority "%s" not found' % priority)
            self.logger.warning('Priority "%s" not found' % priority)
        else:
            try:
                self.browser['issue[priority_id]'] = ['']
            except ClientForm.ControlNotFoundError:
                self.logger.warning('Priority item not found')

    def set_start(self, start):
        if start is not None:
            self.browser['issue[start_date]'] = start.strftime("%Y-%m-%d")
        #XXX: else set to "" ?

    def set_due(self, due):
        if due is not None:
            self.browser['issue[due_date]'] = due.strftime("%Y-%m-%d")
        #XXX: else set to "" ?

    def set_note(self, message):
        try:
            self.browser['notes'] = message.encode('utf-8')
        except ClientForm.ControlNotFoundError:
            self.browser['issue[notes]'] = message.encode('utf-8')

    def set_fields(self, fields):
        for key, div in self.iter_custom_fields():
            try:
                control = self.browser.find_control(div.attrib['name'], nr=0)
                if isinstance(control, ClientForm.TextControl):
                    control.value = fields[key]
                else:
                    item = control.get(label=fields[key].encode("utf-8"), nr=0)
                    if item and fields[key] != '':
                        item.selected = True
            except KeyError:
                continue

    def fill_form(self, **kwargs):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'issue-form')
        for key, value in kwargs.iteritems():
            if value is not None:
                getattr(self, 'set_%s' % key)(value)
        self.browser.submit()


class IssuePage(NewIssuePage):
    def _parse_selection(self, id):
        try:
            select = self.parser.select(self.document.getroot(), 'select#%s' % id, 1)
        except BrokenPageError:
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
        content = self.parser.select(self.document.getroot(), 'div#content', 1)
        issue = self.parser.select(content, 'div.issue', 1)

        params['project'] = self.get_project(to_unicode(self.parser.select(self.document.getroot(), 'h1', 1).text))
        params['subject'] = to_unicode(self.parser.select(issue, 'div.subject', 1).find('div').find('h3').text.strip())
        params['body'] = to_unicode(self.parser.select(self.document.getroot(), 'textarea#issue_description', 1).text)
        author = self.parser.select(issue, 'p.author', 1)

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
        div = self.parser.select(self.document.getroot(), 'input#issue_start_date', 1)
        if 'value' in div.attrib:
            params['start_date'] = datetime.datetime.strptime(div.attrib['value'], "%Y-%m-%d")
        else:
            params['start_date'] = None
        div = self.parser.select(self.document.getroot(), 'input#issue_due_date', 1)
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
        try:
            for p in self.parser.select(content, 'div.attachments', 1).findall('p'):
                attachment = {}
                a = p.find('a')
                attachment['id'] = int(a.attrib['href'].split('/')[-2])
                attachment['filename'] = p.find('a').text
                attachment['url'] = '%s://%s%s' % (self.browser.PROTOCOL, self.browser.DOMAIN, p.find('a').attrib['href'])
                params['attachments'].append(attachment)
        except BrokenPageError:
            pass

        params['updates'] = []
        for div in self.parser.select(content, 'div.journal'):
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
                details = self.parser.select(div, 'ul.details', 1)
            except BrokenPageError:
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


class IssueLogTimePage(Page):
    def logtime(self, hours, message):
        self.browser.select_form(predicate=lambda form: form.attrs.get('action', '').endswith('/edit'))
        self.browser['time_entry[hours]'] = '%.2f' % hours
        self.browser['time_entry[comments]'] = message.encode('utf-8')
        self.browser['time_entry[activity_id]'] = ['8']
        self.browser.submit()


class IssueTimeEntriesPage(Page):
    pass
