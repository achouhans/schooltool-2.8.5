#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve33
"""
import unittest
import doctest

from zope.app.testing import setup

from zope.component import provideUtility
from zope.component import provideAdapter
from zope.interface import implements
from zope.intid import IntIds
from zope.site.folder import Folder
from zope.container.btree import BTreeContainer
from zope.component.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
from schooltool.generations.tests import setUp as packageSetUp
from schooltool.generations.tests import tearDown
from schooltool.contact.basicperson import getBoundContact
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.basicperson.person import BasicPerson


def populate(app):
    app['persons'] = BTreeContainer()
    app['persons']['john'] = BasicPerson("john", "Johny", "John")
    app['persons']['pete'] = BasicPerson("pete", "Petey", "Pete")


def verboseGetBoundContact(context):
    print 'IContact(<%s>)' % context.first_name
    return getBoundContact(context)



def doctest_evolve33():
    """Test evolution to generation 33.

    Set initial site:

        >>> setSite(None)

    Also an adapter to obtain the contact, and adapter to create form keys.

        >>> provideAdapter(verboseGetBoundContact, [IBasicPerson], IContact)
        >>> provideAdapter(lambda obj: obj.__name__, [None], IUniqueFormKey)

    And of course the app.

        >>> context = ContextStub(app)
        >>> manager = setup.createSiteManager(app)

    Let's evolve now.  Note that persons get adapted to IContact.

        >>> from schooltool.generations.evolve33 import evolve
        >>> evolve(context)
        IContact(<Johny>)
        IContact(<Petey>)

    Site was restored after evolution.

        >>> print getSite()
        None

    """


def setUp(test):
    packageSetUp(test)
    populate(test.globs['app'])
    

def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
