#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Unit tests for levels.
"""
import unittest
import doctest
from persistent import Persistent
from transaction import abort

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.interface import implements, Interface
from zope.interface.verify import verifyObject
from zope.location.pickling import LocationCopyHook
from zope.location.interfaces import ILocation
from zope.component import provideAdapter
from zope.component.hooks import getSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.level.level import URILevelCourses, URILevel
from schooltool.testing.setup import getIntegrationTestZCML
from schooltool.testing.stubs import AppStub


class CourseStub(Persistent, Contained):
    implements(IAttributeAnnotatable)
    def __init__(self, title):
        self.title = unicode(title)
    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.title)


def doctest_LevelContainer():
    """Tests for LevelContainer.

        >>> from schooltool.level.interfaces import ILevelContainer
        >>> from schooltool.level.level import LevelContainer

    A simple ordered container of levels.

        >>> level_container = app['schooltool.level.level']
        >>> verifyObject(ILevelContainer, level_container)
        True

        >>> level_container['vienas'] = u'One'
        >>> level_container['du'] = u'Two'
        >>> level_container['trys'] = u'Three'

        >>> level_container.keys()
        ['vienas', 'du', 'trys']

        >>> level_container.values()
        [u'One', u'Two', u'Three']

        >>> level_container.updateOrder(['trys', 'du', 'vienas'])

        >>> level_container.values()
        [u'Three', u'Two', u'One']

    """


def doctest_Level():
    """Tests for Level.

        >>> from schooltool.level.interfaces import ILevel
        >>> from schooltool.level.level import Level

    Level is a very simple object.

        >>> levels = app['schooltool.level.level']
        >>> level = levels['1'] = Level(u'1')
        >>> verifyObject(ILevel, level)
        True

        >>> print level.title
        1

    It has a courses attribute to control which courses are taught this level.

        >>> courses = app['schooltool.course.course']
        >>> course1 = courses['c1'] = CourseStub('C1')
        >>> course2 = courses['c2'] = CourseStub('C2')
        >>> level.courses.add(course1)
        >>> level.courses.add(course2)

        >>> print sorted(level.courses, key=lambda l: l.title)
        [<CourseStub u'C1'>, <CourseStub u'C2'>]

    The courses attribute actually manages relationships between the level and
    the course objects.

        >>> print ['Level %r' % l.title
        ...     for l in getRelatedObjects(
        ...         course1, URILevel, rel_type=URILevelCourses)]
        ["Level u'1'"]

    """


def doctest_LevelVocabulary():
    """Tests for LevelVocabulary.

        >>> from schooltool.level.interfaces import ILevelContainer

    Vocabulary of levels:

        >>> from zope.schema.interfaces import IVocabularyTokenized
        >>> from schooltool.level.level import Level
        >>> from schooltool.level.level import LevelVocabulary

        >>> class ContextStub(object):
        ...     implements(Interface)

        >>> context = ContextStub()
        >>> vocabulary = LevelVocabulary(context)
        >>> verifyObject(IVocabularyTokenized, vocabulary)
        True

    If the ISchoolToolApplication object cannot be adapted to
    ILevelContainer, the vocabulary is empty:

        >>> provideAdapter(
        ...     lambda ignored: None,
        ...     (ISchoolToolApplication,),
        ...     ILevelContainer)
        >>> vocabulary.container
        {}

        >>> len(vocabulary)
        0

        >>> list(vocabulary)
        []

        >>> def expand_term(term):
        ...     return (term.token, term.value, term.title)

        >>> level = Level(u'Basic')
        >>> level.__name__ = 'basic'
        >>> expand_term(vocabulary.getTerm(level))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

        >>> vocabulary.getTermByToken('basic-')
        Traceback (most recent call last):
        ...
        LookupError: basic-

        >>> level in vocabulary
        False

    Let's provide the needed adapters.

        >>> from schooltool.level.interfaces import ILevelContainer
        >>> from schooltool.level.level import LevelContainer

        >>> levels = app['schooltool.level.level']
        >>> levels['basic'] = Level(u'Basic')
        >>> levels['advanced'] = Level(u'Advanced')

        >>> provideAdapter(
        ...     lambda ignored: levels,
        ...     adapts=(ISchoolToolApplication, ),
        ...     provides=ILevelContainer)

    Now we can use the vocabulary.

        >>> vocabulary = LevelVocabulary(context)
        >>> verifyObject(IVocabularyTokenized, vocabulary)
        True

        >>> vocabulary.container
        <schooltool.level.level.LevelContainer ...>

        >>> len(vocabulary)
        2

        >>> [expand_term(term) for term in vocabulary]
        [('basic-', <schooltool.level.level.Level ...>, u'Basic'),
         ('advanced-', <schooltool.level.level.Level ...>, u'Advanced')]

        >>> expand_term(vocabulary.getTerm(levels['basic']))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

        >>> levels['basic'] in vocabulary
        True

        >>> expand_term(vocabulary.getTermByToken('basic-'))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

    """


def setUp(test):
    setup.placefulSetUp()
    # Workaround: _clear actually sets the Zope's vocabulary registry and
    #             is called on zope.app.schema.vocabularies import (during
    #             zcml parsing, for example).  When running multiple tests
    #             this ingenious idea fails, so we call it manually.
    from zope.app.schema import vocabulary
    vocabulary._clear()
    zcml = getIntegrationTestZCML()
    zcml.include('schooltool.level', file='level.zcml')
    provideAdapter(LocationCopyHook, (ILocation,))
    app = AppStub()
    app['schooltool.course.course'] = BTreeContainer()
    test.globs.update({
        'CourseStub': CourseStub,
        'getRelatedObjects': getRelatedObjects,
        'provideAdapter': provideStubAdapter,
        'unregisterAdapter': unregisterStubAdapter,
        'app': app,
        })


def tearDown(test):
    setup.placefulTearDown()
    abort()


def provideStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.registerAdapter(factory, required=adapts, provided=provides, name=name)


def unregisterStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.unregisterAdapter(factory, required=adapts, provided=provides, name=name)


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=optionflags),
        doctest.DocFileSuite(
            'level-integration.txt',
            setUp=setUp, tearDown=tearDown,
            optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
