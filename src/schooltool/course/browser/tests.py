# -*- coding: utf-8 -*-
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
Unit tests for course and section views.
"""
import unittest
import doctest

from zope.i18n import translate
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.publisher.browser import BrowserView
from zope.traversing.interfaces import IContainmentRoot
from zope.component import provideAdapter

from schooltool.course.tests import setUp, tearDown


class AddingStub(BrowserView):
    pass

def doctest_CourseContainerView():
    r"""View for the courses container.

        >>> from schooltool.course.browser.course import CourseContainerView
        >>> from schooltool.course.course import CourseContainer
        >>> cc = CourseContainer()
        >>> request = TestRequest()
        >>> view = CourseContainerView(cc, request)

    """


def doctest_CourseView():
    r"""View for courses.

    Lets create a simple view for a course:

        >>> from schooltool.course.browser.course import CourseView
        >>> from schooltool.course.course import Course
        >>> course = Course(title="Algebra 1")
        >>> request = TestRequest()
        >>> view = CourseView(course, request)

    And look at the course details.

        >>> print view.details
        []

    Add some details and check again.

        >>> course.course_id = u'Course1'
        >>> course.government_id = u'GovC1'
        >>> course.credits = 1
        >>> [sorted(detail.items()) for detail in view.details]
        [[('title', u'Course ID'),    ('value', u'Course1')],
         [('title', u'Alternate ID'), ('value', u'GovC1')],
         [('title', u'Credits'),      ('value', 1)]]

    Empty values are hidden.

        >>> course.course_id = u''
        >>> course.government_id = u'   '
        >>> course.credits = 0
        >>> [sorted(detail.items()) for detail in view.details]
        [[('title', u'Credits'), ('value', 0)]]

    """


def doctest_CourseAddView():
    r"""

        >>> from schooltool.course.browser.course import CourseAddView
        >>> from schooltool.course.course import Course
        >>> from schooltool.course.interfaces import ICourse

        >>> class CourseAddViewForTesting(CourseAddView):
        ...     schema = ICourse
        ...     fieldNames = ('title', 'description')
        ...     _factory = Course

        >>> from schooltool.course.course import CourseContainer
        >>> container = CourseContainer()
        >>> request = TestRequest()
        >>> context = AddingStub(container, request)
        >>> context = container

        >>> view = CourseAddViewForTesting(context, request)
        >>> view.update()

        >>> request = TestRequest()
        >>> request.form = {'field.title' : 'math'}
        >>> context = AddingStub(context, request)
        >>> view = CourseAddViewForTesting(context, request)
        >>> view.update()

    """


def doctest_CourseCSVImporter():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.course.browser.csvimport import CourseCSVImporter
        >>> from schooltool.course.course import CourseContainer
        >>> container = courses
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description
        ... Course2,,course2_local,course2_gov,5   
        ... Course3, Course 3 Description,,,10
        ... Course 4, Course 4 description, local_course4, gov_course4\n\n\n'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the courses exist

        >>> [course for course in container]
        [u'course-1', u'course2_local', u'course3', u'local_course4']

    Check that descriptions were imported properly

        >>> [course.title for course in container.values()]
        ['Course 1', 'Course2', 'Course3', 'Course 4']
        
        >>> [course.description for course in container.values()]
        ['Course 1 Description', '', 'Course 3 Description', 'Course 4 description']
        
        >>> [course.course_id for course in container.values()]
        [None, 'course2_local', None, 'local_course4']
        
        >>> [course.government_id for course in container.values()]
        [None, 'course2_gov', None, 'gov_course4']

        >>> [course.credits for course in container.values()]
        [None, Decimal('5'), Decimal('10'), None]

    """


def doctest_CourseCSVImporter_invalid_id():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.course.browser.csvimport import CourseCSVImporter
        >>> from schooltool.course.course import CourseContainer
        >>> container = CourseContainer()
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description, +foo'''
        >>> importer.importFromCSV(csvdata)
        False

    We should get an error, because the id is invalid:

        >>> for error in importer.errors.fields:
        ...     print translate(error)
        Course "Course 1" id "+foo" is invalid. Names cannot begin with '+' or '@' or contain '/'

    """


def doctest_CourseCSVImporter_invalid_credits():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.course.browser.csvimport import CourseCSVImporter
        >>> from schooltool.course.course import CourseContainer
        >>> container = CourseContainer()
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description, course1_local, , 34.3
        ... Course3,, course3, , 2+2
        ... Course2,,,,invalid'''
        >>> importer.importFromCSV(csvdata)
        False

    We should get an error, because the credits value is not a number:

        >>> for error in importer.errors.fields:
        ...     print translate(error)
        Course "Course3" credits "2+2" value must be a number.
        Course "Course2" credits "invalid" value must be a number.

    Note that 34.3 is a valid value number.

    """


def doctest_CourseCSVImporter_reimport():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.course.browser.csvimport import CourseCSVImporter
        >>> from schooltool.course.course import CourseContainer
        >>> container = courses
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description
        ... Course2,,course-2, course-2-gov, 10   ,
        ... Course3, Course 3 Description,,course-3-gov\n\n\n'''
        >>> importer.importFromCSV(csvdata)
        True


    Check that the courses exist

        >>> [course for course in container]
        [u'course-1', u'course-2', u'course3']

    Check that titles were imported properly

        >>> [course.title for course in container.values()]
        ['Course 1', 'Course2', 'Course3']

    Check that descriptions were imported properly

        >>> [course.description for course in container.values()]
        ['Course 1 Description', '', 'Course 3 Description']

    Check that course ids were imported properly

        >>> [course.course_id for course in container.values()]
        [None, 'course-2', None]

    Check that goverment ids were imported properly

        >>> [course.government_id for course in container.values()]
        [None, 'course-2-gov', 'course-3-gov']

    Check that credits were imported properly

        >>> [course.credits for course in container.values()]
        [None, Decimal('10'), None]

    Now import a different CSV with some courses matching:

        >>> csvdata='''Course 1, Course Description
        ... Course2,             ,course-2,,20
        ... Course4, Course 4 Description\n\n\n'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the courses exist

        >>> [course for course in container]
        [u'course-1', u'course-2', u'course3', u'course4']

    Check that descriptions were updated properly

        >>> [course.description for course in container.values()]
        ['Course Description', '', 'Course 3 Description', 'Course 4 Description']

    Check that credits were imported properly

        >>> [course.credits for course in container.values()]
        [None, Decimal('20'), None, None]

    By the way - ID takes precedence over title so if we import:

        >>> csvdata='''Course4, Description, course3'''
        >>> importer.importFromCSV(csvdata)
        True

    We definitely get the same amount of courses

        >>> [course for course in container]
        [u'course-1', u'course-2', u'course3', u'course4']

    But description and title of the course3 have been changed:

        >>> container['course3'].title
        'Course4'

        >>> container['course3'].description
        'Description'

    While course 4 hasn't been modified:

        >>> container['course4'].title
        'Course4'

        >>> container['course4'].description
        'Course 4 Description'

    """


def doctest_CourseCSVImportView():
    r"""
    We'll create a course csv import view

        >>> from schooltool.course.browser.csvimport import CourseCSVImportView
        >>> from schooltool.course.course import CourseContainer
        >>> from zope.publisher.browser import TestRequest
        >>> container = courses
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : u"A Course, The best Course, some-course\nAnother Course,,,,5\nEspañol, Descripción, spanish, spanish-gov, 20\n\n",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> sorted([course for course in container])
        [u'another-course', u'some-course', u'spanish']
        >>> [container[key].course_id for key in sorted(container)]
        [None, u'some-course', u'spanish']
        >>> [container[key].government_id for key in sorted(container)]
        [None, None, u'spanish-gov']
        >>> [container[key].credits for key in sorted(container)]
        [Decimal('5'), None, Decimal('20')]

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line starts with a comma (no title)

        >>> request.form = {'csvtext' : u", No title provided here",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'Titles may not be empty']

    """


def doctest_SectionContainerView():
    r"""View for the sections container.

        >>> from schooltool.course.browser.section import SectionContainerView
        >>> from schooltool.course.section import SectionContainer
        >>> sc = SectionContainer()
        >>> request = TestRequest()
        >>> view = SectionContainerView(sc, request)

    """


def doctest_SectionView():
    r"""View for sections

    Lets create a simple view for a section:

        >>> from schooltool.course.browser.section import SectionView
        >>> from schooltool.course.section import Section
        >>> section = sections['section'] = Section()
        >>> request = TestRequest()
        >>> view = SectionView(section, request)

    Stub a table formatter.

        >>> class TableFormatterStub(object):
        ...     def __init__(self, container, request):
        ...         self.container = container
        ...     def setUp(self, table_formatter=None, items=[], batch_size=0):
        ...         self.items = items
        ...         self.table_formatter = table_formatter
        ...     def render(self):
        ...         print 'Rendering persons from %s, using %s:' % (
        ...             self.container, self.table_formatter)
        ...         for item in self.items:
        ...             print item.title

        >>> from zope.publisher.interfaces.http import IHTTPRequest
        >>> from schooltool.person.interfaces import IPersonContainer

        >>> from schooltool.person.person import Person
        >>> from schooltool.table.interfaces import ITableFormatter
        >>> provideAdapter(lambda p, r: TableFormatterStub(p, r),
        ...                adapts=(IPersonContainer, IHTTPRequest),
        ...                provides=ITableFormatter)

    Let's add some students.

        >>> person1 = persons['p1'] = Person('Person1', 'Person1')
        >>> person2 = persons['p2'] = Person('Person2', 'Person2')
        >>> person3 = persons['p3'] = Person('Person3', 'Person3')
        >>> section.members.add(person1)
        >>> section.members.add(person2)
        >>> section.members.add(person3)

    And render the person table.

        >>> view.renderPersonTable()
        Rendering persons from <...PersonContainer ...>,
        using <class 'zc.table.table.StandaloneFullFormatter'>:
        Person1
        Person2
        Person3

    """


def doctest_SectionEditView():
    r"""Test for SectionEditView

    Let's create a view for editing a section:

        >>> from schooltool.course.browser.section import SectionEditView
        >>> from schooltool.course.section import Section
        >>> from schooltool.course.interfaces import ISection

    We need some setup:

        >>> from schooltool.resource.resource import Location
        >>> app['resources']['room1'] = room1 = Location("Room 1")

        >>> section = Section()
        >>> directlyProvides(section, IContainmentRoot)
        >>> request = TestRequest()

        >>> class TestSectionEditView(SectionEditView):
        ...     schema = ISection
        ...     fieldNames = ('title', 'description')
        ...     _factory = Section

        >>> view = TestSectionEditView(section, request)

    We should not get redirected if we did not click on apply button:

        >>> request = TestRequest()
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        599

    After changing name of the section you should get redirected to the
    container:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> section.title
        u'new_title'

    Even if the title has not changed you should get redirected to the section
    list:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> section.title
        u'new_title'

    We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    """


def doctest_SectionMemberCSVImporter():
    r"""Tests for SectionMemberCSVImporter.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> from schooltool.course.section import PersonLearnerAdapter
        >>> school = app

        >>> persons = school['persons']
        >>> smith = persons['smith'] = Person('smith', 'John Smith')
        >>> [section.title for section in PersonLearnerAdapter(smith).sections()]
        []
        >>> jones = persons['jones'] = Person('jones', 'Sally Jones')
        >>> [section.title for section in PersonLearnerAdapter(jones).sections()]
        []
        >>> stevens = persons['stevens'] = Person('stevens', 'Bob Stevens')
        >>> [section.title for section in PersonLearnerAdapter(stevens).sections()]
        []

    Create a section and an importer

        >>> from schooltool.course.browser.csvimport import SectionMemberCSVImporter
        >>> from schooltool.course.section import Section
        >>> section = sections['section'] = Section('Section title', 'Section description')
        >>> [person.username for person in section.members]
        []
        >>> importer = SectionMemberCSVImporter(section, None)

    Import some sample data

        >>> csvdata='''smith
        ... stevens\n\n\n'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the persons were added to the section members:

        >>> [person.username for person in section.members]
        ['smith', 'stevens']
        >>> [section.title for section in PersonLearnerAdapter(smith).sections()]
        ['Section title']
        >>> [section.title for section in PersonLearnerAdapter(jones).sections()]
        []
        >>> [section.title for section in PersonLearnerAdapter(stevens).sections()]
        ['Section title']

    Create another section and another importer

        >>> another_section = sections['another'] = Section('Another section', 'Another description')
        >>> [person.username for person in another_section.members]
        []
        >>> another_importer = SectionMemberCSVImporter(another_section, None)

    Import some more data

        >>> csvdata='''stevens
        ... jones\n\n\n'''
        >>> another_importer.importFromCSV(csvdata)
        True

    Check that the persons were added to the another section members:

        >>> [person.username for person in another_section.members]
        ['stevens', 'jones']
        >>> [section.title for section in PersonLearnerAdapter(smith).sections()]
        ['Section title']
        >>> [section.title for section in PersonLearnerAdapter(jones).sections()]
        ['Another section']
        >>> [section.title for section in PersonLearnerAdapter(stevens).sections()]
        ['Section title', 'Another section']

    """


def doctest_SectionMemberCSVImportView():
    r"""Tests for SectionMemberCSVImportView

    First we need to set up some persons:

        >>> from zope.i18n import translate
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> school = app

        >>> persons = school['persons']
        >>> smith = persons['smith'] = Person('smith', 'John Smith')
        >>> jones = persons['jones'] = Person('jones', 'Sally Jones')
        >>> stevens = persons['stevens'] = Person('stevens', 'Bob Stevens')

    We'll create a section member csv import view

        >>> from schooltool.course.browser.csvimport import \
        ...      SectionMemberCSVImportView
        >>> from schooltool.course.section import Section
        >>> from zope.publisher.browser import TestRequest
        >>> section = sections['section'] = Section('Section title', 'Section description')
        >>> request = TestRequest()

    Now we'll try a text import.

        >>> request.form = {
        ...     'csvtext' : u'stevens\n',
        ...     'charset' : 'UTF-8',
        ...     'UPDATE_SUBMIT': 1}
        >>> view = SectionMemberCSVImportView(section, request)
        >>> view.update()
        >>> [person.username for person in section.members]
        ['stevens']

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view = SectionMemberCSVImportView(section, request)
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line doesn't have a username

        >>> request.form = {'csvtext' : u" ,stevens\njones,Sally",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = SectionMemberCSVImportView(section, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'User names must not be empty.']

    Or if the username is not in the persons container

        >>> request.form = {'csvtext' : u"foobar\nstevens\njones",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = SectionMemberCSVImportView(section, request)
        >>> view.update()
        >>> [translate(error) for error in view.errors]
        [u'Failed to import CSV text', u'"foobar" is not a valid username.']

    """


def doctest_SectionInstructorView():
    """Tests for SectionInstructorView.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> school = app
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> persons['smith'] = Person('smith', 'John Smith')
        >>> persons['jones'] = Person('jones', 'Sally Jones')
        >>> persons['stevens'] = Person('stevens', 'Bob Stevens')

    getCollection plainly returns instructors attribute of a section:

        >>> from schooltool.course.browser.section import SectionInstructorView
        >>> class SectionStub(object):
        ...     instructors = [persons['smith']]
        >>> view = SectionInstructorView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['John Smith']

    All persons that are not in the current instructor list are
    considered available:

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'Bob Stevens']

        >>> view.context.instructors = []

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'John Smith', 'Bob Stevens']

    """


def doctest_SectionLearnerView():
    """Tests for SectionLearnerView.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> school = app
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> smith = persons['smith'] = Person('smith', 'John Smith')
        >>> jones = persons['jones'] = Person('jones', 'Sally Jones')
        >>> stevens = persons['stevens'] = Person('stevens', 'Bob Stevens')

    getCollection plainly returns members attribute of a section:

        >>> from schooltool.course.browser.section import SectionLearnerView
        >>> class SectionStub(object):
        ...     members = [smith]
        >>> view = SectionLearnerView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['John Smith']

    All persons that are not in the selected learner list are
    considered available:

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'Bob Stevens']

        >>> view.context.members = []

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'John Smith', 'Bob Stevens']

    Any non-person members should be skipped when displaying selected
    items:

        >>> from schooltool.group.group import Group
        >>> frogs = Group('frogs')
        >>> view.context.members = [smith, frogs]
        >>> [item.title for item in view.getSelectedItems()]
        ['John Smith']

    """


def doctest_CoursesViewlet():
    r"""Test for CoursesViewlet

    Adapters:

        >>> from zope.ucol.localeadapter import LocaleCollator
        >>> from zope.component import provideAdapter, provideUtility
        >>> from zope.i18n.interfaces.locales import ICollator
        >>> from zope.i18n.interfaces.locales import ILocale
        >>> from schooltool.course.section import PersonInstructorAdapter
        >>> from schooltool.course.section import PersonLearnerAdapter
        >>> from schooltool.course.interfaces import ISection
        >>> from schooltool.term.interfaces import ITerm
        >>> from schooltool.schoolyear.interfaces import ISchoolYear
        >>> provideAdapter(LocaleCollator, [ILocale], ICollator)
        >>> provideAdapter(PersonInstructorAdapter)
        >>> provideAdapter(PersonLearnerAdapter)
        >>> class DummySchoolYear(object):
        ...     title = '2010'
        ...     first = 'date'
        >>> class DummyTerm(object):
        ...     title = 'Semester'
        ...     first = 'date'
        >>> year2010 = DummySchoolYear()
        >>> semester = DummyTerm()
        >>> def DummySchoolYearSectionAdapter(section):
        ...     return year2010
        >>> def DummyTermSectionAdapter(section):
        ...     return semester
        >>> provideAdapter(DummySchoolYearSectionAdapter, [ISection], ISchoolYear)
        >>> provideAdapter(DummyTermSectionAdapter, [ISection], ITerm)

    Let's create a viewlet for a person's courses:

        >>> from schooltool.course.browser.course import CoursesViewlet
        >>> from schooltool.person.person import Person

        >>> school = app
        >>> persons = school['persons']
        >>> from schooltool.course.section import SectionContainer

        >>> persons['teacher'] = teacher = Person("Teacher")
        >>> teacher_view = CoursesViewlet(teacher, TestRequest(), None, None)

    Not a teacher yet:

        >>> teacher_view.update()
        >>> teacher_view.isTeacher()
        False

    We'll need something to teach:

        >>> from schooltool.course.section import Section
        >>> sections['section'] = section1 = Section(title="History")
        >>> sections['section2'] = section2 = Section(title="Algebra")
        >>> section1.instructors.add(teacher)

    Now we're teaching:

        >>> teacher_view.update()
        >>> teacher_view.isTeacher()
        True
        >>> teacher_view.isLearner()
        False

    We'll teach 2 courses this semester, and we'll need an easy way to get a
    list of all the courses we're teaching.

        >>> section2.instructors.add(teacher)
        >>> teacher_view = CoursesViewlet(teacher, TestRequest(), None, None)
        >>> teacher_view.update()
        >>> for schoolyear_data in teacher_view.instructorOf:
        ...     for term in schoolyear_data['terms']:
        ...         for section in term['sections']:
        ...             print section['obj'].title
        Algebra
        History

    Let's create a student

        >>> persons['student'] = student = Person("Student")
        >>> student_view = CoursesViewlet(student, TestRequest(), None, None)
        >>> student_view.update()

        >>> student_view.isTeacher()
        False
        >>> student_view.isLearner()
        False

    Membership in a Section implies being a learner:

        >>> section2.members.add(student)
        >>> student_view.update()
        >>> student_view.isTeacher()
        False

        >>> student_view.isLearner()
        True

        >>> sections['section3'] = section3 = Section(title="English")
        >>> sections['section4'] = section4 = Section(title="Gym")

    Our student is taking several classes

        >>> section3.members.add(student)
        >>> student_view = CoursesViewlet(student, TestRequest(), None, None)
        >>> student_view.update()

        >>> for schoolyear_data in student_view.learnerOf:
        ...     for term in schoolyear_data['terms']:
        ...         for section in term['sections']:
        ...             print section['obj'].title
        Algebra
        English

    """


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
