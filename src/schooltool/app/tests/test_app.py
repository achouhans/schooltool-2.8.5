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
Unit tests for schooltool.app.
"""
import unittest
import doctest

from zope.component import provideAdapter
from zope.interface.verify import verifyObject
from zope.app.testing import setup, placelesssetup

from schooltool.testing import setup as sbsetup
from schooltool.app.tests import setUp, tearDown


def doctest_SchoolToolApplication():
    """SchoolToolApplication

    We need to register an adapter to make the title attribute available:

        >>> placelesssetup.setUp()
        >>> setup.setUpAnnotations()
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> provideAdapter(getApplicationPreferences,
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IApplicationPreferences)

    Let's check that SchoolToolApplication satisfies the interface:

        >>> app = sbsetup.createSchoolToolApplication()

        >>> verifyObject(ISchoolToolApplication, app)
        True

    The most basic containers should be available:

        >>> from schooltool.person.interfaces import IPersonContainer
        >>> verifyObject(IPersonContainer, app['persons'])
        True

        >>> from schooltool.resource.interfaces import IResourceContainer
        >>> verifyObject(IResourceContainer, app['resources'])
        True

    Our ApplicationPreferences title should be 'SchoolTool' by default:

        >>> from schooltool.app.app import getApplicationPreferences
        >>> getApplicationPreferences(app).title
        u'Your School'

    We can set it to something else:

        >>> getApplicationPreferences(app).title = "My School"
        >>> getApplicationPreferences(app).title
        'My School'

    Time settings for application:

        >>> prefs = getApplicationPreferences(app)
        >>> prefs.timezone
        'UTC'

        >>> prefs.dateformat
        '%Y-%m-%d'

        >>> prefs.timeformat
        '%H:%M'

        >>> prefs.weekstart
        0

    Clean up

        >>> placelesssetup.tearDown()

    """


def doctest_getSchoolToolApplication():
    """Tests for getSchoolToolApplication.

      >>> setup.placelessSetUp()

    Let's say we have a SchoolTool app, which is a site.

      >>> from schooltool.app.app import SchoolToolApplication
      >>> app = SchoolToolApplication()

      >>> from zope.site import LocalSiteManager
      >>> app.setSiteManager(LocalSiteManager(app))

    If site is not a SchoolToolApplication, we get None

      >>> from schooltool.app.app import getSchoolToolApplication
      >>> print getSchoolToolApplication()
      None

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True

      >>> setup.placelessTearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app.app',
                                     setUp=setUp, tearDown=tearDown,
                                     optionflags=doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE),
                doctest.DocTestSuite('schooltool.app.interfaces',
                                     setUp=setUp, tearDown=tearDown,
                                     optionflags=doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE),
                doctest.DocTestSuite('schooltool.app.membership',
                                     setUp=setUp, tearDown=tearDown,
                                     optionflags=doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
