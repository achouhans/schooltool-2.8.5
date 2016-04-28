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
Unit tests for schooltool.relationship
"""

import unittest
import doctest

from schooltool.relationship.tests import URIStub


def doctest_relate():
    """Tests for relate

    getRelatedObjects relies on adapters to IRelationshipLinks.  For the
    purposes of this test it is simpler to just implement IRelationshipLinks
    directly in the object

        >>> from zope.interface import implements
        >>> from schooltool.relationship.interfaces import IRelationshipLinks

        >>> from schooltool.relationship.relationship import LinkSet
        >>> from schooltool.relationship.uri import URIObject as URIStub
        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> prefix = 'example:'
        >>> class Relatable(LinkSet):
        ...     def add(self, link):
        ...         super(Relatable, self).add(link)
        ...         this = self.__parent__
        ...         print 'Linking %s with %s (the %s in %s)' % (
        ...                 this, link.target, str(link.role.uri).replace(prefix, ''), str(link.rel_type).replace(prefix, ''))
        >>> from schooltool.relationship.annotatable import getRelationshipLinks
        >>> def getLinks(context):
        ...     return getRelationshipLinks(context, Relatable)
        >>> from zope.component import provideAdapter
        >>> from zope.annotation.interfaces import IAnnotatable
        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> provideAdapter(getLinks, [IAnnotatable], IRelationshipLinks)

        >>> fred = persons['fred'] = SomeContainedPersistent('Fred')
        >>> wilma = persons['wilma'] = SomeContainedPersistent('Wilma')

    Now we can test relate

        >>> from schooltool.relationship.relationship import relate

        >>> husband = URIStub('%shusband' % prefix)
        >>> wife = URIStub('%swife' % prefix)

        >>> relate(URIStub('%smarriage' % prefix), (fred, husband), (wilma, wife))
        Linking Fred with Wilma (the wife in marriage)
        Linking Wilma with Fred (the husband in marriage)

    """


def doctest_LinkSet_getTargetsByRole():
    """Tests for getTargetsByRole

        >>> from schooltool.relationship.relationship import LinkSet, Link

        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> abc = persons['abc'] = SomeContainedPersistent('abc')
        >>> from schooltool.relationship.annotatable import getRelationshipLinks
        >>> a = persons['a'] = SomeContainedPersistent('a')
        >>> b = persons['b'] = SomeContainedPersistent('b')
        >>> from schooltool.relationship.uri import URIObject as URIStub
        >>> role_a = URIStub('rel:role_of_a')
        >>> role_b = URIStub('rel:role_of_b')
        >>> from schooltool.relationship.relationship import relate
        >>> relate(URIStub('example:rel'), (a, role_a), (b, role_b))

    Now we can test getTargetsByRole

        >>> role_c = URIStub('rel:role_c')
        >>> obj = getRelationshipLinks(a)
        >>> obj.getTargetsByRole(role_b)
        [b]
        >>> obj.getTargetsByRole(role_c)
        []
        >>> obj = getRelationshipLinks(b)
        >>> obj.getTargetsByRole(role_a)
        [a]
        >>> obj.getTargetsByRole(role_c)
        []

    """


def doctest_RelationshipSchema():
    """Tests for RelationshipSchema

    The constructor takes exactly two keyword arguments

        >>> from schooltool.relationship import RelationshipSchema
        >>> from schooltool.relationship.uri import URIObject as URIStub
        >>> role_mgr = URIStub('example:Mgr')
        >>> role_rpt = URIStub('example:Rpt')
        >>> role_spv = URIStub('example:Spv')
        >>> RelationshipSchema('example:Mgmt', manager=role_mgr,
        ...                    report=role_rpt, supervisor=role_spv)
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.
        >>> RelationshipSchema('example:Mgmt', manager='example:Mgr')
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.

    This works:

        >>> Management = RelationshipSchema(URIStub('example:Mgmt'),
        ...                                 manager=role_mgr,
        ...                                 report=role_rpt)

    You can call relationship schemas

        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> a = persons['a'] = SomeContainedPersistent('a')
        >>> b = persons['b'] = SomeContainedPersistent('b')
        >>> Management(manager=a, report=b)

    You will see that a is b's manager, and b is a's report:

        >>> from schooltool.relationship import getRelatedObjects
        >>> getRelatedObjects(b, role_mgr)
        [a]
        >>> getRelatedObjects(a, role_rpt)
        [b]

    Order of arguments does not matter

        >>> c = persons['c'] = SomeContainedPersistent('c')
        >>> d = persons['d'] = SomeContainedPersistent('d')
        >>> Management(report=c, manager=d)
        >>> getRelatedObjects(c, role_mgr)
        [d]
        >>> getRelatedObjects(d, role_rpt)
        [c]

    You must give correct arguments, though

        >>> Management(report=c, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Missing a 'manager' keyword argument.

        >>> Management(manager=c, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Missing a 'report' keyword argument.

    You should not give extra arguments either

        >>> Management(report=c, manager=b, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Too many keyword arguments.

    """


def doctest_unrelateAll():
    r"""Tests for unrelateAll.

    Nothing happens if the object has no relationships.

        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> a = persons['a'] = SomeContainedPersistent('a')
        >>> from schooltool.relationship import unrelateAll
        >>> events = []
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(events.append)
        >>> unrelateAll(a)
        >>> events
        []

    Suppose that the object has a number of relationships

        >>> from schooltool.relationship import relate
        >>> b = persons['b'] = SomeContainedPersistent('b')
        >>> c = persons['c'] = SomeContainedPersistent('c')
        >>> d = persons['d'] = SomeContainedPersistent('d')

        >>> relationships = [
        ...       ('example:SomeRelationship', (a, 'example:Foo'),
        ...                                    (b, 'example:Bar')),
        ...       ('example:SomeRelationship', (a, 'example:Foo'),
        ...                                    (c, 'example:Bar')),
        ...       ('example:OtherRelationship', (a, 'example:Symmetric'),
        ...                                     (d, 'example:Symmetric')),
        ...       ('example:Loop', (a, 'example:OneEnd'),
        ...                        (a, 'example:OtherEnd')),
        ...       ('example:Loop', (a, 'example:BothEnds'),
        ...                        (a, 'example:BothEnds')),
        ... ]
        >>> for rel_type, (a, rel_a), (b, rel_b) in relationships:
        ...     relate(rel_type, (a, URIStub(rel_a)), (b, URIStub(rel_b)))

    We are not interested in relationship events up to this point

        >>> del events[:]

    We call `unrelateAll` and it suddenly has no relationships

        >>> unrelateAll(a)

        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(a))
        []

    Relationships are broken properly, from both ends

        >>> from schooltool.relationship import getRelatedObjects
        >>> getRelatedObjects(b, URIStub('example:Foo'))
        []

    Also, we got a bunch of events

        >>> from schooltool.relationship.interfaces \
        ...         import IBeforeRemovingRelationshipEvent
        >>> from schooltool.relationship.interfaces \
        ...         import IRelationshipRemovedEvent
        >>> before_removal_events = set([
        ...         (e.rel_type, (e.participant1, e.role1.uri),
        ...                      (e.participant2, e.role2.uri))
        ...         for e in events
        ...         if IBeforeRemovingRelationshipEvent.providedBy(e)])
        >>> before_removal_events == set(relationships)
        True

        >>> removal_events = set([(e.rel_type,
        ...                        (e.participant1, e.role1.uri),
        ...                        (e.participant2, e.role2.uri))
        ...                       for e in events
        ...                       if IRelationshipRemovedEvent.providedBy(e)])
        >>> removal_events == set(relationships)
        True

        >>> zope.event.subscribers[:] = old_subscribers

    """


def doctest_BoundRelationshipProperty():
    """Tests for BoundRelationshipProperty.

    Set up two types of membership.

        >>> from schooltool.relationship.uri import URIObject as URIStub
        >>> role_student = URIStub('example:Student')
        >>> role_instructor = URIStub('example:Instructor')
        >>> role_course = URIStub('example:Course')

        >>> uri_attending = URIStub('example:Attending')
        >>> uri_instruction = URIStub('example:Instruction')

        >>> from schooltool.relationship import RelationshipSchema
        >>> Instruction = RelationshipSchema(uri_instruction,
        ...                                  instructor=role_instructor,
        ...                                  course=role_course)
        >>> Attending = RelationshipSchema(uri_attending,
        ...                                student=role_student,
        ...                                course=role_course)

    Create Course and Person classes.  We will use the RelationshipProperty
    that should bind to an instance as BoundRelationshipProperty.

        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> from schooltool.relationship.relationship import RelationshipProperty

        >>> class Course(SomeContainedPersistent):
        ...     students = RelationshipProperty(
        ...         uri_attending, role_course, role_student)
        ...     instructors = RelationshipProperty(
        ...         uri_instruction, role_course, role_instructor)

        >>> class Person(SomeContainedPersistent):
        ...     attends = RelationshipProperty(
        ...         uri_attending, role_student, role_course)
        ...     instructs = RelationshipProperty(
        ...         uri_instruction, role_instructor, role_course)

    Set up a course with several students.

        >>> course_a = courses['a'] = Course('course A')
        >>> john = persons['john'] = Person('John')
        >>> peter = persons['peter'] = Person('Peter')
        >>> cathy = persons['cathy'] = Person('Cathy')
        >>> students = [john, peter, cathy]

        >>> for student in students:
        ...     Attending(student=student, course=course_a)

    Set up a teacher that instructs the two courses.

        >>> teacher = persons['william'] = Person('William')
        >>> course_b = courses['b'] = Course('course B')
        >>> Instruction(instructor=teacher, course=course_a)
        >>> Instruction(instructor=teacher, course=course_b)

    We're done with preparations.

    Check that relationship properties were bound.

        >>> course_a.students
        <schooltool.relationship.relationship.BoundRelationshipProperty object ...>
        >>> teacher.instructs
        <schooltool.relationship.relationship.BoundRelationshipProperty object ...>

    They can be used to add and remove relationships, can be iterated to obtain
    related objects and have other useful methods.

        >>> bool(course_b.students)
        False

        >>> for student in students:
        ...     course_b.students.add(student)

        >>> len(course_b.students)
        3

        >>> course_b.students.remove(john)

        >>> len(course_b.students)
        2

        >>> bool(course_b.students)
        True

        >>> list(course_b.students)
        [Peter, Cathy]

    You can also obtain RelationshipInfo helpers for related objects.

        >>> list(course_a.instructors.relationships)
        [<schooltool.relationship.relationship.RelationshipInfo object ...>]

        >>> rel_info = list(course_a.instructors.relationships)[0]
        >>> rel_info.source
        course A
        >>> rel_info.target
        William

    Notice that 'source' in RelationshipInfo is the instace that
    BoundRelationshipProperty is bound to.  Let's look at the info for a class
    that William teaches.

        >>> list(teacher.instructs)
        [course A, course B]

        >>> rel_info = list(teacher.instructs.relationships)[0]
        >>> rel_info.source
        William
        >>> rel_info.target
        course A

    Finally, let's check that BoundRelationshipProperty.relationships are
    filtered correctly.

        >>> [info.target for info in course_b.students.relationships]
        [Peter, Cathy]
        >>> [info.target for info in course_b.instructors.relationships]
        [William]

    """


from schooltool.app.tests import setUp, tearDown


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS | doctest.REPORT_ONLY_FIRST_FAILURE
    return unittest.TestSuite([
                doctest.DocFileSuite('../README.txt', setUp=setUp, tearDown=tearDown, optionflags=optionflags),
                # XXX: unit tests of each class need to be updated
                # doctest.DocTestSuite('schooltool.relationship.relationship'),
                doctest.DocTestSuite(setUp=setUp, tearDown=tearDown, optionflags=optionflags),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
