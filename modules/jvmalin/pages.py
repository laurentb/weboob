# -*- coding: utf-8 -*-

import re
import datetime

from weboob.capabilities.travel import RoadmapError
from weboob.tools.misc import to_unicode
from weboob.deprecated.mech import ClientForm
from weboob.deprecated.browser import Page


class RoadmapAmbiguity(RoadmapError):
    def __init__(self, error):
        RoadmapError.__init__(self, error)


class RoadmapSearchPage(Page):
    def search(self, departure, arrival, departure_time, arrival_time):
        match = -1
        i = 0
        for form in self.browser.forms():
            try:
                if form.attrs['id'] == 'rech-iti':
                    match = i
            except KeyError:
                pass
            i += 1

        self.browser.select_form(nr=match)
        self.browser['Departure'] = departure
        self.browser['Destination'] = arrival

        time = None
        if departure_time:
            self.browser['sens'] = ['1']
            time = departure_time
        elif arrival_time:
            self.browser['sens'] = ['-1']
            time = arrival_time

        if time:
            try:
                self.browser['dateFull'] = '%02d/%02d/%d' % (time.day, time.month, time.year)
                self.browser['hour'] = ['%02d' % time.hour]
                self.browser['minute'] = ['%02d' % (time.minute - (time.minute % 5))]
            except ClientForm.ItemNotFoundError:
                raise RoadmapError('Unable to establish a roadmap with %s time at "%s"' % ('departure' if departure_time else 'arrival', time))
        self.browser.submit()


class RoadmapResultsPage(Page):
    def html_br_strip(self, text):
        return "".join([l.strip() for l in text.split("\n")]).strip().replace(' ', '%20')

    def find_best(self):
        if len(self.parser.select(self.document.getroot(), 'img.img-error')) > 0:
            if len(self.parser.select(self.document.getroot(), 'form#iti-ambi')) > 0:
                raise RoadmapAmbiguity('Ambigious stop name')
            else:
                raise RoadmapError('Error when submitting form')

        best = self.parser.select(self.document.getroot(), 'div.alerte-bloc-important div.bloc-iti')
        if len(best) == 0:
            best = self.parser.select(self.document.getroot(), 'div.bloc-iti')
            if len(best) == 0:
                raise RoadmapError('Unable to get the best roadmap')

        link = self.parser.select(best[0], 'a.btn-submit')
        if len(link) == 0:
            raise RoadmapError('Unable to get a link to best roadmap')

        return self.html_br_strip(link[0].attrib['href'])

    def resubmit_best_form(self):
        if len(self.parser.select(self.document.getroot(), 'img.img-error')) == 0:
            raise RoadmapError('No error reported!')

        ambi = None
        i = 0
        for form in self.parser.select(self.document.getroot(), 'form'):
            if 'id' in form.attrib and form.attrib['id'] == 'iti-ambi':
                ambi = form
                break
            i += 1

        if ambi is None:
            raise RoadmapError('No ambigous form!')

        props = self.parser.select(ambi, 'span.precision-arret input')
        if len(props) == 0:
            props = self.parser.select(ambi, 'span.precision-adresse input')
            if len(props) == 0:
                raise RoadmapError('Nothing to select to get a roadmap')

        self.browser.select_form(nr=i)
        propname = props[0].attrib['name']
        propvalue = props[0].attrib['value'].encode('utf-8')
        self.browser[propname] = [ propvalue ]
        self.browser.submit()


class RoadmapPage(Page):
    def get_steps(self):
        errors = []
        # for p in self.parser.select(self.document.getroot(), 'p.errors'):
        #    if p.text:
        #        errors.append(p.text.strip())

        if len(errors) > 0:
            raise RoadmapError('Unable to establish a roadmap: %s' % ', '.join(errors))

        current_step = None
        i = 0
        for tr in self.parser.select(self.document.getroot(), 'table.itineraire-detail tr'):
            if current_step is None:
                current_step = {
                    'id': i,
                    'start_time': datetime.datetime.now(),
                    'end_time': datetime.datetime.now(),
                    'line': '',
                    'departure': '',
                    'arrival': '',
                    'duration': datetime.timedelta()
                }

            if 'class' in tr.attrib:
                if 'bg-ligne' in tr.attrib['class']:
                    continue

                if 'iti-map' in tr.attrib['class']:
                    continue

            for td in self.parser.select(tr, 'td'):
                if 'class' not in td.attrib:
                    continue

                if 'iti-inner' in td.attrib['class']:
                    continue

                if 'cell-infos' in td.attrib['class']:
                    if 'id' in td.attrib:
                        if td.attrib['id'].find('MapOpenLink') >= 0:
                            hasA = self.parser.select(td, 'a')
                            if len(hasA) == 0:
                                if len(current_step['line']) > 0 and \
                                   len(current_step['departure']) > 0 and \
                                   len(current_step['arrival']) > 0:
                                    current_step['line'] = to_unicode("%s : %s" %
                                        (current_step['mode'], current_step['line']))
                                    del current_step['mode']
                                    yield current_step
                                    i += 1
                                    current_step = None
                                    continue

                if 'cell-horaires' in td.attrib['class']:
                    # real start
                    for heure in self.parser.select(td, 'span.heure'):
                        if heure.attrib['id'].find('FromTime') >= 0:
                            current_step['start_time'] = self.parse_time(heure.text)
                        if heure.attrib['id'].find('ToTime') >= 0:
                            current_step['end_time'] = self.parse_time(heure.text)
                    for mode in self.parser.select(td, 'span.mode-locomotion img'):
                        current_step['mode'] = mode.attrib['title']

                if 'cell-details' in td.attrib['class']:
                    # If we get a span, it's a line indication,
                    # otherwise check for id containing LibDeparture or
                    # LibDestination
                    spans = self.parser.select(td, 'span.itineraire-ligne')
                    if len(spans) == 1:
                        line = self.html_br_strip(spans[0].text, " ").replace('Ligne ', '')
                        if line.index('- ') == 0:
                            line = re.sub(r'^- ', '', line)
                        current_step['line'] = line

                    elif 'id' in td.attrib:
                        stops = self.parser.select(td, 'strong')
                        stop = self.html_br_strip(stops[0].text, " ")

                        if td.attrib['id'].find('LibDeparture') >= 0:
                            current_step['departure'] = to_unicode(stop)

                        if td.attrib['id'].find('LibDestination') >= 0:
                            current_step['arrival'] = to_unicode(stop)

                            duree = self.parser.select(td, 'span.duree strong')
                            if len(duree) == 1:
                                current_step['duration'] = self.parse_duration(duree[0].text)

    def html_br_strip(self, text, joining=""):
        return joining.join([l.strip() for l in text.split("\n")]).strip()

    def parse_time(self, time):
        time = self.html_br_strip(time)
        h, m = time.split('h')
        return datetime.time(int(h), int(m))

    def parse_duration(self, dur):
        dur = self.html_br_strip(dur)
        m = re.match('(\d+)min', dur)
        if m:
            return datetime.timedelta(minutes=int(m.group(1)))
        m = re.match('(\d+)h(\d+)', dur)
        if m:
            return datetime.timedelta(hours=int(m.group(1)),
                                      minutes=int(m.group(2)))
