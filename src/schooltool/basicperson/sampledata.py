#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Basic person sample data generation
"""
import datetime
import os
from pytz import utc

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.basicperson.person import BasicPerson
from schooltool.sampledata import PortableRandom
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata.name import NameGenerator
from schooltool.group.interfaces import IGroupContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.cal import CalendarEvent
from schooltool.common import DateRange


class ChoiceGenerator(object):
    def __init__(self, seed, choices):
        self.random = PortableRandom(seed)
        self.choices = choices

    def generate(self):
        return self.random.choice(self.choices)


class SampleStudents(object):

    implements(ISampleDataPlugin)

    name = 'students'
    dependencies = ('terms', )

    # Number of persons to generate
    power = 1000

    def personFactory(self, namegen, prefixgen, gendergen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'student%03d' % count
        person = BasicPerson(person_id, first_name, last_name)
        person.setPassword(person_id)
        person.gender = gendergen.generate()
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        prefixgen = ChoiceGenerator(str(seed), ['Mr', 'Mrs', 'Miss', ''])
        gendergen = ChoiceGenerator(str(seed), ['male', 'female'])

        students = IGroupContainer(app)['students']
        for count in range(self.power):
            person = self.personFactory(namegen, prefixgen, gendergen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            app['persons'][person.username] = person
            removeSecurityProxy(students.members).add(person)


class SampleTeachers(object):
    implements(ISampleDataPlugin)

    name = 'teachers'
    dependencies = ('terms', )

    # Number of teachers to generate
    power = 48

    def personFactory(self, namegen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'teacher%03d' % count
        person = BasicPerson(person_id, first_name, last_name)
        person.setPassword(person_id)
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        teachers = IGroupContainer(app)['teachers']
        for count in range(self.power):
            person = self.personFactory(namegen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            app['persons'][person.username] = person
            removeSecurityProxy(teachers.members).add(person)


class SamplePersonalEvents(object):
    """Sample data plugin class that generates personal random events."""

    implements(ISampleDataPlugin)

    name = 'personal_events'
    dependencies = ('students', 'teachers', 'terms')

    probability = 2     # probability of having an event on any day

    def _readLines(self, filename):
        """Read in lines from file

        Filename is relative to the module.
        Returned lines are stripped.
        """
        fullpath = os.path.join(os.path.dirname(__file__), filename)
        lines = file(fullpath).readlines()
        return [line.strip() for line in lines]

    def generate(self, app, seed=None):
        self.random = PortableRandom(seed)
        event_titles = self._readLines('event_titles.txt')
        person_ids = [person for person in app['persons'].keys()
                      if person.startswith('student') or
                         person.startswith('teacher')]
        dates = []
        for term in ITermContainer(app).values():
            dates.append(term.first)
            dates.append(term.last)
        first = min(dates)
        last = max(dates)
        days = DateRange(first, last)
        for person_id in person_ids:
            person = app['persons'][person_id]
            calendar = ISchoolToolCalendar(person)
            for day in days:
                if self.random.randrange(0, 100) < self.probability:
                    event_title = self.random.choice(event_titles)
                    time_hour = self.random.randint(6, 23)
                    time_min = self.random.choice((0, 30))
                    event_time = datetime.datetime(day.year,
                                                   day.month,
                                                   day.day,
                                                   time_hour,
                                                   time_min,
                                                   tzinfo=utc)
                    event_duration = datetime.timedelta(
                                       minutes=self.random.randint(1, 12)*30)
                    event = CalendarEvent(event_time,
                                          event_duration,
                                          event_title)
                    calendar.addEvent(event)

