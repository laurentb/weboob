# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from datetime import timedelta
import sys

from weboob.capabilities.bugtracker import ICapBugTracker, Query, Update, Project, Issue
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter
from weboob.tools.misc import html2text


__all__ = ['BoobTracker']


class IssueFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'project', 'title', 'body', 'author')

    def format_obj(self, obj, alias):
        result = u'%s%s - #%s - %s%s\n' % (self.BOLD, obj.project.name, obj.fullid, obj.title, self.NC)
        result += '\n%s\n\n' % obj.body
        result += 'Author: %s (%s)\n' % (obj.author.name, obj.creation)
        if hasattr(obj, 'status') and obj.status:
            result += 'Status: %s\n' % obj.status.name
        if hasattr(obj, 'version') and obj.version:
            result += 'Version: %s\n' % obj.version.name
        if hasattr(obj, 'category') and obj.category:
            result += 'Category: %s\n' % obj.category
        if hasattr(obj, 'assignee') and obj.assignee:
            result += 'Assignee: %s\n' % (obj.assignee.name)
        if hasattr(obj, 'attachments') and obj.attachments:
            result += '\nAttachments:\n'
            for a in obj.attachments:
                result += '* %s%s%s <%s>\n' % (self.BOLD, a.filename, self.NC, a.url)
        if hasattr(obj, 'history') and obj.history:
            result += '\nHistory:\n'
            for u in obj.history:
                result += '* %s%s - %s%s\n' % (self.BOLD, u.date, u.author.name, self.NC)
                for change in u.changes:
                    result += '  - %s%s%s: %s -> %s\n' % (self.BOLD, change.field, self.NC, change.last, change.new)
                if u.message:
                    result += html2text(u.message)
        return result


class IssuesListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'project', 'status', 'title', 'category')

    def get_title(self, obj):
        return '%s - [%s] %s' % (obj.project.name, obj.status.name, obj.title)

    def get_description(self, obj):
        return obj.category


class BoobTracker(ReplApplication):
    APPNAME = 'boobtracker'
    VERSION = '0.i'
    COPYRIGHT = 'Copyright(C) 2011 Romain Bignon'
    DESCRIPTION = "Console application allowing to create, edit, view bug tracking issues."
    SHORT_DESCRIPTION = "manage bug tracking issues"
    CAPS = ICapBugTracker
    EXTRA_FORMATTERS = {'issue_info': IssueFormatter,
                        'issues_list': IssuesListFormatter,
                       }
    COMMANDS_FORMATTERS = {'get':     'issue_info',
                           'post':    'issue_info',
                           'edit':    'issue_info',
                           'search':  'issues_list',
                           'ls':      'issues_list',
                          }
    COLLECTION_OBJECTS = (Project, Issue, )

    def add_application_options(self, group):
        group.add_option('--author')
        group.add_option('--title')
        group.add_option('--assignee')
        group.add_option('--target-version', dest='version')
        group.add_option('--category')
        group.add_option('--status')

    @defaultcount(10)
    def do_search(self, line):
        """
        search PROJECT

        List issues for a project.

        You can use these filters from command line:
           --author AUTHOR
           --title TITLE_PATTERN
           --assignee ASSIGNEE
           --target-version VERSION
           --category CATEGORY
           --status STATUS
        """
        query = Query()

        path = self.working_path.get()
        backends = []
        if line.strip():
            query.project, backends = self.parse_id(line, unique_backend=True)
        elif len(path) > 0:
            query.project = path[0]
        else:
            print >>sys.stderr, 'Please enter a project name'
            return 1

        query.author = self.options.author
        query.title = self.options.title
        query.assignee = self.options.assignee
        query.version = self.options.version
        query.category = self.options.category
        query.status = self.options.status

        self.change_path([query.project, u'search'])
        for backend, issue in self.do('iter_issues', query, backends=backends):
            self.add_object(issue)
            self.format(issue)

    def complete_get(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_get(self, line):
        """
        get ISSUE

        Get an issue and display it.
        """
        if not line:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('get', short=True)
            return 2

        issue = self.get_object(line, 'get_issue')
        if not issue:
            print >>sys.stderr, 'Issue not found: %s' % line
            return 3
        self.format(issue)

    def complete_comment(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_comment(self, line):
        """
        comment ISSUE [TEXT]

        Comment an issue. If no text is given, enter it in standard input.
        """
        id, text = self.parse_command_args(line, 2, 1)
        if text is None:
            text = self.acquire_input()

        id, backend_name = self.parse_id(id, unique_backend=True)
        update = Update(0)
        update.message = text

        self.do('update_issue', id, update, backends=backend_name).wait()

    def do_logtime(self, line):
        """
        logtime ISSUE HOURS [TEXT]

        Log spent time on an issue.
        """
        id, hours, text = self.parse_command_args(line, 3, 2)
        if text is None:
            text = self.acquire_input()

        try:
            hours = float(hours)
        except ValueError:
            print >>sys.stderr, 'Error: HOURS parameter may be a float'
            return 1

        id, backend_name = self.parse_id(id, unique_backend=True)
        update = Update(0)
        update.message = text
        update.hours = timedelta(hours=hours)

        self.do('update_issue', id, update, backends=backend_name).wait()

    def do_remove(self, line):
        """
        remove ISSUE

        Remove an issue.
        """
        id, backend_name = self.parse_id(line, unique_backend=True)
        self.do('remove_issue', id, backends=backend_name).wait()

    ISSUE_FIELDS = (('title',    (None,       False)),
                    ('assignee', ('members',  True)),
                    ('version',  ('versions', True)),
                    ('category', ('categories', False)),
                    ('status',   ('statuses', True)),
                   )

    def get_list_item(self, objects_list, name):
        if name is None:
            return None

        for obj in objects_list:
            if obj.name.lower() == name.lower():
                return obj
        print 'Error: "%s" is not found' % name
        return None

    def prompt_issue(self, issue, requested_key=None, requested_value=None):
        for key, (list_name, is_list_object) in self.ISSUE_FIELDS:
            if requested_key and requested_key != key:
                continue

            if requested_value:
                value = requested_value
            elif not self.interactive:
                value = getattr(self.options, key)
            else:
                value = None

            if sys.stdin.isatty():
                default = getattr(issue, key)
                if not default:
                    default = None
                elif 'name' in dir(default):
                    default = default.name
                if list_name is None:
                    if value is not None:
                        setattr(issue, key, value)
                        print '%s: %s' % (key.capitalize(), value)
                        continue
                    setattr(issue, key, self.ask(key.capitalize(), default=default))
                else:
                    objects_list = getattr(issue.project, list_name)
                    if len(objects_list) == 0:
                        continue

                    print '----------'
                    if value is not None:
                        if is_list_object:
                            value = self.get_list_item(objects_list, value)
                        if value is not None:
                            setattr(issue, key, value)
                            print '%s: %s' % (key.capitalize(), value.name)
                            continue

                    while value is None:
                        print 'Availables:', ', '.join([(o if isinstance(o, basestring) else o.name) for o in objects_list])
                        if is_list_object and getattr(issue, key):
                            default = getattr(issue, key).name
                        else:
                            default = getattr(issue, key) or ''
                        text = self.ask(key.capitalize(), default=default)
                        if not text:
                            break
                        if is_list_object:
                            value = self.get_list_item(objects_list, text)
                        else:
                            value = text

                    if value is not None:
                        setattr(issue, key, value)

    def do_post(self, line):
        """
        post PROJECT

        Post a new issue.

        If you are not in interactive mode, you can use these parameters:
           --title TITLE
           --assignee ASSIGNEE
           --target-version VERSION
           --category CATEGORY
           --status STATUS
        """
        if not line.strip():
            print 'Please give the project name'
            return 1

        project, backend_name = self.parse_id(line, unique_backend=True)

        backend = self.weboob.get_backend(backend_name)
        issue = backend.create_issue(project)

        self.prompt_issue(issue)
        if sys.stdin.isatty():
            print '----------'
            print 'Please enter the content of this new issue.'
        issue.body = self.acquire_input()

        for backend, issue in self.weboob.do('post_issue', issue, backends=backend):
            if issue:
                print 'Issue %s%s@%s%s created' % (self.BOLD, issue.id, issue.backend, self.NC)

    def complete_remove(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()
        if len(args) == 3:
            return dict(self.ISSUE_FIELDS).keys()

    def do_edit(self, line):
        """
        edit ISSUE [KEY [VALUE]]

        Edit an issue.
        If you are not in interactive mode, you can use these parameters:
           --title TITLE
           --assignee ASSIGNEE
           --target-version VERSION
           --category CATEGORY
           --status STATUS
        """
        _id, key, value = self.parse_command_args(line, 3, 1)
        issue = self.get_object(_id, 'get_issue')
        if not issue:
            print >>sys.stderr, 'Issue not found: %s' % _id
            return 3

        self.prompt_issue(issue, key, value)

        for backend, i in self.weboob.do('post_issue', issue, backends=issue.backend):
            if i:
                print 'Issue %s%s@%s%s updated' % (self.BOLD, issue.id, issue.backend, self.NC)
                self.format(i)

    def complete_attach(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()
        elif len(args) >= 3:
            return self.path_completer(args[2])

    def do_attach(self, line):
        """
        attach ISSUE FILENAME

        Attach a file to an issue (Not implemented yet).
        """
        print >>sys.stderr, 'Not implemented yet.'
