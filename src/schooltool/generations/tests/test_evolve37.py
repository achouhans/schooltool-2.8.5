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
Unit tests for schooltool.generations.evolve37
"""
import unittest
import doctest
import datetime

from persistent.interfaces import IPersistent
from zope.app.testing import setup
from zope.component import provideUtility
from zope.component import provideAdapter
from zope.component import getUtility
from zope.interface import implements
from zope.intid import IntIds
from zope.intid.interfaces import IIntIds
from zope.keyreference.interfaces import IKeyReference
from zope.site.folder import Folder
from zope.component.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
from schooltool.generations.tests import tearDown

from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.schoolyear import SchoolYearInit
from schooltool.schoolyear.schoolyear import SchoolYearDateRangeAdapter
from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.generations.evolve37 import LEVELS_APP_KEY
from schooltool.generations.evolve37 import LevelContainerContainer
from schooltool.testing.setup import getIntegrationTestZCML
from schooltool.testing.stubs import AppStub


def populate(app):
    years = getSchoolYearContainer(app)
    years['1'] = SchoolYear('2010',
                            datetime.date(2010, 01, 01),
                            datetime.date(2010, 12, 30))
    years['2'] = SchoolYear('2011',
                            datetime.date(2011, 01, 01),
                            datetime.date(2011, 12, 30))
    years._active_id = None
    return years


def doctest_guessMostRecentLevels():
    """Tests for guessing the best level container.

        >>> years = getSchoolYearContainer(app)

        >>> from schooltool.generations.evolve37 import guessMostRecentLevels

        >>> print guessMostRecentLevels(app)
        None

        >>> app[LEVELS_APP_KEY] = LevelContainerContainer()

        >>> print guessMostRecentLevels(app)
        None

        >>> int_ids = getUtility(IIntIds)
        >>> app[LEVELS_APP_KEY][unicode(int_ids.getId(years['1']))] = 'levels 1'
        >>> app[LEVELS_APP_KEY][unicode(int_ids.getId(years['2']))] = 'levels 2'

        >>> print guessMostRecentLevels(app)
        levels 2

        >>> years.activateNextSchoolYear(year_id='1')
        >>> print guessMostRecentLevels(app)
        levels 1

        >>> years.activateNextSchoolYear(year_id='2')
        >>> print guessMostRecentLevels(app)
        levels 2

    """


def doctest_evolve37():
    """Test evolution to generation 37.

        >>> context = ContextStub(app)

        >>> years = getSchoolYearContainer(app)
        >>> years.activateNextSchoolYear(year_id='2')

        >>> int_ids = getUtility(IIntIds)
        >>> app[LEVELS_APP_KEY] = LevelContainerContainer()
        >>> app[LEVELS_APP_KEY][unicode(int_ids.getId(years['1']))] = 'levels 1'
        >>> app[LEVELS_APP_KEY][unicode(int_ids.getId(years['2']))] = 'levels 2'

    Let's evolve now.

        >>> from schooltool.generations.evolve37 import evolve
        >>> evolve(context)

        >>> print app[LEVELS_APP_KEY]
        levels 2

    Site was restored after evolution.

        >>> print getSite()
        None

    """


def doctest_evolve37_no_levels():
    """Test evolution to generation 37.

        >>> context = ContextStub(app)

        >>> years = getSchoolYearContainer(app)
        >>> years.activateNextSchoolYear(year_id='2')

    Let's evolve now.

        >>> from schooltool.generations.evolve37 import evolve
        >>> evolve(context)

        >>> print app.get(LEVELS_APP_KEY)
        None

    """


def setUp(test):
    setup.placefulSetUp()
    zcml = getIntegrationTestZCML()
    zcml.include('schooltool.schoolyear', file='schoolyear.zcml')
    app = AppStub()
    populate(app)
    test.globs.update({
        'app': app,
        'zcml': zcml,
    })
    setSite()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
