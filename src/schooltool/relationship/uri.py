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
URI objects.

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  Instead of dealing with strings directly,
schooltool.relationship uses introspectable URI objects that also have an
optional short name and a description in addition to the URI itself.

By convention, names of global URI object constants start with 'URI'.
"""

import re

from persistent import Persistent

from zope.interface import Interface, implements
from zope.schema import Text, TextLine, URI
from zope.container.contained import Contained
from schooltool.relationship.relationship import BoundRelationshipProperty


class IURIObject(Interface):
    """An opaque identifier of a role or a relationship type.

    Roles and relationships are identified by URIs in XML representation.
    URI objects let the application assign human-readable names to roles
    and relationship types.

    URI objects are equal iff their uri attributes are equal.

    URI objects are hashable.
    """

    uri = URI(title=u"URI",
            description=u"The URI (as a string).")

    name = TextLine(title=u"Name",
            description=u"Human-readable name.")

    description = Text(title=u"Description",
            description=u"Human-readable description.")

    def persist():
        """Return persistent version of self to store in DB."""

    def __eq__(other):
        """self == other"""

    def __ne__(other):
        """self != other"""

    def __hash__():
        """Hash self (for example, return hash of uri)"""

    def access(state):
        """Access relevant portion of shared state."""

    def bind(instance, my_role, rel_type, other_role):
        """Return a relationship property bound to given instance."""

    def filter(link):
        """Default filter."""


class URIObject(object):
    """See IURIObject."""

    implements(IURIObject)

    def __init__(self, uri, name=None, description=''):
        if not looks_like_a_uri(uri):
            raise ValueError("This does not look like a URI: %r" % uri)
        self._uri = uri
        self._name = name
        self._description = description

    def persist(self):
        return PersistentURIObject(
            self, self._uri, name=self._name, description=self._description)

    uri = property(lambda self: self._uri)
    name = property(lambda self: self._name)
    description = property(lambda self: self._description)

    def __eq__(self, other):
        if not IURIObject.providedBy(other):
            return False
        return self.uri == other.uri

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._uri)

    def __unicode__(self):
        return unicode(self._uri)

    def __str__(self):
        if isinstance(self._uri, str):
            return self._uri
        return self._uri.encode('UTF-8')

    def __repr__(self):
        return '<URIObject %s>' % (self.name or self.uri)

    def access(self, state):
        return state

    def bind(self, instance, my_role, rel_type, other_role):
        return BoundRelationshipProperty(
            instance, rel_type, my_role, other_role)

    def filter(self, link):
        return link.rel_type == self


class PersistentURIObject(Persistent, Contained, URIObject):

    __name__ = None
    __parent__ = None


def looks_like_a_uri(uri):
    r"""Check if the argument looks like a URI string.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.

    Some examples of valid URI strings:

        >>> looks_like_a_uri('http://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('HTTP://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('mailto:root')
        True

    These strings are all invalid URIs:

        >>> looks_like_a_uri('2HTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('\nHTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('mailto:postmaster ')
        False
        >>> looks_like_a_uri('mailto:postmaster text')
        False
        >>> looks_like_a_uri('nocolon')
        False
        >>> looks_like_a_uri(None)
        False

    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return bool(uri and uri_re.match(uri) is not None)

