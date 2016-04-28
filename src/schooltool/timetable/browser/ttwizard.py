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
Timetable setup wizard for SchoolTool.

This module implements a the workflow described by Tom Hoffman on Jun 9 2005
on the schooltool mailing list, in ttschema-wireframes.pdf[1].

    [1] http://lists.schooltool.org/pipermail/schooltool/2005-June/001347.html

It has been slightly modified since.  You can find an up-to-date diagram
of the workflow in src/schooltool/app/browser/ftests/images/

The workflow is as follows:

    1. "New timetable"

       (The user enters a name.)

    2. "Does your school's timetable cycle use days of the week, or a rotating
        cycle?"

        Skip to step 4 if days of the week was chosen.

    3. "Enter names of days in cycle:"

        (The user enters a list of day names in a single textarea.)

    4. "Do classes begin and end at the same time each day in your school's
        timetable?"

        Continue with step 5 if "yes".
        Skip to step 6 if "no", and "cycle" was chosen in step 2.
        Skip to step 7 if "no", and "days of the week" was chosen in step 2.

    5. "Enter start and end times for each slot"

        (The user enters a list of start and end times in a single textarea.)

        Jump to step 9.

    6. "Do the start and end times vary based on the day of the week, or the
        day in the cycle?"

        Continue with step 7 if "days of week".
        Continue with step 8 if "cycle".

    7. "Enter the start and end times of each slot on each day:"

        (The user sees 5 columns of text lines, with five buttons that let him
        add an extra slot for each column.)

        Jump to step 9.

    8. "Enter the start and end times of each slot on each day:"

        (The user sees N columns of text lines, with N buttons that let him
        add an extra slot for each column.)

    9. "Do periods have names or are they simply designated by time?"

        Skip to step 14 if periods are simply designated by time.

    10. "Enter names of the periods:"

        (The user enters a list of periods in a single textarea.)

    11. "Is the sequence of periods each day the same or different?"

        Skip to step 13 if it is different

    12. "Put the periods in order for each day:"

        (The user sees a list of drop-downs.)

        Jump to step 14.

    13. "Put the periods in order:"

        (The user sees a grid of drop-downs.)

    14. "Does your school have a homeroom period?"

        Skip to step 16 if it doesn't.

    15. "Indicate which period is the homeroom period."

        (The user sees a list of drop-downs.)

    16. The timetable is created.


The shortest path through this workflow contains 7 steps, the longest contains
13 steps.

Step 16 needs the following data:

    - title (determined in step 1)
    - timetable model factory (determined in step 2)
    - a list of day IDs (determined in step 3)
    - a list of periods for each day ID
    - a list of day templates (weekday -> period_id -> start time & duration)

"""
import os

from zope.interface import Interface
from zope.schema import TextLine, Text, getFieldNamesInOrder
from zope.i18n import translate
from zope.app.form.utility import setUpWidgets
from zope.app.form.utility import getWidgetsData
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.browserpage.viewpagetemplatefile import BoundPageTemplate
from zope.container.interfaces import INameChooser
from zope.container.contained import containedEvent
from zope.event import notify
from zope.publisher.browser import BrowserView
from zope.session.interfaces import ISession
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.skin.flourish.content
import schooltool.skin.flourish.form
import schooltool.skin.flourish.page
from schooltool.app.browser.cal import day_of_week_names
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common import parse_time_range, format_time_range
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool.skin.flourish.tal import JSONDecoder
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period
from schooltool.timetable.timetable import Timetable

from schooltool.common import SchoolToolMessage as _


def getSessionData(view):
    """Return the data container stored in the session."""
    return ISession(view.request)['schooltool.ttwizard']

#
# Abstract step classes
#

class Step(BrowserView):
    """A step, one of many.

    Each step has three important methods:

        `__call__` renders the page.

        `update` processes the form, and then either stores the data in the
        session, and returns True if the form was submitted correctly, or
        returns False if it wasn't.

        `next` returns the next step.

    """
    getSessionData = getSessionData

    @property
    def label(self):
        session = self.getSessionData()
        return _("Timetable $title",
                 mapping={'title': session['title']})



class ChoiceStep(Step):
    """A step that requires the user to make a choice.

    Subclasses should provide three attributes:

        `question` -- question text

        `choices` -- a list of tuples (choice_value, choice_text)

        `key` -- name of the session dict key that will store the value.

    They should also define the `next` method.
    """

    __call__ = ViewPageTemplateFile("templates/ttwizard_choice.pt")

    def update(self):
        session = self.getSessionData()
        for n, (value, text) in enumerate(self.choices):
            if 'NEXT.%d' % n in self.request:
                session[self.key] = value
                return True
        return False


class FormStep(Step):
    """A step that presents a form.

    Subclasses should provide a `schema` attribute.

    They can override the `description` attribute and specify some informative
    text to be displayed above the form.

    They should also define the `update` and `next` methods.
    """

    __call__ = ViewPageTemplateFile("templates/ttwizard_form.pt")

    description = None

    error = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpWidgets(self, self.schema, IInputWidget)

    def widgets(self):
        return [getattr(self, name + '_widget')
                for name in getFieldNamesInOrder(self.schema)]


#
# Concrete wizard steps
#

class FirstStep(FormStep):
    """First step: enter the title for the new timetable."""

    __name__ = 'first_step'

    __call__ = ViewPageTemplateFile("templates/ttwizard.pt")

    label = _('A new timetable')

    class schema(Interface):
        title = TextLine(title=_("Title"), default=u"default")

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError:
            return False
        session = self.getSessionData()
        session['title'] = data['title']
        return True

    def next(self):
        return CycleStep


class CycleStep(ChoiceStep):
    """A step for choosing the timetable cycle."""

    __name__ = 'cycle_step'
    key = 'cycle'

    question = _("Does your school's timetable cycle use days of the week,"
                 " or a rotating cycle?")

    choices = (('weekly',   _("Days of the week")),
               ('rotating', _("Rotating cycle")))

    def next(self):
        session = self.getSessionData()
        if session['cycle'] == 'weekly':
            return IndependentDaysStep
        else:
            return DayEntryStep

    def update(self):
        success = ChoiceStep.update(self)
        session = self.getSessionData()
        if success and session['cycle'] == 'weekly':
            weekday_names = [translate(day_of_week_names[i],
                                       context=self.request)
                             for i in range(7)]
            session['day_names'] = weekday_names
        session['time_model'] = session['cycle']
        return success


class DayEntryStep(FormStep):
    """A step for entering names of days."""

    __name__ = 'day_entry_step'
    description = _("Enter names of days in cycle, one per line.")

    class schema(Interface):
        days = Text(required=False)

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError, e:
            return False
        day_names = parse_name_list(data.get('days') or '')
        if not day_names:
            self.error = _("Please enter at least one day name.")
            return False

        seen = set()
        for day in day_names:
            if day in seen:
                self.error = _("Please make sure the day names are unique.")
                return False
            seen.add(day)
        session = self.getSessionData()
        session['day_names'] = day_names
        return True

    def next(self):
        return IndependentDaysStep


class IndependentDaysStep(ChoiceStep):
    """A step for choosing if all period times are the same each day."""

    __name__ = 'independent_days_step'
    key = 'similar_days'

    question = _("Do classes begin and end at the same time each day in"
                 " your school's timetable?")

    choices = ((True,  _("Same time each day")),
               (False, _("Different times")))

    def next(self):
        session = self.getSessionData()
        if session['similar_days']:
            return SimpleSlotEntryStep
        else:
            if session['cycle'] == 'weekly':
                return WeeklySlotEntryStep
            else:
                return SequentialModelStep


class SequentialModelStep(ChoiceStep):
    """Step for choosing if start and end times vay based on the day of
    the week or the day in the cycle."""

    __name__ = 'sequential_model_step'
    key = 'time_model'

    question = _("Do start and end times vary based on the day of the week"
                 " (Monday - Friday) or the day in the cycle?")

    choices = [('weekly', _("Day of week")),
               ('rotating', _("Day in cycle"))]

    def next(self):
        session = self.getSessionData()
        if session['time_model'] == 'weekly':
            return WeeklySlotEntryStep
        else:
            return RotatingSlotEntryStep


def parse_name_list(names):
    r"""Parse a multi-line string into a list of names.

    One day name per line.  Empty lines are ignored.  Extra spaces
    are stripped.

        >>> parse_name_list(u'Day 1\n Day 2\nDay 3 \n\n\n Day 4 ')
        [u'Day 1', u'Day 2', u'Day 3', u'Day 4']
        >>> parse_name_list(u'  \n\n ')
        []
        >>> parse_name_list(u'')
        []

    """
    return [s.strip() for s in names.splitlines() if s.strip()]


def parse_time_range_list(times):
    r"""Parse a multi-line string into a list of time slots.

    One slot per line (HH:MM - HH:MM).  Empty lines are ignored.  Extra
    spaces are stripped.

        >>> parse_time_range_list(u' 9:30 - 10:25 \n \n 12:30 - 13:25 \n')
        [(datetime.time(9, 30), datetime.timedelta(0, 3300)),
         (datetime.time(12, 30), datetime.timedelta(0, 3300))]

        >>> parse_time_range_list(u'  \n\n ')
        []
        >>> parse_time_range_list(u'')
        []

        >>> parse_time_range_list(u'9:30-12:20\nbad value\nanother bad value')
        Traceback (most recent call last):
          ...
        ValueError: bad value

    """
    result = []
    for line in times.splitlines():
        line = line.strip()
        if line:
            try:
                result.append(parse_time_range(line))
            except ValueError:
                raise ValueError(line)
    return result


def format_time_range_list(times):
    r"""Format a multi-line string from a list of time slots.

    One slot per line (HH:MM - HH:MM).  Empty lines are ignored.  Extra
    spaces are stripped.

        >>> import datetime
        >>> times = [(datetime.time(9, 30), datetime.timedelta(0, 3300)),
        ...          (datetime.time(12, 30), datetime.timedelta(0, 3300))]

        >>> print format_time_range_list(times)
        09:30-10:25
        12:30-13:25

    """
    lines = []
    for tr_time, tr_delta in times:
        lines.append(format_time_range(tr_time, tr_delta))

    return '\n'.join(lines)


class SimpleSlotEntryStep(FormStep):
    """A step for entering times for classes.

    This step is used when the times are the same in each day.
    """

    __name__ = 'simple_slot_entry_step'

    description = _("Enter start and end times for each slot,"
                    " one slot (HH:MM - HH:MM) per line. "
                    "The start and end times MUST BE IN 24 HOUR FORMAT, "
                    "for example, 13:30 not 01:30 PM.")

    class schema(Interface):
        times = Text(default=u"9:30-10:25\n10:30-11:25", required=False)

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError, e:
            return False
        try:
            times = parse_time_range_list(data.get('times') or '')
        except ValueError, e:
            self.error = _("Not a valid time slot: $slot.",
                           mapping={'slot': unicode(e.args[0])})
            return False
        if not times:
            self.error = _("Please enter at least one time slot.")
            return False
        session = self.getSessionData()
        if session.get('similar_days') and session['cycle'] == 'weekly':
            session['time_slots'] = [times] * 5 + [[]] * 2
        else:
            num_days = len(session['day_names'])
            session['time_slots'] = [times] * num_days
        return True

    def next(self):
        return NamedPeriodsStep


class RotatingSlotEntryStep(Step):
    """Step for entering start and end times of slots in each day.

    This step is taken when the start/end times are different for each day,
    the rotating cycle is chosen in the CycleStep and 'day in the cycle' is
    chosen in the SequentialModelStep.
    """

    __name__ = 'rotating_slot_entry_step'
    __call__ = ViewPageTemplateFile("templates/ttwizard_slottimes.pt")

    description = _("Enter start and end times for each slot on each day,"
                    " one slot (HH:MM - HH:MM) per line. The start and "
                    "end times MUST BE IN 24 HOUR FORMAT, "
                    "for example, 13:30 not 01:30 PM.")

    error = None
    example_intervals = '8:00 - 8:45\n9:05 - 9:50\n'

    def days(self):
        """Return a list of day ids/values for the view"""
        for day_number in range(len(self.dayNames())):
            day_id = "times.%s" % day_number
            default = ""
            if day_number < 5:
                default = self.example_intervals

            value = self.request.get(day_id, default)
            yield {'id': day_id,
                   'value': value}

    def dayNames(self):
        """Return the list of day names."""
        return self.getSessionData()['day_names']

    def update(self):
        result = []
        for i, day_name in enumerate(self.dayNames()):
            s = self.request.form.get('times.%d' % i, '')
            try:
                times = parse_time_range_list(s)
            except ValueError, e:
                self.error = _("Not a valid time slot: $slot.",
                               mapping={'slot': unicode(e.args[0])})
                return False
            result.append(times)

        session = self.getSessionData()
        session['time_slots'] = result
        return True

    def next(self):
        return NamedPeriodsStep


class WeeklySlotEntryStep(RotatingSlotEntryStep):
    """Step for entering start and end times of slots in each day.

    This step is taken when the start/end times are different for each day,
    and the weekly cycle is chosen in the CycleStep or in the
    SequentialModelStep.
    """

    __name__ = 'weekly_slot_entry_step'

    def dayNames(self):
        """Return the list of day names."""
        return [translate(day_of_week_names[i], context=self.request)
                for i in range(7)]

    def update(self):
        """Store the slots in the session.

        If a rotating timetable cycle is selected and slots vary based on day
        of week, each day must have the same number of slots.
        """
        result = RotatingSlotEntryStep.update(self)
        session = self.getSessionData()
        if (result and session['cycle'] == 'rotating'
            and session.get('time_model') == 'weekly'):
            slots = session['time_slots']
            assert len(slots) == 7 # Monday - Sunday
            num_slots = len(slots[0])
        return result


class NamedPeriodsStep(ChoiceStep):
    """A step for choosing if periods have names or are designated by time"""

    __name__ = 'named_periods_step'
    key = 'named_periods'

    question = _("Do periods have names or are they simply"
                 " designated by time?")

    @property
    def choices(self):
        session = self.getSessionData()
        if session['cycle'] == 'rotating':
            choices = ((True,  _("Have names")),)
        else:
            choices = ((True,  _("Have names")),
                       (False, _("Designated by time")))
        return choices

    def next(self):
        session = self.getSessionData()
        if session['named_periods']:
            return PeriodNamesStep
        else:
            periods_order = default_period_names(session['time_slots'])
            session['periods_order'] = periods_order
            return HomeroomStep


def default_period_names(time_slots):
    """Derive period names and order from time slots.

        >>> from datetime import time, timedelta
        >>> periods = [(time(9, 0), timedelta(minutes=50)),
        ...            (time(12, 35), timedelta(minutes=50)),
        ...            (time(14, 15), timedelta(minutes=55))]
        >>> periods2 = [(time(9, 10), timedelta(minutes=50)),
        ...             (time(12, 35), timedelta(minutes=50))]
        >>> default_period_names([periods] * 3 + [periods2])
        [['09:00-09:50', '12:35-13:25', '14:15-15:10'],
         ['09:00-09:50', '12:35-13:25', '14:15-15:10'],
         ['09:00-09:50', '12:35-13:25', '14:15-15:10'],
         ['09:10-10:00', '12:35-13:25']]

    """
    return [[format_time_range(tstart, duration)
             for tstart, duration in slots]
            for slots in time_slots]


class PeriodNamesStep(FormStep):
    """A step for entering names of periods"""

    __name__ = 'period_names_step'
    description = _("Enter names of periods, one per line.")

    class schema(Interface):
        periods = Text(required=False)

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError, e:
            return False
        periods = parse_name_list(data.get('periods') or '')
        min_periods = self.requiredPeriods()
        if len(periods) < min_periods:
            self.error = _("Please enter at least $number periods.",
                           mapping={'number': min_periods})
            return False
        seen = set()
        for period in periods:
            if period in seen:
                self.error = _("Please make sure the period names are unique.")
                return False
            seen.add(period)
        session = self.getSessionData()
        session['period_names'] = periods
        return True

    def requiredPeriods(self):
        """Return the maximum number of slots there can be on a day."""
        session = self.getSessionData()
        times = session['time_slots']
        return max(map(len, times))

    def next(self):
        return PeriodSequenceSameStep


class PeriodSequenceSameStep(ChoiceStep):
    """A step for choosing whether periods are the same on all days"""

    __name__ = 'period_sequence_same_step'
    key = 'periods_same'

    question = _("Is the sequence of periods each day the same or different?")

    choices = ((True,  _("Same")),
               (False, _("Different")))

    def next(self):
        session = self.getSessionData()
        if session[self.key]:
            return PeriodOrderSimple
        else:
            return PeriodOrderComplex


class PeriodOrderSimple(Step):
    """Step to put periods in order if all days are the same."""

    __name__ = 'period_order_simple_step'

    __call__ = ViewPageTemplateFile('templates/ttwizard_period_order1.pt')

    description = _('Please put the periods in order:')

    error = None

    def periods(self):
        return self.getSessionData()['period_names']

    def numPeriods(self):
        return max([len(day) for day in self.getSessionData()['time_slots']])

    def update(self):
        result = []
        periods = self.getSessionData()['period_names']
        for i in range(self.numPeriods()):
            name = 'period_%d' % i
            if name not in self.request:
                self.error = _('Please provide all periods.')
                return False
            result.append(self.request[name])

        # Validate that all periods are selected
        seen = set()
        errors = set()
        for period in result:
            if period not in seen:
                seen.add(period)
            else:
                errors.add(period)
        if errors:
            self.error = _('The following periods were selected more'
                           ' than once: $periods',
                           mapping={'periods': ', '.join(errors)})
            return False

        day_names = self.getSessionData()['day_names']
        self.getSessionData()['periods_order'] = [result] * len(day_names)
        return True

    def next(self):
        return HomeroomStep


class PeriodOrderComplex(Step):
    """Step to put periods in order if order is different on different days"""

    __name__ = 'period_order_complex_step'
    __call__ = ViewPageTemplateFile('templates/ttwizard_period_order2.pt')

    description = _('Please put the periods in order for each day:')

    error = None

    def periods(self):
        return self.getSessionData()['period_names']

    def days(self):
        session = self.getSessionData()
        return session['day_names']

    def numSlots(self):
        session = self.getSessionData()
        if (session['cycle'] != session.get('time_model')):
            np = len(self.periods())
            return [np for day in self.getSessionData()['day_names']]
        return [len(day) for day in self.getSessionData()['time_slots']]

    def update(self):
        result = []
        periods = self.periods()
        numSlots = self.numSlots()
        for i in range(len(self.days())):
            day = []
            for j in range(numSlots[i]):
                name = 'period_%d_%d' % (i, j)
                if name not in self.request:
                    self.error = _('Please provide all periods.')
                    return False
                day.append(self.request[name])
            result.append(day)

        # Validate that all periods are selected
        errors = set()
        for i, day in enumerate(self.days()):
            seen = set()
            for period in result[i]:
                if period not in seen:
                    seen.add(period)
                else:
                    error = _("$period on day $day",
                              mapping={'period': period, 'day': self.days()[i]})
                    errors.add(translate(error, context=self.request))
        if errors:
            self.error = _('The following periods were selected more'
                           ' than once: $periods',
                           mapping={'periods': ', '.join(errors)})
            return False

        self.getSessionData()['periods_order'] = result
        return True

    def next(self):
        return HomeroomStep


class HomeroomStep(ChoiceStep):
    """A step for choosing whether the school has homeroom periods."""

    __name__ = 'homeroom_step'
    key = 'homeroom'

    question = _("Do you check student attendance for the day in a homeroom"
                 " period or equivalent?")

    choices = ((True,  _("Yes")),
               (False, _("No")))

    def next(self):
        session = self.getSessionData()
        if session['homeroom']:
            return HomeroomPeriodsStep
        else:
            return FinalStep


class HomeroomPeriodsStep(Step):
    """Step to indicate the homeroom period for each day."""

    __name__ = 'homeroom_periods_step'
    __call__ = ViewPageTemplateFile('templates/ttwizard_homeroom.pt')

    description = _('Please indicate the homeroom period(s) for each day:')

    error = None

    def periodsInOrder(self):
        return self.getSessionData()['periods_order']

    def days(self):
        session = self.getSessionData()
        return session['day_names']

    def update(self):
        result = []
        for daynr, periods in enumerate(self.periodsInOrder()):
            homeroom_period_ids = []
            for period in periods:
                period_id = 'homeroom_%d_%s' % (daynr, period)
                if period_id in self.request:
                    homeroom_period_ids.append(period)
            result.append(homeroom_period_ids)
        self.getSessionData()['homeroom_periods'] = result
        return True

    def next(self):
        return FinalStep


class FinalStep(Step):
    """Final step: create the timetable."""

    __name__ = 'final_step'

    def __call__(self):
        self.createAndAdd()
        self.request.response.redirect(
            absoluteURL(self.context, self.request))

    def createAndAdd(self):
        timetable = self.createTimetable()
        self.add(timetable)
        self.setUpTimetable(timetable)
        return timetable

    def update(self):
        return True

    def next(self):
        return FirstStep

    def createTimetable(self):
        session = self.getSessionData()
        app = ISchoolToolApplication(None)
        tzname = IApplicationPreferences(app).timezone

        # XXX: quick fix for date range
        owner = IHaveTimetables(self.context)
        first, last = owner.first, owner.last

        timetable = Timetable(
            first, last,
            title=session['title'],
            timezone=tzname)
        return timetable

    def addTimeSlotTemplates(self, day_template_schedule, days):
        for key, title, time_slots in days:
            template = DayTemplate(title=title)
            day_template_schedule.templates[key] = template
            name_chooser = INameChooser(template)
            for tstart, duration in time_slots:
                timeslot = TimeSlot(tstart, duration, activity_type=None)
                key = name_chooser.chooseName('', timeslot)
                template[key] = timeslot

    def createTimeSlots(self, timetable, model, day_titles, time_slots):
        if model == 'weekly':
            timetable.time_slots, object_event = containedEvent(
                WeekDayTemplates(), timetable, 'time_slots')
            days = [
                (unicode(n),
                 translate(day_of_week_names[n], context=self.request),
                 time_slot)
                for n, time_slot in zip(range(7), time_slots)]
        elif model == 'rotating':
            timetable.time_slots, object_event = containedEvent(
                SchoolDayTemplates(), timetable, 'time_slots')
            # An UI limitations at the time of writing
            time_slots = time_slots[:len(day_titles)]
            day_ids = [unicode(n) for n in range(len(day_titles))]
            days = zip(day_ids, day_titles, time_slots)
        else:
            raise NotImplementedError()

        notify(object_event)
        timetable.time_slots.initTemplates()

        self.addTimeSlotTemplates(timetable.time_slots, days)

    def addPeriodTemplates(self, day_template_schedule, days):
        for day_key, day_title, periods in days:
            template = DayTemplate(title=day_title)
            day_template_schedule.templates[day_key] = template

            name_chooser = INameChooser(template)
            for period_title, activity_type in periods:
                period = Period(title=period_title,
                                activity_type=activity_type)
                key = name_chooser.chooseName('', period)
                template[key] = period

    def createPeriods(self, timetable, model, day_titles,
                      period_names, homeroom_periods):
        if model == 'weekly':
            timetable.periods, object_event = containedEvent(
                WeekDayTemplates(), timetable, 'periods')
            day_ids = [unicode(n) for n in range(min(len(day_titles), 7))]
        elif model == 'rotating':
            timetable.periods, object_event = containedEvent(
                SchoolDayTemplates(), timetable, 'periods')
            day_ids = [unicode(n) for n in range(len(day_titles))]
        else:
            raise NotImplementedError()

        notify(object_event)
        timetable.periods.initTemplates()

        periods = []
        for titles, homeroom_titles in zip(period_names, homeroom_periods):
            periods.append(
                [(title, title in homeroom_titles and 'homeroom' or 'lesson')
                 for title in titles])

        days = zip(day_ids, day_titles, periods)

        self.addPeriodTemplates(timetable.periods, days)

    def setUpTimetable(self, timetable):
        session = self.getSessionData()

        # XXX: would be nice to set theese properly in previous steps
        periods_model = session['cycle']
        time_model = session.get('time_model', 'rotating')
        if periods_model == 'weekly':
            time_model = 'weekly'
        if periods_model == 'rotating' and session['similar_days']:
            time_model = 'rotating'

        assert time_model in ('weekly', 'rotating')
        assert periods_model in ('weekly', 'rotating')

        # An UI limitations at the time of writing
        assert not(time_model == 'rotating' and periods_model != 'rotating')

        day_titles = session['day_names']

        # set time slots
        time_slots = session['time_slots']
        self.createTimeSlots(timetable, time_model, day_titles, time_slots)

        # set periods
        period_names = session['periods_order']
        if session['homeroom']:
            homeroom_periods = session['homeroom_periods']
        else:
            homeroom_periods = [tuple() for day in day_titles]

        self.createPeriods(timetable, periods_model, day_titles,
                           period_names, homeroom_periods)

    def add(self, timetable):
        """Add the timetable to self.context."""
        nameChooser = INameChooser(self.context)
        key = nameChooser.chooseName('', timetable)
        self.context[key] = timetable


#
# The wizard itself
#

class TimetableWizard(BrowserView):
    """View for defining a new timetable."""

    getSessionData = getSessionData

    def getLastStep(self):
        session = self.getSessionData()
        step_class = session.get('last_step', FirstStep)
        step = step_class(self.context, self.request)
        return step

    def rememberLastStep(self, step):
        session = self.getSessionData()
        session['last_step'] = step.__class__

    def __call__(self):
        if 'CANCEL' in self.request:
            self.rememberLastStep(FirstStep(self.context, self.request))
            self.request.response.redirect(
                    absoluteURL(self.context, self.request))
            return
        current_step = self.getLastStep()
        if current_step.update():
            next = current_step.next()
            current_step = next(self.context, self.request)
        self.rememberLastStep(current_step)
        return current_step()


class FlourishTimetableWizard(flourish.page.WideContainerPage, TimetableWizard):

    _state = None
    _session = None
    current_step = None

    def getLastStep(self):
        raise NotImplemented('No longer used.')

    def rememberLastStep(self, step):
        raise NotImplemented('No longer used.')

    @property
    def state(self):
        if self._state is None:
            if 'viewstate' in self.request:
                decoder = JSONDecoder()
                self._state = decoder.decode(self.request['viewstate'])
                slots = self._state.get('time_slots')
                if slots is not None:
                    self._state['time_slots'] = [
                        parse_time_range_list(day) for day in slots]
            else:
                self._state = {}
        if not self._state.get('steps'):
            self._state['steps'] = []
        return self._state

    @property
    def json_state(self):
        state = self.state
        slots = state.get('time_slots')
        if slots is not None:
            state['time_slots'] = [
                format_time_range_list(day) for day in slots]
        return state

    def queryStep(self, name):
        return flourish.content.queryContentProvider(
            self.context, self.request, self, name)

    def nextURL(self):
        link = flourish.content.queryContentProvider(
            self.context, self.request, self, 'done_link')
        if link is not None:
            return link.url
        return absoluteURL(self.context, self.request)

    def update(self):
        flourish.page.WideContainerPage.update(self)

        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return

        steps = self.state['steps']

        if 'STEP_BACK' in self.request:
            if len(steps) > 1:
                steps.pop()
            self.current_step = self.queryStep(steps[-1])
            return

        if not steps:
            first_step_name = FirstStep.__dict__['__name__']
            self.current_step = self.queryStep(first_step_name)
            steps.append(self.current_step.__name__)
            return

        self.current_step = self.queryStep(steps[-1])

        step = self.current_step
        step.update()

        if step.finished:
            next_step = step.next()
            self.current_step = next_step
            steps.append(next_step.__name__)


def flourishStep(base, auto_template=True):

    template = None
    if auto_template and isinstance:
        if isinstance(base.__call__, BoundPageTemplate):
            filename = os.path.split(base.__call__.filename)[-1]
            template = os.path.join('templates', 'f_%s' % filename)

    def getSessionData(self):
        return self.view.state
    def update(self):
        self.finished = base.update(self)
    def next(self):
        cls = base.next(self)
        next_step_name = cls.__dict__['__name__']
        return self.view.queryStep(next_step_name)
    class_dict = {
        'getSessionData': lambda self: self.view.state,
        'update': update,
        'next': next,
        }
    if template is not None:
        class_dict['template'] = ViewPageTemplateFile(template)
    new_class = type('Flourish%s' % base.__name__,
                     (flourish.content.ContentProvider, base),
                     class_dict)
    return new_class


FlourishFirstStep = flourishStep(FirstStep, auto_template=False)
FlourishCycleStep = flourishStep(CycleStep)
FlourishDayEntryStep = flourishStep(DayEntryStep)
FlourishIndependentDaysStep = flourishStep(IndependentDaysStep)
FlourishSequentialModelStep = flourishStep(SequentialModelStep)
FlourishSimpleSlotEntryStep = flourishStep(SimpleSlotEntryStep)
FlourishRotatingSlotEntryStep = flourishStep(RotatingSlotEntryStep)
FlourishWeeklySlotEntryStep = flourishStep(WeeklySlotEntryStep)
FlourishNamedPeriodsStep = flourishStep(NamedPeriodsStep)
FlourishPeriodNamesStep = flourishStep(PeriodNamesStep)
FlourishPeriodSequenceSameStep = flourishStep(PeriodSequenceSameStep)
FlourishPeriodOrderSimple = flourishStep(PeriodOrderSimple)
FlourishPeriodOrderComplex = flourishStep(PeriodOrderComplex)
FlourishHomeroomStep = flourishStep(HomeroomStep)
FlourishHomeroomPeriodsStep = flourishStep(HomeroomPeriodsStep)


class FlourishFinalStep(flourish.content.ContentProvider, FinalStep):
    timetable = None

    getSessionData = lambda self: self.view.state
    next = lambda self: None

    def render(self, *args, **kw):
        # XXX: risky:
        if self.timetable is None:
            self.timetable = self.createAndAdd()
        self.request.response.redirect(
            absoluteURL(self.timetable, self.request))
        return ''
