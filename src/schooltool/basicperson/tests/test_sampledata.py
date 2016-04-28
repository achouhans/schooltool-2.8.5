#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
"""Unit tests for schooltool.basicperson.sampledata
"""

import unittest
import doctest
from transaction import abort

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.container.btree import BTreeContainer
from zope.interface import Interface
from zope.interface.verify import verifyObject

from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.testing import setup as stsetup
from schooltool.testing.stubs import AppStub


def doctest_SampleStudents():
    """A sample data plugin that generates students

        >>> from schooltool.basicperson.sampledata import SampleStudents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleStudents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin simply creates a 1000 persons with random names and
    usernames of a form 'student123'.

        >>> plugin.power
        1000

        >>> students = IGroupContainer(app)['students']

        >>> len(students.members)
        0

        >>> plugin.generate(app, 42)

        >>> len(students.members)
        1000

        >>> for i in range(5):
        ...     print app['persons']['student%03d' % i].title
        Freja Freeman
        Klara Phillips
        Cath Rodriguez
        Daniela Petersen
        Gabbie Cunningham

    The students get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'student%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_SampleTeachers():
    """A sample data plugin that generates teachers

        >>> from schooltool.basicperson.sampledata import SampleTeachers
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTeachers()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin creates this many teachers:

        >>> plugin.power
        48

    This plugin creates a number of teachers and adds them to the
    Teachers group.

        >>> teachers = IGroupContainer(app)['teachers']

        >>> len(teachers.members)
        0

        >>> plugin.generate(app, 42)
        >>> len(teachers.members)
        48

    Teachers' names are different from the students' names above:

        >>> for i in range(5):
        ...     teacher = app['persons']['teacher%03d' % i]
        ...     print teacher.title
        Catherine Martin
        Kimmy Cooper
        Helen Patterson
        Iris Laurent
        Philippa Stewart

    The teachers get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'teacher%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_SamplePersonalEvents():
    """A sample data plugin that generates random personal events.

        >>> from schooltool.basicperson.sampledata import SamplePersonalEvents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SamplePersonalEvents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> from schooltool.basicperson.sampledata import SampleStudents
        >>> from schooltool.basicperson.sampledata import SampleTeachers
        >>> from schooltool.term.sampledata import SampleTerms
        >>> plugin_students = SampleStudents()
        >>> plugin_students.power = 20
        >>> plugin_teachers = SampleTeachers()
        >>> plugin_teachers.power = 3
        >>> plugin_terms = SampleTerms()
        >>> plugin_terms.generate(app, 42)
        >>> plugin_students.generate(app, 42)
        >>> plugin_teachers.generate(app, 42)

    Probability of person having event on any day in percents:

        >>> plugin.probability
        2

        >>> plugin.probability = 50

    Create random events for all students and teachers.

        >>> plugin.generate(app, 42)

        >>> for i in range(5):
        ...     person = app['persons']['student%03d' % i]
        ...     calendar = ISchoolToolCalendar(person)
        ...     print len(calendar)
        233
        250
        227
        252
        248

        >>> person = app['persons']['teacher000']
        >>> calendar = ISchoolToolCalendar(person)
        >>> len(calendar)
        240

        >>> events = list(calendar)
        >>> events.sort()
        >>> for event in events[0:5]:
        ...     print event.dtstart,
        ...     print event.duration,
        ...     print event.title
        2005-08-24 12:00:00+00:00 5:00:00 Tribal dances
        2005-08-25 17:30:00+00:00 1:30:00 Dentist
        2005-08-27 11:30:00+00:00 4:00:00 Concert
        2005-08-28 23:30:00+00:00 3:30:00 Quake tournament
        2005-08-29 19:00:00+00:00 6:00:00 Boating
    """


def setUp(test):
    setup.placefulSetUp()
    zcml = stsetup.getIntegrationTestZCML()
    zcml.include('schooltool.schoolyear', file='schoolyear.zcml')
    app = AppStub()
    app['persons'] = BTreeContainer()

    from schooltool.term.term import getTermContainer
    from schooltool.term.interfaces import ITermContainer
    from schooltool.schoolyear.schoolyear import getSchoolYearContainer
    provideAdapter(getTermContainer, [Interface], ITermContainer)
    provideAdapter(getSchoolYearContainer)

    from schooltool.group.group import GroupContainer, Group
    groups = app['groups'] = GroupContainer()
    provideAdapter(lambda context: groups,
                   adapts=[ISchoolToolApplication],
                   provides=IGroupContainer)
    groups['teachers'] = Group('Teachers')
    groups['students'] = Group('Students')

    from zope.annotation.interfaces import IAnnotatable
    from schooltool.relationship.interfaces import IRelationshipLinks
    from schooltool.relationship.annotatable import getRelationshipLinks
    provideAdapter(getRelationshipLinks, [IAnnotatable], IRelationshipLinks)

    from schooltool.app.cal import getCalendar
    from schooltool.app.interfaces import ISchoolToolCalendar
    from schooltool.person.interfaces import IPerson
    provideAdapter(getCalendar, [IPerson], ISchoolToolCalendar)
    test.globs.update({
        'app': app,
    })


def tearDown(test):
    setup.placefulTearDown()
    abort()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
