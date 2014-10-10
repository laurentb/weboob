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


from weboob.deprecated.browser import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.capabilities.contact import QueryError
from weboob.tools.log import getLogger


class QueriesQueue(Optimization):
    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('queriesqueue', browser.logger)

        self.queue = storage.get('queries_queue', 'queue', default=[])

        self.check_cron = None

    def save(self):
        self.storage.set('queries_queue', 'queue', self.queue)
        self.storage.save()

    def start(self):
        self.check_cron = self.sched.repeat(3600, self.flush_queue)
        return True

    def stop(self):
        self.sched.cancel(self.check_cron)
        self.check_cron = None
        return True

    def is_running(self):
        return self.check_cron is not None

    def enqueue_query(self, id, priority=999):
        id_queue = [_id[1] for _id in self.queue]
        if int(id) in id_queue:
            raise QueryError('This id is already queued')
        self.queue.append((int(priority), int(id)))
        self.save()
        # Try to flush queue to send it now.
        self.flush_queue()

        # Check if the enqueued query has been sent
        for p, i in self.queue:
            if i == int(id):
                return False
        return True

    def flush_queue(self):
        self.queue.sort()

        priority = 0
        id = None

        try:
            try:
                while len(self.queue) > 0:
                    priority, id = self.queue.pop()

                    if not id:
                        continue

                    with self.browser:
                        if self.browser.send_charm(id):
                            self.logger.info('Charm sent to %s' % id)
                        else:
                            self.queue.append((priority, id))
                            self.logger.info("Charm can't be send to %s" % id)
                            break

                    # As the charm has been correctly sent (no exception raised),
                    # we don't store anymore ID, because if nbAvailableCharms()
                    # fails, we don't want to re-queue this ID.
                    id = None
                    priority = 0

            except BrowserUnavailable:
                # We consider this profil hasn't been [correctly] analysed
                if id is not None:
                    self.queue.append((priority, id))
        finally:
            self.save()
