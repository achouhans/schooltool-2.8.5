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
Unit tests for schooltool.relationship.objectevents
"""
import unittest
import doctest

from schooltool.relationship.tests import URIStub
from schooltool.app.tests import setUp, tearDown


def doctest_delete_breaks_relationships():
    """When you delete an object, all of its relationships should be removed

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schooltool.relationship.objectevents import unrelateOnDeletion
        >>> zope.event.subscribers.append(unrelateOnDeletion)

    Suppose we have two related objects

        >>> from schooltool.relationship.tests import SomeContainedPersistent
        >>> apple = persons['apple'] = SomeContainedPersistent('apple')
        >>> orange = persons['orange'] = SomeContainedPersistent('orange')

        >>> from schooltool.relationship import getRelatedObjects, relate
        >>> from schooltool.relationship.uri import URIObject as URIStub
        >>> relate(URIStub('example:Relationship'),
        ...             (apple, URIStub('example:One')),
        ...             (orange, URIStub('example:Two')))
        >>> getRelatedObjects(apple, URIStub('example:Two'))
        [orange]

    We put those objects to a Zope 3 container.

        >>> from zope.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> container['apple'] = apple
        >>> container['orange'] = orange

    When we delete an object, all of its relationships should disappear

        >>> del container['orange']
        >>> getRelatedObjects(apple, URIStub('example:Two'))
        []

        >>> zope.event.subscribers[:] = old_subscribers

    """

# XXX: disabled copy tests since we don't copy related objects anywhere
#def doctest_copy_breaks_relationships():
#    """When you copy an object, all of its relationships should be removed
#
#    (An alternative solution would be to clone the relationships, but I'm
#    wary of that path.  What happens if you copy and paste objects between
#    different application instances?)
#
#        >>> from schooltool.relationship.tests import setUp, tearDown
#        >>> setUp()
#
#        >>> import zope.event
#        >>> old_subscribers = zope.event.subscribers[:]
#        >>> from schooltool.relationship.objectevents import unrelateOnCopy
#        >>> zope.event.subscribers.append(unrelateOnCopy)
#
#    Suppose we have two related objects.  We must have objects that are
#    IContained, otherwise ObjectCopier will happily duplicate all related
#    objects as well as relationship links.
#
#        >>> from schooltool.relationship.tests import SomeContained
#        >>> apple = SomeContained('apple')
#        >>> orange = SomeContained('orange')
#
#        >>> from schooltool.relationship import getRelatedObjects, relate
#        >>> relate('example:Relationship',
#        ...             (apple, URIStub('example:One')),
#        ...             (orange, URIStub('example:Two')))
#        >>> getRelatedObjects(apple, URIStub('example:Two'))
#        [orange]
#
#    We put those objects to a Zope 3 container.
#
#        >>> from zope.container.btree import BTreeContainer
#        >>> container = BTreeContainer()
#        >>> container['apple'] = apple
#        >>> container['orange'] = orange
#
#    We copy one of the objects to another container.
#
#        >>> from zope.copypastemove import ObjectCopier
#        >>> another_container = BTreeContainer()
#        >>> copier = ObjectCopier(container['orange'])
#        >>> new_name = copier.copyTo(another_container)
#        >>> copy_of_orange = another_container[new_name]
#
#    When we copy an object, all of its relationships should disappear
#
#        >>> from schooltool.relationship.interfaces import IRelationshipLinks
#        >>> list(IRelationshipLinks(copy_of_orange))
#        []
#
#    The old relationships should still work
#
#        >>> getRelatedObjects(apple, URIStub('example:Two'))
#        [orange]
#        >>> getRelatedObjects(orange, URIStub('example:One'))
#        [apple]
#
#        >>> zope.event.subscribers[:] = old_subscribers
#        >>> tearDown()
#
#    """
#
#
#def doctest_copy_does_not_break_inside_relationships():
#    """When you copy an object, all of its relationships should be removed
#
#    This is a regression test for the following bug: If x is related to x.y
#    where x.y is a subobject of x, when you copy x to x', all links from x'
#    will be removed, but the copied link on x'.y' will remain.
#
#        >>> from schooltool.relationship.tests import setUp, tearDown
#        >>> setUp()
#
#        >>> import zope.event
#        >>> old_subscribers = zope.event.subscribers[:]
#        >>> from schooltool.relationship.objectevents import unrelateOnCopy
#        >>> zope.event.subscribers.append(unrelateOnCopy)
#
#    Suppose we have two related objects.  We must have objects that are
#    IContained, otherwise ObjectCopier will happily duplicate all related
#    objects as well as relationship links.
#
#        >>> from schooltool.relationship.tests import SomeContained
#        >>> apple = SomeContained('apple')
#        >>> orange = SomeContained('orange')
#
#        >>> from schooltool.relationship import getRelatedObjects, relate
#        >>> relate(URIStub('example:Relationship'),
#        ...             (apple, URIStub('example:One')),
#        ...             (orange, URIStub('example:Two')))
#        >>> getRelatedObjects(apple, URIStub('example:Two'))
#        [orange]
#
#    We put one of the objects to a Zope 3 container.
#
#        >>> from zope.container.btree import BTreeContainer
#        >>> container = BTreeContainer()
#        >>> container['orange'] = orange
#
#    We make the other object a subobject of the first object
#
#        >>> apple.__parent__ = orange
#        >>> apple.__name__ = 'apple'
#        >>> orange.apple = apple
#
#    We copy the first object to another container.
#
#        >>> from zope.copypastemove import ObjectCopier
#        >>> another_container = BTreeContainer()
#        >>> copier = ObjectCopier(container['orange'])
#        >>> new_name = copier.copyTo(another_container)
#        >>> copy_of_orange = another_container[new_name]
#        >>> copy_of_apple = copy_of_orange.apple
#
#        >>> r1 = URIStub('example:One')
#        >>> r2 = URIStub('example:Two')
#
#    When we copy an object, its internal relationships should remain
#
#        >>> getRelatedObjects(copy_of_orange, r1)
#        [apple]
#        >>> getRelatedObjects(copy_of_apple, r2)
#        [orange]
#
#    These two objects are, in fact, copies
#
#        >>> getRelatedObjects(copy_of_orange, r1)[0] is copy_of_apple
#        True
#        >>> getRelatedObjects(copy_of_apple, r2)[0] is copy_of_orange
#        True
#
#    The old relationships should still work
#
#        >>> getRelatedObjects(apple, r2)
#        [orange]
#        >>> getRelatedObjects(orange, r1)
#        [apple]
#
#        >>> zope.event.subscribers[:] = old_subscribers
#        >>> tearDown()
#
#    """
#

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(setUp=setUp, tearDown=tearDown),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
