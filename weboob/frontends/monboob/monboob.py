# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon, Christophe Benz
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


from email.mime.text import MIMEText
from smtplib import SMTP
from email.Header import Header, decode_header
from email.Utils import parseaddr, formataddr
from email import message_from_file
import time
import re
import sys
import logging

from weboob.capabilities.messages import ICapMessages, ICapMessagesReply, Message
from weboob.tools.application import ConsoleApplication
from weboob.tools.misc import html2text, get_backtrace


__all__ = ['Monboob']


class Monboob(ConsoleApplication):
    APPNAME = 'monboob'
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    CONFIG = {'interval':  15,
              'domain':    'weboob.example.org',
              'recipient': 'weboob@example.org',
              'smtp':      'localhost',
              'backends':  '',
              'html':      0}

    def main(self, argv):
        self.load_config()

        names = None
        if self.config.get('backends'):
            names = self.config.get('backends').split()

        self.load_backends(ICapMessages, names=names, storage=self.create_storage())

        return self.process_command(*argv[1:])

    @ConsoleApplication.command("pipe with a mail to post message")
    def command_post(self):
        msg = message_from_file(sys.stdin)
        reply_to = msg.get('In-Reply-To')
        if not reply_to:
            print >>sys.stderr, 'This is not a reply (no Reply-To field)'
            return 1

        m = re.match('<(.*)@(.*)>', reply_to)
        if m:
            reply_to = m.group(1)
        title = msg.get('Subject')
        if title:
            new_title = u''
            for part in decode_header(title):
                if part[1]:
                    new_title += unicode(part[0], part[1])
                else:
                    new_title += unicode(part[0])
            title = new_title

        content = u''
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                s = part.get_payload(decode=True)
                charsets = part.get_charsets() + msg.get_charsets()
                for charset in charsets:
                    try:
                        content += unicode(s, charset)
                    except:
                        continue
                    else:
                        break

        # remove signature
        content = content.split(u'\n-- \n')[0]

        bname, id = reply_to.split('.', 1)
        try:
            backend = self.weboob.backends[bname]
        except KeyError:
            print >>sys.stderr, 'Backend %s not found' % bname
            return 1

        if not backend.has_caps(ICapMessagesReply):
            print >>sys.stderr, 'The backend %s does not implement ICapMessagesReply' % bname
            return 1

        thread_id, msg_id = id.rsplit('.', 1)
        try:
            backend.post_reply(thread_id, msg_id, title, content)
        except Exception, e:
            content = u'Unable to send message to %s:\n' % thread_id
            content += '\n\t%s\n' % e
            if logging.root.level == logging.DEBUG:
                content += '\n%s\n' % get_backtrace(e)
            self.send_email(backend, Message(thread_id,
                                             0,
                                             title='Unable to send message',
                                             sender='Monboob',
                                             reply_id=msg_id,
                                             content=content))

    @ConsoleApplication.command("run daemon")
    def command_run(self):
        self.weboob.repeat(int(self.config.get('interval')), self.process)
        self.weboob.loop()

    def process(self):
        for backend, message in self.weboob.do('iter_new_messages'):
            self.send_email(backend, message)

    def send_email(self, backend, mail):
        domain = self.config.get('domain')
        recipient = self.config.get('recipient')

        reply_id = ''
        if mail.get_reply_id():
            reply_id = u'<%s.%s@%s>' % (backend.name, mail.get_full_reply_id(), domain)
        subject = mail.get_title()
        sender = u'"%s" <%s@%s>' % (mail.get_from().replace('"', '""'), backend.name, domain)

        # assume that get_date() returns an UTC datetime
        date = time.strftime('%a, %d %b %Y %H:%M:%S +0000', mail.get_date().timetuple())
        msg_id = u'<%s.%s@%s>' % (backend.name, mail.get_full_id(), domain)

        if int(self.config.get('html')) and mail.is_html:
            body = mail.get_content()
            content_type = 'html'
        else:
            if mail.is_html:
                body = html2text(mail.get_content())
            else:
                body = mail.get_content()
            content_type = 'plain'

        if mail.get_signature():
            if int(self.config.get('html')) and mail.is_html:
                body += u'<p>-- <br />%s</p>' % mail.get_signature()
            else:
                body += u'\n\n-- \n'
                if mail.is_html:
                    body += html2text(mail.get_signature())
                else:
                    body += mail.get_signature()

        # Header class is smart enough to try US-ASCII, then the charset we
        # provide, then fall back to UTF-8.
        header_charset = 'ISO-8859-1'

        # We must choose the body charset manually
        for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
            try:
                body.encode(body_charset)
            except UnicodeError:
                pass
            else:
                break

        # Split real name (which is optional) and email address parts
        sender_name, sender_addr = parseaddr(sender)
        recipient_name, recipient_addr = parseaddr(recipient)

        # We must always pass Unicode strings to Header, otherwise it will
        # use RFC 2047 encoding even on plain ASCII strings.
        sender_name = str(Header(unicode(sender_name), header_charset))
        recipient_name = str(Header(unicode(recipient_name), header_charset))

        # Make sure email addresses do not contain non-ASCII characters
        sender_addr = sender_addr.encode('ascii')
        recipient_addr = recipient_addr.encode('ascii')

        # Create the message ('plain' stands for Content-Type: text/plain)
        msg = MIMEText(body.encode(body_charset), content_type, body_charset)
        msg['From'] = formataddr((sender_name, sender_addr))
        msg['To'] = formataddr((recipient_name, recipient_addr))
        msg['Subject'] = Header(unicode(subject), header_charset)
        msg['Message-Id'] = msg_id
        msg['Date'] = date
        if reply_id:
            msg['In-Reply-To'] = reply_id

        # Send the message via SMTP to localhost:25
        smtp = SMTP(self.config.get('smtp'))
        print 'Send mail from <%s> to <%s>' % (sender, recipient)
        smtp.sendmail(sender, recipient, msg.as_string())
        smtp.quit()

        return msg['Message-Id']
