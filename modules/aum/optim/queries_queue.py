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


from weboob.exceptions import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.capabilities.contact import QueryError
from weboob.tools.log import getLogger


class QueriesQueue(Optimization):
    def __init__(self, sched, storage, browser):
        super(QueriesQueue, self).__init__()
        self._sched = sched
        self._storage = storage
        self._browser = browser
        self._logger = getLogger('queriesqueue', browser.logger)

        self._queue = storage.get('queries_queue', 'queue', default=[])

        self._check_cron = None

    def save(self):
        self._storage.set('queries_queue', 'queue', self._queue)
        self._storage.save()

    def start(self):
        self._check_cron = self._sched.repeat(3600, self.flush_queue)
        return True

    def stop(self):
        self._sched.cancel(self._check_cron)
        self._check_cron = None
        return True

    def is_running(self):
        return self._check_cron is not None

    def enqueue_query(self, id, priority=999):
        id_queue = [_id[1] for _id in self._queue]
        if int(id) in id_queue:
            raise QueryError('This id is already queued')
        self._queue.append((int(priority), int(id)))
        self.save()
        # Try to flush queue to send it now.
        self.flush_queue()

        # Check if the enqueued query has been sent
        for _, i in self._queue:
            if i == int(id):
                return False
        return True

    def flush_queue(self):
        self._queue.sort()

        priority = 0
        id = None

        try:
            try:
                while len(self._queue) > 0:
                    priority, id = self._queue.pop()

                    if not id:
                        continue

                    if self._browser.send_charm(id):
                        self._logger.info('Charm sent to %s', id)
                    else:
                        self._queue.append((priority, id))
                        self._logger.info("Charm can't be send to %s", id)
                        break

                    # As the charm has been correctly sent (no exception raised),
                    # we don't store anymore ID, because if nbAvailableCharms()
                    # fails, we don't want to re-queue this ID.
                    id = None
                    priority = 0

            except BrowserUnavailable:
                # We consider this profil hasn't been [correctly] analysed
                if id is not None:
                    self._queue.append((priority, id))
        finally:
            self.save()
