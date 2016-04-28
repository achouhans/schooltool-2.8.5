from transaction import abort

from zope.app.testing import setup
from zope.container.btree import BTreeContainer

from schooltool.testing.setup import getIntegrationTestZCML
from schooltool.testing.stubs import AppStub


def setUp(test):
    setup.placefulSetUp()
    zcml = getIntegrationTestZCML()
    app = AppStub()
    persons = app['persons'] = BTreeContainer()
    courses = app['schooltool.course.course'] = BTreeContainer()
    sections = app['schooltool.course.section'] = BTreeContainer()
    groups = app['schooltool.group'] = BTreeContainer()
    test.globs.update({
        'zcml': zcml,
        'app': app,
        'persons': persons,
        'sections': sections,
        'groups': groups,
        'courses': courses,
        })


def tearDown(test):
    setup.placefulTearDown()
    abort()
