#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve29
"""
import unittest
import doctest
from persistent import Persistent

from zope.container.btree import BTreeContainer

from schooltool.generations.tests import ContextStub
from schooltool.generations.tests import setUp as packageSetUp
from schooltool.generations.tests import tearDown



class PersonStub(Persistent):

    def __init__(self, username, first_name, last_name):
        self.username = username
        self.first_name = first_name
        self.last_name = last_name


def doctest_evolve29():
    """Evolution to generation 29.

        >>> context = ContextStub(app)

    We set up some persons and evolve the application

        >>> from schooltool.generations.evolve29 import evolve
        >>> evolve(context)

    and the extra attributes are gone

        >>> for username, person in sorted(app['persons'].items()):
        ...     print person.__dict__
        {'username': 'john', 'first_name': 'Johny', 'last_name': 'John'}
        {'username': 'pete', 'first_name': 'Petey', 'last_name': 'Pete'}

    """


def populate(app):
    app['persons'] = BTreeContainer()
    app['persons']['john'] = PersonStub("john", "Johny", "John")
    app['persons']['john'].email = "john@example.com"
    app['persons']['john'].phone = "667755"

    app['persons']['pete'] = PersonStub("pete", "Petey", "Pete")
    app['persons']['pete'].email = "pete@example.com"
    app['persons']['pete'].phone = "667755"
    app['persons']['pete'].gradeclass = 'gradeclass'


def setUp(test):
    packageSetUp(test)
    populate(test.globs['app'])


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS
                             |doctest.REPORT_ONLY_FIRST_FAILURE)
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
