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
SchoolTool XLS export views.
"""
import xlwt
import datetime
from operator import attrgetter
from StringIO import StringIO

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.skin import flourish
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.interfaces import IDemographics, IBasicPerson
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.common import SchoolToolMessage as _
from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IAsset
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.common import format_time_range
from schooltool.contact.interfaces import IContact, IContactContainer
from schooltool.contact.interfaces import IContactable
from schooltool.export.interfaces import IXLSExportView
from schooltool.export.interfaces import IXLSProgressMessage
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.level.interfaces import ILevelContainer
from schooltool.report.browser.report import RequestRemoteReportDialog
from schooltool.report.browser.report import ProgressReportPage
from schooltool.report.report import ReportLinkViewlet
from schooltool.task.progress import TaskProgress
from schooltool.task.progress import normalized_progress
from schooltool.report.report import AbstractReportTask
from schooltool.report.report import NoReportException
from schooltool.report.report import ReportMessage
from schooltool.report.report import OnPDFReportScheduled
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.daytemplates import CalendarDayTemplates
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates


class ExcelExportView(ProgressReportPage):

    implements(IXLSExportView)

    def __init__(self, context, request):
        super(ExcelExportView, self).__init__(context, request)
        self._font_cache = {}
        self._style_cache = {}

    def setUpHeaders(self, data):
        """Set up HTTP headers to serve data as excel spreadsheet."""
        response = self.request.response
        response.setHeader('Content-Type', 'application/vnd.ms-excel')
        response.setHeader('Content-Length', len(data))

    def listRelationships(self, header, relationships, ws, offset, last=False):
        items = sorted(relationships.all(), key=lambda i: i.__name__)
        if not items:
            return offset - 1
        self.write_header(ws, offset + 1, 0,  header, merge=1)
        for n, item in enumerate(items):
            self.write(ws, offset + 2 + n, 0,  item.__name__)
            self.write(ws, offset + 2 + n, 1,  "")
            state = relationships.state(item)
            for x, (date, meaning, code) in enumerate(state):
                self.write(ws, offset + 2 + n, 2+x*2,
                           Date(date))
                self.write(ws, offset + 2 + n, 2+x*2+1, code)
        return 1 + offset + len(items)

    def skipRow(self, ws, offset):
        return offset + 1

    def listFields(self, item, accessors, ws, offset):
        for n, accessor in enumerate(accessors):
            header, field, style = accessor(item)
            self.write_header(ws, offset + n, 0, header)
            self.write(ws, offset + n, 1, field, format_str=style)
        return offset + len(accessors)

    def _makeFont(self, font_key):
        font = xlwt.Font()
        for attr, value in font_key:
            setattr(font, attr, value)
        return font

    def getFont(self, font_key):
        font = self._font_cache.get(font_key, None)
        if font is None:
            self._font_cache[font_key] = font = self._makeFont(font_key)
        return font

    def write(self, ws, row, col, data, **kw):
        if isinstance(data, Text):
            kw.update(data.style)
            data = data.data
        bold = kw.get('bold', False)
        color = kw.get('color', None)
        format_str = kw.get('format_str', None)
        borders = kw.get('borders', None)
        merge = kw.get('merge', None)
        if borders is None:
            borders = []
        if data is None:
            data = ""
        if type(data) == type(True):
            data = str(data)
        key = (bold, color, format_str, tuple(borders))
        style = self._style_cache.get(key, None)
        if style is None:
            style = xlwt.XFStyle()
            if bold:
                style.font = self.getFont((("bold", True),))

            if color is not None:
                pattern = xlwt.Pattern()
                pattern.pattern = xlwt.Pattern.SOLID_PATTERN
                pattern.pattern_fore_colour = color
                style.pattern = pattern

            if format_str is not None:
                style.num_format_str = format_str

            if borders:
                b = xlwt.Formatting.Borders()
                for border in borders:
                    setattr(b, border, xlwt.Formatting.Borders.THIN)
                style.borders = b
            self._style_cache[key] = style
        if merge is None:
            ws.write(row, col, data, style)
        else:
            ws.write_merge(row, row, col, col + merge, data, style)

    def write_header(self, ws, row, col, data,
                     borders=None, merge=None):
        YELLOW = 5
        self.write(ws, row, col, data, borders=borders, bold=True, color=YELLOW,
                   merge=merge)


class SchoolTimetableExportView(ExcelExportView):

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    def format_periods(self, periods, ws, offset):
        self.write_header(ws, offset, 0, "Days")
        max_periods = max([len(day) for day in periods.templates.values()])
        self.write_header(ws, offset, 1, "Periods", merge=max_periods - 1)
        offset += 1

        for day in periods.templates.values():
            self.write(ws, offset, 0, day.title)
            for col, period in enumerate(day.values()):
                self.write(ws, offset, col + 1, period.title)
                self.write(ws, offset + 1, col + 1, period.activity_type)
            offset += 2
        return offset

    def format_time_slots(self, time_slots, ws, offset):
        self.write_header(ws, offset, 0, "Time schedule")
        offset += 1

        for day in time_slots.templates.values():
            self.write(ws, offset, 0, day.title)
            for col, slot in enumerate(day.values()):
                time = format_time_range(slot.tstart, slot.duration)
                self.write(ws, offset, col + 1, time)
                self.write(ws, offset + 1, col + 1, slot.activity_type)
            offset += 2
        return offset

    day_templates = (
        ('calendar_days', CalendarDayTemplates),
        ('week_days', WeekDayTemplates),
        ('school_days', SchoolDayTemplates),
        )

    def format_school_timetable(self, timetable, ws, offset):
        template_ids = dict([(cls, tid)
                             for tid, cls in self.day_templates])
        factory_id = lambda t: template_ids[t.__class__]
        schoolyear_id = lambda t: IHaveTimetables(t).__name__
        fields = [lambda i: ("School Timetable", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("School Year", schoolyear_id(i), None),
                  lambda i: ("Period days", factory_id(i.periods), None),
                  lambda i: ("Time slots", factory_id(i.time_slots), None)]

        offset = self.listFields(timetable, fields, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_periods(timetable.periods, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_time_slots(timetable.time_slots, ws, offset)
        return offset + 1

    def export_school_timetables(self, wb):
        self.task_progress.force('export_school_timetables', active=True)
        ws = wb.add_sheet("School Timetables")
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)
        row = 0
        for ny, school_year in enumerate(sorted(school_years, key=lambda i: i.last)):
            timetables = ITimetableContainer(school_year)
            for nt, timetable in enumerate(sorted(timetables.values(), key=lambda i: i.__name__)):
                row = self.format_school_timetable(timetable, ws, row) + 1
                self.progress('export_school_timetables', normalized_progress(
                        ny, len(school_years), nt, len(timetables)))
        self.finish('export_school_timetables')


def merge_date_ranges(dates):
    ranges = []
    start = None
    previous_day = None
    for day in dates:
        if start is None:
            previous_day = start = day
        elif day - datetime.timedelta(days=1) == previous_day:
            previous_day = day
        else:
            ranges.append((start, previous_day))
            previous_day = start = day
    if start is not None:
        ranges.append((start, previous_day))

    return ranges


class Text(object):

    style = {}
    def __init__(self, data):
        self.data = data

    def __cmp__(self, other):
        try:
            return cmp(self.data, other.data)
        except TypeError:
            return cmp(unicode(self.data), unicode(other.data))

    def __repr__(self):
        return 'Text(%r)' % self.data


class Header(Text):
    YELLOW = 5
    style = {'bold': True,
             'color': YELLOW}

    def __repr__(self):
        return 'Header(%r)' % self.data


class Date(Text):
    style = {'format_str': 'YYYY-MM-DD'}

    def __repr__(self):
        return 'Date(%r)' % self.data


class ContactRelationship(object):

    def __init__(self, person, contact, relationship):
        self.person = person
        self.contact = contact
        self.relationship = relationship


class MegaExporter(SchoolTimetableExportView):

    overall_line_id = 'overall'

    def print_table(self, table, ws, row=0, col=0):
        for y, cells in enumerate(table):
            self.print_row(cells, ws, row=(row+y), col=col)
        return len(table)

    def print_row(self, cells, ws, row=0, col=0):
        for x, cell in enumerate(cells):
            self.write(ws, row, col+x, cell.data, **cell.style)

    def format_table(self, fields, items, importer=None, major_progress=(),
                     sort=True):
        headers = [Header(header)
                   for header, style, getter in fields]
        rows = []
        total_items = len(removeSecurityProxy(items))
        for n, item in enumerate(items):
            row = [style(getter(item))
                   for header, style, getter in fields]
            rows.append(row)
            if importer is not None:
                self.progress(importer, normalized_progress(
                        *(major_progress + (n, total_items))))
        if sort:
            rows.sort()
        return [headers] + rows

    def format_school_years(self):
        fields = [('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Start', Date, attrgetter('first')),
                  ('End', Date, attrgetter('last'))]
        items = ISchoolYearContainer(self.context).values()
        result = self.format_table(fields, items, importer='export_school_years')
        return result

    def export_school_years(self, wb):
        self.task_progress.force('export_school_years', active=True)
        ws = wb.add_sheet("School Years")
        self.print_table(self.format_school_years(), ws)
        self.finish('export_school_years')

    def calculate_holidays_and_weekdays(self):

        work_days = 0.0

        days_of_week = {}
        for dow in range(7):
            days_of_week[dow] = [0, 0]

        school_years = ISchoolYearContainer(self.context).values()
        for school_year in school_years:
            terms = ITermContainer(school_year).values()
            for term in terms:
                for date in term:
                    if term.isSchoolday(date):
                        days_of_week[date.weekday()][0] += 1
                        work_days += 1
                    else:
                        days_of_week[date.weekday()][1] += 1

        if work_days == 0:
            return [[], list(range(7)), []]

        coefficients = [counts[0] / work_days
                        for day, counts in sorted(days_of_week.items())]

        # Weekends
        weekends = []
        for n, k in enumerate(coefficients):
            if k < 0.1:
                weekends.append(n)

        # Weekend exceptions and holidays
        holidays = []
        weekend_exceptions = []
        for school_year in school_years:
            terms = ITermContainer(school_year).values()
            for term in terms:
                for date in term:
                    if term.isSchoolday(date) and date.weekday() in weekends:
                        weekend_exceptions.append(date)
                    elif not term.isSchoolday(date) and date.weekday() not in weekends:
                        holidays.append(date)

        holiday_ranges = merge_date_ranges(holidays)
        return [holiday_ranges, weekends, weekend_exceptions]

    def format_holidays(self, holidays):
        if not holidays:
            return []
        table = [[], [Header("Holidays")]]
        table.extend([[Date(start), Date(end)]
                      for start, end in holidays])
        return table

    def format_weekends(self, weekends):
        if not weekends:
            return []

        table = [[], [Header("Weekends")]]
        weekdays = map(Text, ['Monday',
                              'Tuesday',
                              'Wednesday',
                              'Thursday',
                              'Friday',
                              'Saturday',
                              'Sunday'])
        table.append(weekdays)
        table.append([weekday in weekends and Text('X') or Text('')
                      for weekday in range(len(weekdays))])
        return table

    def format_weekend_exceptions(self, working_weekends):
        if not working_weekends:
            return []

        table = [[], [Header("Working weekends")]]
        table.extend([[Date(day)]
                      for day in working_weekends])
        return table

    def format_terms(self):
        fields = [('SchoolYear', Text, lambda t: t.__parent__.__name__),
                  ('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Start', Date, attrgetter('first')),
                  ('End', Date, attrgetter('last'))]

        school_years = ISchoolYearContainer(self.context).values()
        items = []
        for year in school_years:
            items.extend([term for term in
                          ITermContainer(year).values()])
        terms_table = self.format_table(fields, items, importer='export_terms')
        holidays, weekends, exceptions = self.calculate_holidays_and_weekdays()
        terms_table.extend(self.format_holidays(holidays))
        terms_table.extend(self.format_weekends(weekends))
        terms_table.extend(self.format_weekend_exceptions(exceptions))
        return terms_table

    def export_terms(self, wb):
        self.task_progress.force('export_terms', active=True)
        ws = wb.add_sheet("Terms")
        self.print_table(self.format_terms(), ws)
        self.finish('export_terms')

    def format_persons(self):
        fields = [('User Name', Text, attrgetter('__name__')),
                  ('Prefix', Text, attrgetter('prefix')),
                  ('First Name', Text, attrgetter('first_name')),
                  ('Middle Name', Text, attrgetter('middle_name')),
                  ('Last Name', Text, attrgetter('last_name')),
                  ('Suffix', Text, attrgetter('suffix')),
                  ('Preferred Name', Text, attrgetter('preferred_name')),
                  ('Birth Date', Date, attrgetter('birth_date')),
                  ('Gender', Text, attrgetter('gender')),
                  ('Password', Text, lambda p: None)]

        def demographics_getter(attribute):
            def getter(person):
                demographics = IDemographics(person)
                return demographics[attribute]
            return getter

        app = ISchoolToolApplication(None)
        demographics_fields = IDemographicsFields(app)
        for field in demographics_fields.values():
            title = field.title
            format = Text
            if isinstance(field, DateFieldDescription):
                format = Date
            getter = demographics_getter(field.name)
            fields.append((title, format, getter))

        items = self.context['persons'].values()
        return self.format_table(fields, items, importer='export_persons')

    def export_persons(self, wb):
        self.task_progress.force('export_persons', active=True)
        ws = wb.add_sheet("Persons")
        self.print_table(self.format_persons(), ws)
        self.finish('export_persons')

    def format_contact_persons(self):
        def contact_getter(attribute):
            def getter(contact):
                person = IBasicPerson(contact.__parent__, None)
                if person is None:
                    return getattr(contact, attribute)
                if attribute == '__name__':
                    return person.username
                return ''
            return getter

        fields = [('ID', Text, contact_getter('__name__')),
                  ('Prefix', Text, contact_getter('prefix')),
                  ('First Name', Text, contact_getter('first_name')),
                  ('Middle Name', Text, contact_getter('middle_name')),
                  ('Last Name', Text, contact_getter('last_name')),
                  ('Suffix', Text, contact_getter('suffix')),
                  ('Address line 1', Text, attrgetter('address_line_1')),
                  ('Address line 2', Text, attrgetter('address_line_2')),
                  ('City', Date, attrgetter('city')),
                  ('State', Date, attrgetter('state')),
                  ('Country', Date, attrgetter('country')),
                  ('Postal code', Date, attrgetter('postal_code')),
                  ('Home phone', Text, attrgetter('home_phone')),
                  ('Work phone', Text, attrgetter('work_phone')),
                  ('Mobile phone', Text, attrgetter('mobile_phone')),
                  ('Email', Text, attrgetter('email')),
                  ('Language', Text, attrgetter('language'))]

        items = []
        for person in self.context['persons'].values():
            items.append(IContact(person))
        for contact in IContactContainer(self.context).values():
            items.append(contact)

        return self.format_table(fields, items, importer='export_contacts',
                                 major_progress=(0,2))

    def format_person_contacts(self, person, major_progress=()):
        contacts = IContactable(person).contacts
        rows = []
        for contact in contacts.all():
            row = []
            row.append(Text(person.username))
            target_person = IBasicPerson(contact.__parent__, None)
            if target_person is None:
                row.append(Text(contact.__name__))
            else:
                row.append(Text(target_person.username))

            state = contacts.state(contact)
            for x, (date, meaning, code) in enumerate(state):
                row.append(Date(date))
                row.append(Text(code))
            rows.append(row)
        return rows

    def format_contact_relationships(self):
        rows = []
        persons = self.context['persons']
        total = len(persons)
        for nperson, person in enumerate(persons.values()):
            person = removeSecurityProxy(person)
            person_rows = self.format_person_contacts(
                person, major_progress=(1, 2, nperson, total))
            rows.extend(person_rows)
        rows.sort()

        headers = [Header('Person ID'), Header('Contact ID'), Header('Relationship')]
        rows.insert(0, headers)

        return rows

    def export_contacts(self, wb):
        self.task_progress.force('export_contacts', active=True)
        ws = wb.add_sheet("Contact Persons")
        self.print_table(self.format_contact_persons(), ws)
        ws = wb.add_sheet("Contact Relationships")
        self.print_table(self.format_contact_relationships(), ws)
        self.finish('export_contacts')

    def format_resources(self):
        fields = [('ID', Text, attrgetter('__name__')),
                  ('Type', Text, lambda r: r.__class__.__name__),
                  ('Title', Text, attrgetter('title'))]
        items = self.context['resources'].values()
        return self.format_table(fields, items, importer='export_resources')

    def export_resources(self, wb):
        self.task_progress.force('export_resources', active=True)
        ws = wb.add_sheet("Resources")
        self.print_table(self.format_resources(), ws)
        self.finish('export_resources')

    def format_levels(self):
        fields = [('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title'))]
        levels = ILevelContainer(self.context)
        items = levels.values()
        return self.format_table(fields, items, importer='export_levels',
                                 sort=False)

    def export_levels(self, wb):
        self.task_progress.force('export_levels', active=True)
        ws = wb.add_sheet("Grade Levels")
        self.print_table(self.format_levels(), ws)
        self.finish('export_levels')

    def format_courses(self):
        def get_course_level(course):
            if course.levels:
                return ', '.join([l.__name__ for l in course.levels])
        fields = [('School Year', Text, lambda c: ISchoolYear(c).__name__),
                  ('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Description', Text, attrgetter('description')),
                  ('Local ID', Text, attrgetter('course_id')),
                  ('Government ID', Text, attrgetter('government_id')),
                  ('Credits', Text, attrgetter('credits')),
                  ('Grade Level ID', Text, get_course_level)]

        school_years = ISchoolYearContainer(self.context).values()
        items = []
        for year in school_years:
            items.extend([term for term in
                          ICourseContainer(year).values()])
        return self.format_table(fields, items, importer='export_courses')

    def export_courses(self, wb):
        self.task_progress.force('export_courses', active=True)
        ws = wb.add_sheet("Courses")
        self.print_table(self.format_courses(), ws)
        self.finish('export_courses')

    def format_timetables(self, section, ws, offset):
        schedules = IScheduleContainer(section)
        if not schedules:
            return offset
        schedules = list(sorted(schedules.values(),
                                key=lambda s: s.timetable.__name__))
        for schedule in schedules:
            timetable = schedule.timetable
            self.write_header(ws, offset, 0,  "School Timetable")
            self.write(ws, offset, 1,  timetable.__name__)
            offset += 1

            self.write(ws, offset, 0,  "Consecutive periods as one")
            self.write(ws, offset, 1,
                       schedule.consecutive_periods_as_one and 'yes' or 'no')
            offset += 1

            self.write_header(ws, offset, 0,  "Day")
            self.write_header(ws, offset, 1,  "Period")
            offset += 1

            for period in schedule.periods:
                day = period.__parent__
                self.write(ws, offset, 0,  day.title)
                self.write(ws, offset, 1,  period.title)
                offset += 1
            offset += 1
        return offset

    def format_section(self, year, courses, term, section, ws, row):
        resources = [r.__name__ for r in section.resources]
        self.write(ws, row, 0, year.__name__)
        self.write(ws, row, 1, courses)
        self.write(ws, row, 2, term.__name__)
        self.write(ws, row, 3, section.__name__)
        if section.previous:
            self.write(ws, row, 4, section.previous.__name__)
        if section.next:
            self.write(ws, row, 5, section.next.__name__)
        self.write(ws, row, 6, section.title)
        if section.description:
            self.write(ws, row, 7, section.description)
        self.write(ws, row, 8, ', '.join(resources))

    def export_sections(self, wb):
        self.task_progress.force('export_sections', active=True)
        ws = wb.add_sheet("Sections")
        headers = ["School Year", "Courses", "Term", "Section ID",
                   "Previous ID", "Next ID", "Title", "Description",
                   "Resources"]
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        sections = []
        for year in ISchoolYearContainer(self.context).values():
            for term in year.values():
                for section in ISectionContainer(term).values():
                    if not list(section.courses):
                        continue
                    courses = ', '.join([c.__name__ for c in section.courses])
                    sections.append((year, courses, term.first, term,
                                     section.__name__, section))

        row = 1
        sections.sort()
        n_sections = len(sections)
        for n, (year, courses, first, term, section_id, section) in enumerate(sections):
            self.format_section(year, courses, term, section, ws, row)
            self.progress('export_sections', normalized_progress(
                    n, n_sections))
            row += 1
        self.finish('export_sections')

    def format_membership_block(self, relationship, headers):
        items = sorted(relationship.all(),
                       key=lambda item: item.__name__)
        if not items:
            return []
        table = [headers]
        for item in items:
            cells = [Text(item.__name__), Text('')]
            state = relationship.state(item)
            for x, (date, meaning, code) in enumerate(state):
                cells.append(Date(date))
                cells.append(Text(code))
            table.append(cells)
        table.append([])
        return table

    def export_section_enrollment(self, ws, year, term, section, row=0):
        row += self.print_table([
            [Header('School Year'), Header('Term'), Header('Section ID')],
            [Text(year.__name__), Text(term.__name__), Text(section.__name__)],
            [],
            ], ws, row=row)

        row += self.print_table(
            self.format_membership_block(section.instructors, [Header('Instructors')]),
            ws, row=row, col=0)

        row += self.print_table(
            self.format_membership_block(section.members, [Header('Students')]),
            ws, row=row, col=0)

        return row

    def export_sections_enrollment(self, wb):
        self.task_progress.force('export_sections_enrollment', active=True)
        ws = wb.add_sheet("SectionEnrollment")

        row = 0
        years = ISchoolYearContainer(self.context)
        total_years = len(years)
        for ny, year in enumerate(sorted(years.values(), key=lambda year: year.first)):
            total_terms = len(year)
            for nt, term in enumerate(sorted(year.values(), key=lambda term: term.first)):
                sections = ISectionContainer(term)
                total_sections = len(sections)
                for ns, section in enumerate(sorted(sections.values(),
                                                    key=lambda section: section.__name__)):
                    row = self.export_section_enrollment(
                        ws, year, term, section, row=row)
                    self.progress(
                        'export_sections_enrollment',
                        normalized_progress(
                            ny, total_years,
                            nt, total_terms,
                            ns, total_sections,
                            ))

        self.finish('export_sections_enrollment')

    def format_timetable_sections(self, year, timetable_sections, ws, row):
        headers = ["School Year", "Term", "Section ID"]
        for index, header in enumerate(headers):
            self.write_header(ws, row, index, header)
        row += 1

        for first, term, section_id, section in sorted(timetable_sections):
            self.write(ws, row, 0, year.__name__)
            self.write(ws, row, 1, term.__name__)
            self.write(ws, row, 2, section.__name__)
            row += 1
        return row + 1

    def format_timetables_block(self, timetables, ws, row):
        for timetable in timetables:
            parts = timetable.split(',')
            self.write_header(ws, row, 0, "Timetable")
            self.write(ws, row, 1, parts[0])
            self.write_header(ws, row, 2, "Consecutive")
            self.write(ws, row, 3, parts[1])
            row += 2

            self.write_header(ws, row, 0, "Day")
            self.write_header(ws, row, 1, "Period ID")
            row += 1

            parts = parts[2:]
            while parts:
                day, period = parts[:2]
                self.write(ws, row, 0, day)
                self.write(ws, row, 1, period)
                parts = parts[2:]
                row += 1
        return row + 1

    def export_section_timetables(self, wb):
        self.task_progress.force('export_section_timetables', active=True)
        ws = wb.add_sheet("SectionTimetables")

        year_sections = {}
        for year in ISchoolYearContainer(self.context).values():
            sections = year_sections[year] = {}
            for term in year.values():
                for section in ISectionContainer(term).values():
                    if not list(section.courses):
                        continue
                    timetables = []
                    for schedule in IScheduleContainer(section).values():
                        if schedule.timetable.__name__ is None:
                            # LP: #1281335
                            continue
                        parts = [schedule.timetable.__name__]
                        if schedule.consecutive_periods_as_one:
                            parts.append('yes')
                        else:
                            parts.append('no')
                        for period in schedule.periods:
                            day = period.__parent__
                            parts.append(day.title)
                            parts.append(period.title)
                        timetables.append(','.join(parts))
                    if not len(timetables):
                        continue
                    timetables = tuple(timetables)
                    timetable_sections = sections.setdefault(timetables, [])
                    timetable_sections.append((term.first, term,
                                               section.__name__, section))

        row = 0
        for ny, (year, sections) in enumerate(sorted(year_sections.items())):
            for nt, (timetables, timetable_sections) in enumerate(sorted(sections.items())):
                row = self.format_timetable_sections(year, timetable_sections,
                                                     ws, row)
                row = self.format_timetables_block(timetables, ws, row)
                self.progress('export_section_timetables', normalized_progress(
                        ny, len(year_sections), nt, len(sections)
                        ))
        self.finish('export_section_timetables')

    def format_group(self, group, ws, offset):
        fields = [lambda i: ("Group Title", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("School Year", ISchoolYear(i.__parent__).__name__, None),
                  lambda i: ("Description", i.description, None)]

        offset = self.listFields(group, fields, ws, offset)

        offset += self.print_table(
            self.format_membership_block(group.members, [Header('Members')]),
            ws, row=offset, col=0)

        offset += 1

        leaders = IAsset(group).leaders
        offset += self.print_table(
            self.format_membership_block(leaders, [Header('Leaders')]),
            ws, row=offset, col=0)

        return offset

    def export_groups(self, wb):
        self.task_progress.force('export_groups', active=True)
        ws = wb.add_sheet("Groups")
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)
        row = 0
        for ny, school_year in enumerate(sorted(school_years, key=lambda i: i.last)):
            groups = IGroupContainer(school_year)
            for ng, group in enumerate(sorted(groups.values(), key=lambda i: i.__name__)):
                row = self.format_group(group, ws, row) + 1
                self.progress('export_groups', normalized_progress(
                        ny, len(school_years), ng, len(groups)
                        ))
        self.finish('export_groups')

    def makeProgress(self):
        self.task_progress = TaskProgress(None)

    def addImporters(self, progress):
        progress.add('export_school_years', active=False,
                     title=_('School Years'), progress=0.0)
        progress.add('export_terms', active=False,
                     title=_('Terms'), progress=0.0)
        progress.add('export_school_timetables', active=False,
                     title=_('School Timetables'), progress=0.0)
        progress.add('export_resources', active=False,
                     title=_('Resources'), progress=0.0)
        progress.add('export_levels', active=False,
                     title=_('Grade Levels'), progress=0.0)
        progress.add('export_persons', active=False,
                     title=_('Persons'), progress=0.0)
        progress.add('export_contacts', active=False,
                     title=_('Contacts'), progress=0.0)
        progress.add('export_courses', active=False,
                     title=_('Courses'), progress=0.0)
        progress.add('export_sections', active=False,
                     title=_('Sections'), progress=0.0)
        progress.add('export_sections_enrollment', active=False,
                     title=_('Section Enrollment'), progress=0.0)
        progress.add('export_section_timetables', active=False,
                     title=_('Section Schedules'), progress=0.0)
        progress.add('export_groups', active=False,
                     title=_('Groups'), progress=0.0)
        progress.add('overall',
                     title=_('School Data'), progress=0.0)

    def update(self):
        super(MegaExporter, self).update()
        self.addImporters(self.task_progress)

    def render(self, workbook):
        datafile = StringIO()
        workbook.save(datafile)
        data = datafile.getvalue()
        self.setUpHeaders(data)
        return data

    def __call__(self):
        self.makeProgress()
        self.task_progress.title = _("Exporting school data")
        self.addImporters(self.task_progress)

        wb = xlwt.Workbook()
        self.export_school_years(wb)
        self.export_terms(wb)
        self.export_school_timetables(wb)
        self.export_resources(wb)
        self.export_levels(wb)
        self.export_persons(wb)
        self.export_contacts(wb)
        self.export_courses(wb)
        self.export_sections(wb)
        self.export_sections_enrollment(wb)
        self.export_section_timetables(wb)
        self.export_groups(wb)
        self.task_progress.title = _("Export complete")
        self.task_progress.force('overall', progress=1.0)
        data = self.render(wb)
        return data


class XLSReportTask(AbstractReportTask):

    default_filename = 'report.xls'
    default_mimetype = 'application/vnd.ms-excel'

    def renderReport(self, renderer, stream, *args, **kw):
        workbook = renderer(*args, **kw)
        if workbook is None:
            raise NoReportException()
        workbook.save(stream)


class RemoteMegaExporter(MegaExporter):

    base_filename = 'school'
    message_title = _('school export')
    makeProgress = ExcelExportView.makeProgress

    def render(self, workbook):
        # Return the workbook itself, should use it to save to blob directly
        return workbook


class RequestXLSReportDialog(RequestRemoteReportDialog):

    task_factory = XLSReportTask


class XLSProgressMessage(ReportMessage):
    implements(IXLSProgressMessage)


class OnXLSReportScheduled(OnPDFReportScheduled):

    message_factory = XLSProgressMessage

    def makeReportTitle(self):
        title = getattr(self.view, 'message_title', None)
        if not title:
            title = getattr(self.view, 'filename', None)
        if not title:
            title = _(u'XLS export')
        return title


class ExportLinkVielwet(ReportLinkViewlet):
    pass


class ImportLinkViewlet(flourish.page.LinkViewlet):
    pass


class RemoteImportLinkViewlet(flourish.page.ModalFormLinkViewlet):

    dialog_title = _('Upload XLS File')
