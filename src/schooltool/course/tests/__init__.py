from datetime import date, timedelta
from transaction import abort

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.container.btree import BTreeContainer

from schooltool.course import section
from schooltool.term.term import getSchoolYearForTerm
from schooltool.term.term import Term
from schooltool.testing.setup import getIntegrationTestZCML
from schooltool.testing.stubs import AppStub
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.section import Section
from schooltool.person.person import PersonContainer


def setUpSchoolYear(year=2000):
    year_container = ISchoolYearContainer(ISchoolToolApplication(None))
    sy = year_container[str(year)] = SchoolYear(
        str(year), date(year, 1, 1), date(year+1, 1, 1) - timedelta(1))
    return sy


def setUpTerms(schoolyear, term_count=3):
    term_delta = timedelta(
        ((schoolyear.last - schoolyear.first) / term_count).days)
    start_date = schoolyear.first
    for n in range(term_count):
        finish_date = start_date + term_delta - timedelta(1)
        schoolyear['Term%d' % (n+1)] =Term(
            'Term %d' % (n+1), start_date, finish_date)
        start_date = finish_date + timedelta(1)


def setUpSections(term_list, sections_per_term=1):
    for term in term_list:
        sections = ISectionContainer(term)
        for n in range(sections_per_term):
            name = 'Sec%d'%(n+1)
            sections[name] = Section(name)


def setUp(test):
    setup.placefulSetUp()
    zcml = getIntegrationTestZCML()
    zcml.include('schooltool.schoolyear', file='schoolyear.zcml')
    zcml.string('''
    <adapter
      for="schooltool.course.interfaces.ISectionContainer"
      factory="schooltool.course.browser.section.SectionNameChooser"
      provides="zope.container.interfaces.INameChooser" />
    ''')

    provideAdapter(section.getSectionContainer)
    provideAdapter(section.getTermForSection)
    provideAdapter(section.getTermForSectionContainer)
    provideAdapter(section.SectionLinkContinuinityValidationSubscriber)
    provideAdapter(getSchoolYearForTerm)
    app = AppStub()
    courses = app['schooltool.course.course'] = BTreeContainer()
    sections = app['schooltool.course.section'] = BTreeContainer()
    groups = app['schooltool.group'] = BTreeContainer()
    persons = app['persons'] = PersonContainer()
    resources = app['resources'] = BTreeContainer()
    test.globs.update({
        'app': app,
        'courses': courses,
        'sections': sections,
        'persons': persons,
        'groups': groups,
        'resources': resources,
        })


def tearDown(test):
    setup.placefulTearDown()
    abort()
