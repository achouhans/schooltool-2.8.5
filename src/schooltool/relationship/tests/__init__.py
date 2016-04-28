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

This module contains a `setUpRelationships` function that can be used in
unit test setup code to register an IRelationshipLinks adapter for IAnnotatable
objects.  There are also `setUp` and `tearDown` functions that perform the
necessary Zope 3 placeless setup that is needed to make annotations and
relationships work for IAttributeAnnotatable objects.

This module also contains some stub objects for use in tests (SomeObject and
SomeContained).
"""

from persistent import Persistent

from zope.app.testing import setup
from zope.interface import implements
from zope.location.pickling import LocationCopyHook
from zope.component import provideAdapter
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.contained import Contained


class SomeObject(object):
    """A simple annotatable object for tests."""

    implements(IAttributeAnnotatable)

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name


class SomeContained(SomeObject, Contained):
    """A simple annotatable contained object for tests."""


class SomeContainedPersistent(Persistent, SomeContained):
    pass


class URIStub(object):
    def __init__(self, uri):
        self.uri = uri
    def __cmp__(self, other):
        return cmp(self.uri, other.uri)


def setUp(test=None):
    """Set up for schooltool.relationship doctests.

    Calls Zope's placelessSetUp, sets up annotations and relationships.
    """
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setUpRelationships()


def tearDown(test=None):
    """Tear down for schooltool.relationshp doctests."""
    setup.placelessTearDown()


def setUpRelationships():
    """Set up the adapter from IAnnotatable to IRelationshipLinks.

    This function is created for use in unit tests.  You should call
    zope.app.testing.setup.placelessSetUp before calling this function
    (and don't forget to call zope.app.testing.setup.placelessTearDown after
    you're done).  You should also call zope.app.testing.setup.setUpAnnotations
    to get a complete test fixture.
    """
    from zope.annotation.interfaces import IAnnotatable
    from zope.component import provideAdapter
    from zope.location.interfaces import ILocation
    from schooltool.relationship.interfaces import IRelationshipLinks
    from schooltool.relationship.annotatable import getRelationshipLinks
    provideAdapter(getRelationshipLinks, (IAnnotatable,), IRelationshipLinks)
    provideAdapter(LocationCopyHook, (ILocation,))


