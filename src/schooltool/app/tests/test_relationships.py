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
"""
Unit tests for schooltool.app.relationships
"""

import unittest
import doctest

from zope.interface import implements
from zope.component import provideAdapter

from schooltool.app.tests import setUp, tearDown


def doctest_Instruction():
    r"""Tests for Instruction URIs and methods

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.app.relationships import enforceInstructionConstraints
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceInstructionConstraints)

    We will need some sample persons and sections for the demonstration

        >>> from schooltool.person.person import Person
        >>> from schooltool.course.section import Section
        >>> jonas = Person()
        >>> petras = Person()
        >>> developers = Section()
        >>> admins = Section()

    There are some constraints: Only objects providing ISection can be
    Sections.

        >>> from schooltool.app.relationships import Instruction
        >>> Instruction(instructor=jonas, section=petras)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_CourseSections():
    r"""Tests for CourseSections relationship

    Lets import the pieces of CourseSections

        >>> from schooltool.app.relationships import CourseSections
        >>> from schooltool.app.relationships import enforceCourseSectionConstraint

    Relationship tests require some setup:

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceCourseSectionConstraint)

    We will need a course and several sections:

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schooltool.person.person import Person
        >>> history = courses['history'] = Course()
        >>> section1 = sections['1'] = Section(title = "section1")
        >>> section2 = sections['2'] = Section(title = "section2")
        >>> section3 = sections['3'] = Section(title = "section3")
        >>> section4 = sections['4'] = Section(title = "section4")
        >>> person = Person()

    Our course doesn't have any sections yet:

        >>> for section in history.sections:
        ...     print section

    Lets add one:

        >>> history.sections.add(section1)
        >>> for section in history.sections:
        ...     print section.title
        section1

    Lets try to add a person to the course:

        >>> history.sections.add(person)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    Lets try to add a course to the course:

        >>> algebra = Course()
        >>> history.sections.add(algebra)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    No luck, you can only add sections:

        >>> history.sections.add(section2)
        >>> history.sections.add(section3)
        >>> for section in history.sections:
        ...     print section.title
        section1
        section2
        section3

    You can use the Relationship to relate sections and courses:

        >>> CourseSections(course=history, section=section4)
        >>> for section in history.sections:
        ...     print section.title
        section1
        section2
        section3
        section4

    That's it:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def getSectionCalendar(section):
    return section.calendar


from zope.annotation.interfaces import IAttributeAnnotatable
from persistent import Persistent
class CalendarStub(Persistent):
    implements(IAttributeAnnotatable)
    def __init__(self, section):
        self.title = section.title
        self.__parent__ = section


def doctest_updateInstructorCalendars():
    r"""
        >>> from schooltool.app.relationships import updateInstructorCalendars
        >>> from schooltool.app.relationships import URIInstruction
        >>> from schooltool.app.relationships import URISection, URIInstructor
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> from schooltool.course.interfaces import ISection
        >>> from schooltool.relationship.interfaces import \
        ...                                         IRelationshipAddedEvent
        >>> from schooltool.relationship.interfaces import \
        ...                                         IRelationshipRemovedEvent
        >>> from schooltool.person.person import Person
        >>> from schooltool.course.section import Section
        >>> from schooltool.relationship.tests import setUp, tearDown

        >>> provideAdapter(getSectionCalendar,
        ...                adapts=(ISection,),
        ...                provides=ISchoolToolCalendar)

        >>> from schooltool.app.overlay import ICalendarOverlayInfo

        >>> class AddEventStub(dict):
        ...     rel_type = URIInstruction
        ...     implements(IRelationshipAddedEvent)

        >>> class RemoveEventStub(dict):
        ...     rel_type = URIInstruction
        ...     implements(IRelationshipRemovedEvent)

        >>> class OtherEventStub(dict):
        ...     rel_type = URIInstruction

        >>> person = persons['person'] = Person('person')
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> section = sections['sectionA'] = Section(title="SectionA")
        >>> section.calendar = CalendarStub(section)

    When the person is made the instructor of a section the sections calendar
    is added to the overlaid calendars:

        >>> add = AddEventStub()
        >>> add[URIInstructor] = person
        >>> add[URISection] = section
        >>> updateInstructorCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionA']

    The calendar of the section is visible.

        >>> [cal.show for cal in person.overlaid_calendars]
        [True]

    The calendar is removed when the instructor is no longer in the section:

        >>> remove = RemoveEventStub()
        >>> remove[URIInstructor] = person
        >>> remove[URISection] = section
        >>> updateInstructorCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If a person allready has that calendar nothing changes:

        >>> sectionb = sections['sectionB'] = Section(title="SectionB")
        >>> sectionb.calendar = CalendarStub(sectionb)
        >>> person.overlaid_calendars.add(sectionb.calendar)
        <...CalendarOverlayInfo object at ...>
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

        >>> add = AddEventStub()
        >>> add[URIInstructor] = person
        >>> add[URISection] = sectionb
        >>> updateInstructorCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

    If the person removes the calendar manually, that's ok:

        >>> person.overlaid_calendars.remove(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []


        >>> remove = RemoveEventStub()
        >>> remove[URIInstructor] = person
        >>> remove[URISection] = sectionb
        >>> updateInstructorCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    Events that aren't RelationshipAdded/Removed are ignored:

        >>> other = OtherEventStub()
        >>> other[URIInstructor] = person
        >>> other[URISection] = sectionb
        >>> updateInstructorCalendars(other)

        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []


        >>> tearDown()

    """


def doctest_updateStudentCalendars():
    r"""
        >>> from schooltool.app.relationships import updateStudentCalendars
        >>> from schooltool.app.membership import URIMembership
        >>> from schooltool.app.membership import URIGroup, URIMember
        >>> from schooltool.relationship.interfaces import \
        ...                                         IRelationshipAddedEvent
        >>> from schooltool.relationship.interfaces import \
        ...                                         IRelationshipRemovedEvent
        >>> from schooltool.course.section import Section
        >>> from schooltool.person.person import Person
        >>> from schooltool.relationship.tests import setUp, tearDown

        >>> from schooltool.course.interfaces import ISection
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> provideAdapter(getSectionCalendar,
        ...                adapts=(ISection,),
        ...                provides=ISchoolToolCalendar)

        >>> from schooltool.app.overlay import ICalendarOverlayInfo

        >>> class AddEventStub(dict):
        ...     rel_type = URIMembership
        ...     implements(IRelationshipAddedEvent)

        >>> class RemoveEventStub(dict):
        ...     rel_type = URIMembership
        ...     implements(IRelationshipRemovedEvent)

        >>> class OtherEventStub(dict):
        ...     rel_type = URIMembership

        >>> person = persons['p'] = Person('p')
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> section = sections['a'] = Section(title="SectionA")
        >>> section.calendar = CalendarStub(section)

    When the person is made a member of a section the sections calendar
    is added to the overlaid calendars:

        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = section
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionA']

    The calendar of the section is visible.

        >>> [cal.show for cal in person.overlaid_calendars]
        [True]

    The calendar is removed when the person is no longer in the section:

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = person
        >>> remove[URIGroup] = section
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If a person already has that calendar nothing changes:

        >>> sectionb = sections['b'] = Section(title="SectionB")
        >>> sectionb.calendar = CalendarStub(sectionb)
        >>> person.overlaid_calendars.add(sectionb.calendar)
        <...CalendarOverlayInfo object at ...>
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = sectionb
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

    If the person removes the calendar manually, that's ok for now, we may
    want to take away this ability later.

        >>> person.overlaid_calendars.remove(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = person
        >>> remove[URIGroup] = sectionb
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    Events that aren't RelationshipAdded/Removed are ignored:

        >>> other = OtherEventStub()
        >>> other[URIMember] = person
        >>> other[URIGroup] = sectionb
        >>> updateStudentCalendars(other)

        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If you add a person to a Group that isn't a section, nothing happens, the
    user will have to overlay the calendar manually:

        >>> from schooltool.group.group import Group
        >>> person = Person('p2')
        >>> group = Group()
        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = group
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    You can add a group to a section and it's members overlay list will be
    updated:

        >>> student = persons['p3'] = Person('p3')
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> freshmen = groups['freshmen'] = Group()
        >>> freshmen.members.add(student)
        >>> section = sections['math'] = Section("Freshmen Math")
        >>> section.calendar = CalendarStub(section)
        >>> add = AddEventStub()
        >>> add[URIMember] = freshmen
        >>> add[URIGroup] = section
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in student.overlaid_calendars]
        ['Freshmen Math']

        >>> [cal.show for cal in student.overlaid_calendars]
        [True]

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = freshmen
        >>> remove[URIGroup] = section
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in student.overlaid_calendars]
        []

        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                     optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app.relationships',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
