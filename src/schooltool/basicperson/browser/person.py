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
Basic person browser views.
"""

from zope.interface import Interface, implements
from zope.container.interfaces import INameChooser
from zope.app.form.browser.interfaces import ITerms
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts
from zope.component import getUtility, queryMultiAdapter, getMultiAdapter
from zope.i18n import translate
from z3c.form import form, field, button, validator
from z3c.form.interfaces import DISPLAY_MODE
from zope.interface import invariant, Invalid
from zope.interface import directlyProvides
from zope.intid.interfaces import IIntIds
from zope.schema import Password, TextLine, Choice, List, Date
from zope.schema import ValidationError
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy
from zope.proxy import sameProxiedObjects

from reportlab.lib import units
import z3c.form.interfaces
import zc.table.column
from zc.table.interfaces import ISortableColumn
from z3c.form.validator import SimpleFieldValidator

from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.browser.app import EditRelationships
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin
from schooltool.app.browser.states import TemporalRelationshipAddTableMixin
from schooltool.app.browser.states import TemporalRelationshipRemoveTableMixin
from schooltool.app.browser.states import EditTemporalRelationships
from schooltool.app.browser.report import ReportPDFView
from schooltool.app.browser.report import DefaultPageTemplate
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.app.membership import Membership
from schooltool.app.states import INACTIVE
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.common.inlinept import InheritTemplate
from schooltool.course.interfaces import ISection
from schooltool.course.section import is_student
from schooltool.basicperson.demographics import LEAVE_SCHOOL_FIELDS
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.contact.interfaces import IContactable
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.interfaces import IGroup
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.browser.person import PersonTable, PersonTableFormatter
from schooltool.person.browser.person import PersonTableFilter
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.relationship.temporal import ACTIVE
from schooltool.report.report import OldReportTask
from schooltool.report.browser.report import RequestRemoteReportDialog
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin.containers import TableContainerView
from schooltool.skin import flourish
from schooltool.skin.flourish.interfaces import IViewletManager
from schooltool.skin.flourish.form import FormViewlet
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager
from schooltool.skin.flourish.content import ContentProvider
from schooltool import table
from schooltool.table.catalog import IndexedLocaleAwareGetterColumn
from schooltool.task.interfaces import IMessageContainer
from schooltool.task.tasks import MessageCatalog
from schooltool.task.tasks import getLastMessagesReadTime
from schooltool.task.tasks import markMessagesRead
from schooltool.task.browser.task import MessageColumn
from schooltool.term.interfaces import IDateManager
from schooltool.term.interfaces import ITerm

from schooltool.common import SchoolToolMessage as _


class BasicPersonContainerView(TableContainerView):
    """A Person Container view."""
    template = ViewPageTemplateFile("templates/container.pt")
    delete_template = ViewPageTemplateFile("templates/person_container_delete.pt")

    index_title = _("Person index")

    def isDeletingHimself(self):
        person = IPerson(self.request.principal, None)
        return person in self.itemsToDelete

    @property
    def schoolyears(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        return syc


class FlourishBasicPersonContainerView(flourish.page.Page):
    """A Person Container view."""

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')


class PersonContainerLinks(flourish.page.RefineLinksViewlet):
    """Person container links viewlet."""


class PersonLinks(flourish.page.RefineLinksViewlet):
    """Person links viewlet."""

    @property
    def title(self):
        return self.context.title


class PersonImportLinks(flourish.page.RefineLinksViewlet):
    """Person container import links viewlet."""


class PersonSettingsLinks(flourish.page.RefineLinksViewlet):
    """Person settings links viewlet."""


class PersonActionsLinks(flourish.page.RefineLinksViewlet):
    """Person actions links viewlet."""


class IPersonAddForm(IBasicPerson):

    group = Choice(
        title=_(u"Group"),
        description=_(u"You can select one group membership now.  Manage multiple memberships after account creation."),
        source="schooltool.basicperson.group_vocabulary",
        required=False)

    advisor = Choice(
        title=_(u"Advisor"),
        source="schooltool.basicperson.advisor_vocabulary",
        required=False)

    username = TextLine(
        title=_("Username"),
        description=_(u"Cannot begin with '+' or '@,' contain non-ascii characters or '/.'"),
        required=True)

    password = Password(
        title=_("Password"),
        description=_(u"Users cannot log in until a password is assigned."),
        required=False)

    confirm = Password(
        title=_("Confirm password"),
        required=False)

    @invariant
    def isPasswordConfirmed(person):
        if person.password != person.confirm:
            raise Invalid(_(u"Passwords do not match"))


class IPhotoField(Interface):

    photo = flourish.fields.Image(
        title=_('Photo'),
        description=_('An image file that will be converted to a JPEG no larger than 99x132 pixels (3:4 aspect ratio). Uploaded images must be JPEG or PNG files smaller than 10 MB'),
        size=(99,132),
        format='JPEG',
        required=False)


class ILevelField(Interface):

    level = Choice(
        title=_('Grade Level'),
        vocabulary='schooltool.level.level.levelvocabulary',
        required=False)


class PersonAddFormAdapter(object):
    implements(IPersonAddForm)
    adapts(IBasicPerson)

    def __init__(self, context):
        self.__dict__['context'] = context

    password = None

    def __setattr__(self, name, value):
        if name == 'password':
            self.context.setPassword(value)
        else:
            setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class PhotoFieldFormAdapter(object):

    adapts(IBasicPerson)
    implements(IPhotoField)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __setattr__(self, name, value):
        setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class UsernameAlreadyUsed(ValidationError):
    __doc__ = _("This username is already in use")


class UsernameBadName(ValidationError):
    __doc__ = _("Names cannot begin with '+' or '@' or contain '/'")


class UsernameNonASCII(ValidationError):
    __doc__ = _("Usernames cannot contain non-ascii characters")


class UsernameValidator(SimpleFieldValidator):

    @property
    def container(self):
        return self.context

    def validate(self, username):
        super(UsernameValidator, self).validate(username)
        if username is not None:
            if username in self.container:
                raise UsernameAlreadyUsed(username)
            try:
                INameChooser(self.container).checkName(username, None)
            except ValueError:
                raise UsernameBadName(username)
        # XXX: this has to be fixed
        # XXX: SchoolTool should handle UTF-8
        try:
            username.encode('ascii')
        except UnicodeEncodeError:
            raise UsernameNonASCII(username)


validator.WidgetValidatorDiscriminators(UsernameValidator,
                                        field=IPersonAddForm['username'])


class PasswordsDontMatch(ValidationError):
    __doc__ = _(u"Passwords do not match")


class PasswordValidator(SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the password error next to the widget!
        super(PasswordValidator, self).validate(value)
        confirm_widget = self.view.widgets['confirm']
        confirm_value = self.request.get(confirm_widget.name)
        if value is not None and value != confirm_value:
            raise PasswordsDontMatch()


validator.WidgetValidatorDiscriminators(PasswordValidator,
                                        field=IPersonAddForm['password'])


class PersonForm(object):

    formErrorsMessage = _('Please correct the marked fields below.')

    def generateExtraFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        if IBasicPerson.providedBy(self.context):
            limit_keys = [group.__name__ for group in self.context.groups]
        else:
            limit_keys = []
        for field_desc in field_descriptions.filter_keys(limit_keys):
            fields += field_desc.makeField()
        return fields


class PersonView(PersonForm, form.DisplayForm):

    template = ViewPageTemplateFile('templates/person_view.pt')

    @property
    def label(self):
        return self.context.title

    def update(self):
        self.fields = field.Fields(IBasicPerson)
        self.fields += self.generateExtraFields()
        super(PersonView, self).update()

    def __call__(self):
        self.update()
        return self.render()


class FlourishPersonView(flourish.page.Page):
    """Person index.html view."""

    @property
    def subtitle(self):
        if is_student(self.context):
            result = []
            levels = self.context.levels
            for level in levels.on(self.request.util.today).any(ACTIVE):
                result.append(level)
            if result:
                return ', '.join([level.title for level in result])


class FlourishPersonInfo(flourish.page.Content):
    body_template = ViewPageTemplateFile('templates/f_person_view_details.pt')

    def markRead(self):
        auth_person = IPerson(self.request.principal, None)
        if (auth_person is None or
            not sameProxiedObjects(auth_person, self.context)):
            return # not looking at his own homepage
        markMessagesRead(self.context)

    def update(self):
        self.markRead()
        super(FlourishPersonInfo, self).update()

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    @property
    def done_link(self):
        done_link = self.request.get('done_link', None)
        if done_link is not None:
            return done_link
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/persons'


class PersonAddFormBase(PersonForm, form.AddForm):
    """Person add form for basic persons."""

    _groups = None
    _advisors = None

    def update(self):
        self.fields = field.Fields(IPersonAddForm)
        self.fields += self.generateExtraFields()
        super(PersonAddFormBase, self).update()

    def updateActions(self):
        super(PersonAddFormBase, self).updateActions()
        self.actions['add'].addClass('button-ok')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        super(PersonAddFormBase, self).handleAdd.func(self, action)

    def create(self, data):
        person = self._factory(data['username'], data['first_name'],
                               data['last_name'])
        data.pop('confirm')
        group = data.pop('group')
        advisor = data.pop('advisor')
        form.applyChanges(self, person, data)
        self._groups = []
        if group is not None:
            self._groups.append(group)
        self._advisors = []
        if advisor is not None:
            self._advisors.append(advisor)
        self._person = person
        return person

    def nextURL(self):
        return absoluteURL(self._person, self.request)

    @property
    def _factory(self):
        return getUtility(IPersonFactory)

    def add(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        name = person.username
        self.context[name] = person
        for group in self._groups:
            person.groups.add(group)
        for advisor in self._advisors:
            person.advisors.add(advisor)
        return person


class PersonAddView(PersonAddFormBase):
    """Person add form for basic persons."""
    label = _("Add new person")
    template = ViewPageTemplateFile('templates/person_add.pt')

    def updateActions(self):
        super(PersonAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        super(PersonAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class ITempPersonList(Interface):
    usernames = List(
        title=_('Usernames'),
        value_type=TextLine(
            title=_('Username'),
            required=False),
        required=False,
        )


class TempPersonList(object):
    implements(ITempPersonList)

    def __init__(self):
        self.usernames = []


class MultiplePersonAddView(form.Form):
    template = ViewPageTemplateFile('templates/person_add_multiple.pt')
    label = _("Add multiple persons")
    fields = field.Fields(ITempPersonList)
    addform = None
    temp_content = None

    def __init__(self, *args, **kw):
        self.temp_content = TempPersonList()
        super(MultiplePersonAddView, self).__init__(*args, **kw)

    def getContent(self):
        return self.temp_content

    def buildAddForm(self):
        self.addform = PersonAddSubForm(self.context, self.request, self)
        n = len(self.widgets['usernames'].value)
        self.addform.prefix = 'addform_%d.' % n

    def updateWidgets(self):
        super(MultiplePersonAddView, self).updateWidgets()
        self.widgets['usernames'].mode = z3c.form.interfaces.HIDDEN_MODE
        self.buildAddForm()

    def update(self):
        super(MultiplePersonAddView, self).update()
        data, errors = self.extractData(setErrors=False)
        form.applyChanges(self, self.getContent(), data)
        self.addform.update()

    def appendAdded(self, username):
        usernames = self.widgets['usernames'].value
        usernames.append(username)
        self.widgets['usernames'].value = usernames
        content = self.getContent()
        content.usernames = usernames

    def render(self):
        if self.addform._finishedAdd:
            self.appendAdded(self.addform._person.__name__)
            # And build a fresh add form.
            self.buildAddForm()
            self.addform.update()
        return super(MultiplePersonAddView, self).render()

    @property
    def addedPersons(self):
        app_persons = ISchoolToolApplication(None)['persons']
        content = self.getContent()
        if not content.usernames:
            return []
        return [app_persons[username]
                for username in content.usernames
                if username in app_persons]

    def updateActions(self):
        super(MultiplePersonAddView, self).updateActions()
        self.actions['done'].addClass('button-neutral')

    @button.buttonAndHandler(_("Done"))
    def handle_done_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishMultiplePersonAddView(MultiplePersonAddView):
    template = InheritTemplate(flourish.page.Page.template)

    def buildAddForm(self):
        self.addform = FlourishPersonAddSubForm(
            self.context, self.request, self)
        n = len(self.widgets['usernames'].value)
        self.addform.prefix = 'addform_%d.' % n


class PersonAddSubForm(PersonAddFormBase):
    template = ViewPageTemplateFile('templates/person_add_subform.pt')

    def __init__(self, context, request, parentForm):
        self.parentForm = parentForm
        super(PersonAddSubForm, self).__init__(context, request)

    def update(self):
        super(PersonAddSubForm, self).update()
        for action in self.parentForm.actions.executedActions:
            handler = queryMultiAdapter(
                (self, self.request, self.getContent(), action),
                interface=z3c.form.interfaces.IActionHandler)
            if handler is not None:
                handler()


class FlourishPersonAddSubForm(PersonAddSubForm):
    template = ViewPageTemplateFile('templates/f_person_add_subform.pt')


class PersonEditView(PersonForm, form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/person_add.pt')

    def update(self):
        self.fields = field.Fields(IBasicPerson)
        self.fields += self.generateExtraFields()
        super(PersonEditView, self).update()

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(PersonEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change information for ${fullname}',
                 mapping={'fullname': self.context.title})


class FlourishPersonEditView(flourish.page.Page, PersonEditView):

    label = None

    def update(self):
        self.buildFieldsetGroups()
        self.fields = field.Fields(IBasicPerson)
        self.fields += field.Fields(IPhotoField)
        self.fields += self.generateExtraFields()
        form.EditForm.update(self)

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handleApply(self, action):
        super(FlourishPersonEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    def makeRows(self, fields, cols=1):
        rows = []
        while fields:
            rows.append(fields[:cols])
            fields = fields[cols:]
        return rows

    def makeFieldSet(self, fieldset_id, legend, fields, cols=1):
        result = {
            'id': fieldset_id,
            'legend': legend,
            }
        result['rows'] = self.makeRows(fields, cols)
        return result

    def buildFieldsetGroups(self):
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix', 'preferred_name']),
            'details': (
                _('Details'), ['gender', 'birth_date', 'photo']),
            'demographics': (
                _('Demographics'), list(self.generateExtraFields())),
            }
        self.fieldset_order = (
            'full_name', 'details', 'demographics')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result


class PersonTerm(object):
    """A term for displaying a person."""
    implements(ITitledTokenizedTerm)

    def __init__(self, value):
        self.title = value.title
        self.token = value.__name__
        self.value = value


class TermsBase(object):
    """Base terms implementation."""

    implements(ITerms)

    def factory(self, value):
        raise NotImplementedError(
            "Term Factory must be provided by inheriting classes.")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getTerm(self, value):
        if value not in self.context:
            raise LookupError(value)
        return self.factory(value)

    def getValue(self, token):
        if token not in self.context:
            raise LookupError(token)
        return token


class PersonTerms(TermsBase):
    """Displaying persons."""
    factory = PersonTerm

    def getValue(self, token):
        if token not in self.context:
            raise LookupError(token)
        app = ISchoolToolApplication(None)
        return app['persons'][token]


class GroupTerm(object):
    """A term for displaying a group."""
    implements(ITitledTokenizedTerm)

    def __init__(self, value):
        self.title = value.title
        self.token = value.__name__
        self.value = value


class GroupTerms(TermsBase):
    """Displaying groups."""

    factory = GroupTerm


class PersonAdvisorView(RelationshipViewBase):
    """View class for adding/removing advisors to/from a person."""

    __used_for__ = IBasicPerson

    current_title = _("Current Advisors")
    available_title = _("Add Advisors")

    @property
    def title(self):
        return _("Advisors of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        """Return a list of current advisors."""
        return self.context.advisors

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisors


class EditPersonRelationships(EditRelationships):

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class EditPersonTemporalRelationships(EditTemporalRelationships):

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getTargets(self, keys):
        if not keys:
            return None
        app = ISchoolToolApplication(None)
        persons = [
            app['persons'].get(username)
            for username in keys
            ]
        return persons


class FlourishPersonAdvisorView(EditPersonTemporalRelationships):

    app_states_name = 'person-advisors'
    dialog_title_template = _("Assign advisor ${target}")

    current_title = _('Current advisors')
    available_title = _('Available advisors')

    def getSelectedItems(self):
        return self.context.advisors

    def getCollection(self):
        return self.context.advisors


class PersonAdviseeView(RelationshipViewBase):
    """View class for adding/removing advisees to/from a person."""

    __used_for__ = IBasicPerson

    current_title = _("Current Advisees")
    available_title = _("Add Advisees")

    @property
    def title(self):
        return _("Advisees of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        """Return a list of current advisees."""
        return self.context.advisees

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisees


class FlourishPersonAdviseeView(EditPersonTemporalRelationships):

    app_states_name = 'person-advisors'
    dialog_title_template = _("Assign advisee ${target}")

    current_title = _("Current advisees")
    available_title = _("Available advisees")

    def getSelectedItems(self):
        return self.context.advisees

    def getCollection(self):
        return self.context.advisees


class IFlourishPersonInfoManager(IViewletManager):
    pass


class FlourishPersonInfoManager(ViewletManager):
    pass


class FlourishAdvisoryViewlet(Viewlet):
    """A viewlet showing the advisors/advisees of a person."""

    template = ViewPageTemplateFile('templates/f_advisoryViewlet.pt')

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishGeneralViewlet(FormViewlet):
    """A viewlet showing the core attributes of a person."""

    template = ViewPageTemplateFile('templates/f_generalViewlet.pt')
    mode = DISPLAY_MODE

    def getFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        for field_desc in field_descriptions.values():
            fields += field_desc.makeField()
        return fields

    @property
    def filtered_widgets(self):
        result = [widget for widget in self.widgets.values()
                  if widget.value]
        return result

    @property
    def heading(self):
        attrs = ['prefix', 'first_name', 'middle_name', 'last_name', 'suffix']
        values = []
        for attr in attrs:
            value = getattr(self.context, attr)
            if value:
                values.append(value)
        return ' '.join(values)

    def makeRow(self, attr, value):
        if value is None:
            value = u''
        return {
            'label': attr,
            'value': unicode(value),
            }

    @property
    def table(self):
        rows = []
        fields = field.Fields(IBasicPerson)
        fields += field.Fields(IPerson).select('username')
        for attr in fields:
            value = getattr(self.context, attr)
            if value:
                label = fields[attr].field.title
                if attr == 'gender':
                    vocabulary = IBasicPerson[attr].vocabulary
                    message = vocabulary.getTermByToken(value).title
                    value = translate(message, context=self.request)
                rows.append(self.makeRow(label, value))
        return rows

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    def update(self):
        self.fields = self.getFields()
        super(FlourishGeneralViewlet, self).update()

    def has_photo(self):
        return self.context.photo is not None

    def table_class(self):
        result = 'person-view-demographics'
        if self.has_photo():
            result += ' show-photo'
        return result


###############  Base class of all group-aware add views ################
class PersonAddViewBase(PersonAddFormBase):

    id = 'person-form'
    template = ViewPageTemplateFile('templates/person_form.pt')

    def makeRows(self, fields, cols=1):
        rows = []
        while fields:
            rows.append(fields[:cols])
            fields = fields[cols:]
        return rows

    def makeFieldSet(self, fieldset_id, legend, fields, cols=1):
        result = {
            'id': fieldset_id,
            'legend': legend,
            }
        result['rows'] = self.makeRows(fields, cols)
        return result

    def fieldsets(self):
        result = []
        sources = [
            (self.base_id, self.base_legend, list(self.getBaseFields())),
            (self.demo_id, self.demo_legend, list(self.getDemoFields())),
            ]
        for fieldset_id, legend, fields in sources:
            result.append(self.makeFieldSet(fieldset_id, legend, fields, 2))
        return result

    def getDemoFields(self):
        fields = field.Fields()
        dfs = IDemographicsFields(ISchoolToolApplication(None))
        keys = self.group_id and [self.group_id] or []
        for field_desc in dfs.filter_keys(keys):
            fields += field_desc.makeField()
        return fields

    def getBaseFields(self):
        return field.Fields(IPersonAddForm).omit('group')

    def updateActions(self):
        super(PersonAddViewBase, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'))
    def handleAdd(self, action):
        super(PersonAddViewBase, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        person = self._factory(username, first_name, last_name)
        data.pop('confirm')
        form.applyChanges(self, person, data)

        self._groups = []
        group = None
        syc = ISchoolYearContainer(ISchoolToolApplication(None))
        active_schoolyear = syc.getActiveSchoolYear()
        if active_schoolyear is not None:
            if self.group_id:
                group = IGroupContainer(active_schoolyear).get(self.group_id)
            else:
                group = data.get('group')
        if group is not None:
            self._groups.append(group)

        self._advisors = []
        advisor = data.get('advisor')
        if advisor is not None:
            self._advisors.append(advisor)

        self._person = person
        return person

    def update(self):
        self.fields = self.getBaseFields()
        self.fields += self.getDemoFields()
        self.updateWidgets()
        self.updateActions()
        self.actions.execute()

    def updateWidgets(self):
        super(PersonAddViewBase, self).updateWidgets()


class FlourishPersonAddView(PersonAddViewBase):
    template = InheritTemplate(flourish.page.Page.template)
    page_template = InheritTemplate(flourish.page.Page.page_template)

    fieldset_groups = None
    fieldset_order = None

    group_id = None

    def update(self):
        self.buildFieldsetGroups()
        PersonAddViewBase.update(self)
        self.widgets['birth_date'].addClass('birth-date-field')

    def getBaseFields(self):
        result = field.Fields(IPersonAddForm)
        if self.group_id:
            result = result.omit('group')
        result += field.Fields(IPhotoField)
        result += field.Fields(ILevelField)
        return result

    def buildFieldsetGroups(self):
        relationship_fields = ['advisor']
        if not self.group_id:
            relationship_fields[0:0] = ['group']
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix', 'preferred_name']),
            'user': (
                _('User'), ['username', 'password', 'confirm']),
            'details': (
                _('Details'), ['gender', 'birth_date', 'photo']),
            'level': (
                _('Level'), ['level']),
            'demographics': (
                _('Demographics'), list(self.getDemoFields())),
            'relationships': (
                _('Relationships'), relationship_fields),
            }
        self.fieldset_order = (
            'full_name', 'details', 'demographics', 'level',
            'relationships', 'user')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleSubmit(self, action):
        super(FlourishPersonAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Submit and add'), name='submitadd')
    def handleSubmitAndAdd(self, action):
        super(FlourishPersonAddView, self).handleAdd.func(self, action)
        if self._finishedAdd:
            self.request.response.redirect(self.action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(FlourishPersonAddView, self).updateActions()
        self.actions['submitadd'].addClass('button-neutral')

    def create(self, data):
        self._level = data.pop('level')
        return super(FlourishPersonAddView, self).create(data)

    def add(self, person):
        person = super(FlourishPersonAddView, self).add(person)
        if self._level is not None:
            self.set_person_level(person, self._level)
        return person

    def set_person_level(self, person, level):
        person.levels.on(self.request.util.today).relate(level)


###############  Group-aware add views ################
class TeacherAddView(PersonAddViewBase):

    group_id = 'teachers'
    base_id = 'base-data'
    base_legend = _('Teacher identification')
    demo_id = 'demo-data'
    demo_legend = _('Teacher demographics')
    label = _('Add new teacher')


class StudentAddView(PersonAddViewBase):

    group_id = 'students'
    base_id = 'base-data'
    base_legend = _('Student identification')
    demo_id = 'demo-data'
    demo_legend = _('Student demographics')
    label = _('Add new student')


class AdministratorAddView(PersonAddViewBase):

    group_id = 'administrators'
    base_id = 'base-data'
    base_legend = _('Administrator identification')
    demo_id = 'demo-data'
    demo_legend = _('Administrator demographics')
    label = _('Add new administrator')


class AddPersonViewlet(object):

    def hasSchoolYear(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        sy = syc.getActiveSchoolYear()
        return sy is not None


class PersonTitle(ContentProvider):
    render = InlineViewPageTemplate('''
        <span tal:replace="view/title"></span>
    '''.strip())

    def title(self):
        person = self.context
        return person.title


class BasicPersonTable(PersonTable):

    def __init__(self, *args, **kw):
        PersonTable.__init__(self, *args, **kw)
        self.css_classes = {'table': ' data persons-table'}

    def columns(self):
        cols = getUtility(IPersonFactory).columns()
        username = IndexedLocaleAwareGetterColumn(
            index='__name__',
            name='username',
            title=_(u'Username'),
            getter=lambda i, f: i.__name__,
            subsort=True)
        return cols + [username]


class PersonListTable(BasicPersonTable):

    @property
    def source(self):
        return ISchoolToolApplication(None)['persons']

    def items(self):
        return self.indexItems(self.context)


class BasicPersonAddRelationshipTable(RelationshipAddTableMixin,
                                      BasicPersonTable):
    pass


class BasicPersonRemoveRelationshipTable(RelationshipRemoveTableMixin,
                                         BasicPersonTable):
    pass


class BasicPersonAddTemporalRelationshipTable(TemporalRelationshipAddTableMixin,
                                      BasicPersonTable):
    pass


class BasicPersonRemoveTemporalRelationshipTable(TemporalRelationshipRemoveTableMixin,
                                         BasicPersonTable):
    pass


class BasicPersonTableFormatter(PersonTableFormatter):

    def columns(self):
        cols = list(reversed(PersonTableFormatter.columns(self)))
        username = IndexedLocaleAwareGetterColumn(
            index='__name__',
            name='username',
            title=_(u'Username'),
            getter=lambda i, f: i.__name__,
            subsort=True)
        return cols + [username]

    def makeFormatter(self):
        formatter = PersonTableFormatter.makeFormatter(self)
        formatter.cssClasses['table'] = 'data persons-table'
        return formatter


class FlourishManagePeopleOverview(flourish.page.Content,
                                   ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_people_overview.pt')

    built_in_groups = ('administrators', 'clerks', 'manager', 'teachers',
                       'students')

    @property
    def groups(self):
        return IGroupContainer(self.schoolyear, None)

    @property
    def persons(self):
        return self.context['persons']

    @property
    def school_name(self):
        preferences = IApplicationPreferences(self.context)
        return preferences.title

    def persons_url(self):
        return self.url_with_schoolyear_id(self.context, view_name='persons')

    def group_members(self, group):
        return len(group.members.all().any(ACTIVE))


class FlourishRequestPersonIDCardView(RequestRemoteReportDialog):

    report_task = OldReportTask
    report_builder = 'person_id_card.pdf'


class IDCardsPageTemplate(DefaultPageTemplate):

    template = ViewPageTemplateFile('templates/f_id_cards_template.pt',
                                    content_type="text/xml")


class FlourishPersonIDCardsViewBase(ReportPDFView):

    template=ViewPageTemplateFile('templates/f_person_id_cards.pt')
    title = _('ID Cards')
    COLUMNS = 2
    ROWS = 4
    # All of the following are cm
    CARD = {
        'height': 5.4,
        'width': 8.57,
        }
    TITLE = {
        'height': 1.1,
        'padding': 0.06, # from the edge of the title frame
        }
    DEMOGRAPHICS = {
        'height': 3.2,
        'margin-left': 0.55, # from the edge of the card
        'margin-bottom': 0.75, # from the edge of the card
        'width': 5.05,
        }
    PHOTO = {
        'height': 3.2,
        'width': 2.4,
        }
    FOOTER = {
        'height': 0.5,
        }
    LEFT_BASE = 1.7
    TOP_BASE = 7.3
    COLUMN_WIDTH = 9.6
    ROW_HEIGHT = 6.1

    def __init__(self, *args, **kw):
        super(FlourishPersonIDCardsViewBase, self).__init__(*args, **kw)
        app = ISchoolToolApplication(None)
        preferences = IApplicationPreferences(app)
        self.schoolName = preferences.title

    @property
    def top(self):
        page_height = self.pageSize[1]
        return (page_height/units.cm) - self.TOP_BASE

    @property
    def left(self):
        return self.LEFT_BASE

    def persons(self):
        """Returns a list of getPersonData calls"""
        raise NotImplementedError('do this in subclass')

    def getPersonData(self, person):
        demographics = IDemographics(person)
        contact_title = None
        contact_phone = None
        contacts = list(IContactable(person).contacts)
        if contacts:
            contact = contacts[0]
            contact_title = contact.title
            phones = [
                contact.home_phone,
                contact.work_phone,
                contact.mobile_phone,
                ]
            if phones:
                contact_phone = phones[0]
        return {
            'title': person.title,
            'username': person.username,
            'ID': demographics.get('ID'),
            'birth_date': person.birth_date,
            'contact_title': contact_title,
            'contact_phone': contact_phone,
            'photo': person.photo,
            }

    def titleVerticalAlign(self, person):
        result = 0
        if len(person['title']) < 44:
            result = 0.25
        return '%fcm' % result

    @Lazy
    def total_cards_in_page(self):
        return self.COLUMNS * self.ROWS

    def insertBreak(self, repeat):
        return repeat['person'].number() % self.total_cards_in_page  == 0

    def personFrame(self, repeat):
        return repeat['person'].index() % self.total_cards_in_page

    def cards(self):
        result = []
        for card_index in range(self.total_cards_in_page):
            card_column = card_index % self.COLUMNS
            card_row = card_index / self.COLUMNS
            card_x1 = self.left + (self.COLUMN_WIDTH * card_column)
            card_y1 = self.top - (self.ROW_HEIGHT * card_row)
            card_info = {
                'index': card_index,
                'x1': card_x1,
                'y1': card_y1,
                'height': self.CARD['height'],
                'width': self.CARD['width'],
                }
            result.append(card_info)
        return result

    @Lazy
    def cardFrames(self):
        result = {}
        for card_info in self.cards():
            info = {
                'outter': self.getOutterFrame(card_info),
                'title': self.getTitleFrame(card_info),
                'demographics': self.getDemographicsFrame(card_info),
                'footer': self.getFooterFrame(card_info),
                }
            result[card_info['index']] = info
        return result

    def getOutterFrame(self, card_info):
        frame_info = card_info.copy()
        frame_info['id'] = 'outter_%d' % card_info['index']
        frame_info['maxWidth'] = card_info['width']
        frame_info['maxHeight'] = card_info['height']
        return frame_info

    def getTitleFrame(self, card_info):
        y1 = card_info['y1'] + (card_info['height'] - self.TITLE['height'])
        return {
            'id': 'title_%d' % card_info['index'],
            'x1': card_info['x1'],
            'y1': y1,
            'width': card_info['width'],
            'maxWidth': card_info['width'] - self.TITLE['padding'],
            'height': self.TITLE['height'],
            'maxHeight': self.TITLE['height'] - self.TITLE['padding'],
            }

    def getDemographicsFrame(self, card_info):
        demo_info = self.DEMOGRAPHICS
        x1 = card_info['x1'] + demo_info['margin-left']
        y1 = card_info['y1'] +  demo_info['margin-bottom']
        return {
            'id': 'demographics_%d' % card_info['index'],
            'x1': x1,
            'y1': y1,
            'width': demo_info['width'],
            'maxWidth': demo_info['width'],
            'height': demo_info['height'],
            'maxHeight': demo_info['height'],
            }

    def getFooterFrame(self, card_info):
        x1 = card_info['x1']
        y1 = card_info['y1']
        return {
            'id': 'footer_%d' % card_info['index'],
            'x1': x1,
            'y1': y1,
            'width': card_info['width'],
            'maxWidth': card_info['width'],
            'height': self.FOOTER['height'],
            'maxHeight': self.FOOTER['height'],
            }


class FlourishPersonIDCardView(FlourishPersonIDCardsViewBase):

    @property
    def filename(self):
        return 'id_cards_%s_%s.pdf' % (
            self.context.last_name,  self.context.first_name)

    @property
    def title(self):
        return _('ID Card: ${person}',
                 mapping={'person': self.context.title})

    def persons(self):
        return [self.getPersonData(self.context)] * self.total_cards_in_page


def getUserViewlet(context, request, view, manager, name):
    principal = request.principal
    user = IPerson(principal, None)
    if user is None:
        return None
    viewlet = flourish.viewlet.lookupViewlet(
        user, request, view, manager, name=name)
    return viewlet


def getPersonActiveViewlet(person, request, view, manager):
    user = IPerson(request.principal, None)
    if (user is not None and
        user.__name__ == person.__name__):
        return u"home"
    return flourish.page.getParentActiveViewletName(
        person, request, view, manager)


class PhotoView(flourish.widgets.ImageView):
    attribute = "photo"


class PersonContainerViewTableFilter(PersonTableFilter, ActiveSchoolYearContentMixin):

    template = ViewPageTemplateFile('templates/f_container_table_filter.pt')

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, 'manage')


class PersonProfilePDF(flourish.report.PlainPDFPage):

    name = _("Profile")
    message_title = _('profile report')

    def formatDate(self, date, format='mediumDate'):
        if date is None:
            return ''
        formatter = getMultiAdapter((date, self.request), name=format)
        return formatter()

    @property
    def scope(self):
        dtm = getUtility(IDateManager)
        today = dtm.today
        return self.formatDate(today)

    @property
    def subtitles_left(self):
        student_id = _('Username: ${username}',
                       mapping={'username': self.context.username})
        subtitles = [
            student_id,
            ]
        return subtitles

    @property
    def title(self):
        return self.context.title

    @property
    def base_filename(self):
        return '%s_%s_%s' % (
            self.context.last_name,  self.context.first_name, self.context.username)


class ProfileGeneralPart(flourish.report.PDFForm):

    title = _("General Information")

    def getFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        for field_desc in field_descriptions.values():
            fields += field_desc.makeField()
        return fields

    def update(self):
        self.fields = field.Fields(IBasicPerson)
        self.fields += field.Fields(IPhotoField)
        self.fields += field.Fields(IPerson).select('username')
        self.fields += self.getFields()
        super(ProfileGeneralPart, self).update()


class UserLinkViewlet(flourish.page.LinkViewlet):

    @property
    def url(self):
        user = IPerson(self.request.principal, None)
        link = self.link
        if not link or user is None:
            return None
        return "%s/%s" % (absoluteURL(user, self.request), self.link)


class PersonMessageFilter(table.table.DoNotFilter):

    @property
    def catalog(self):
        return self.manager.catalog

    @property
    def person(self):
        return IPerson(self.context)

    @property
    def active_person_intid(self):
        person = self.person
        int_ids = getUtility(IIntIds)
        person_intid = int_ids.queryId(person, None)
        return person_intid

    def filter(self, results):
        person_intid = self.active_person_intid
        if person_intid is None:
            return []
        recipient_index = self.catalog['recipient_ids']
        message_ids = recipient_index.apply({'any_of': set([person_intid])})
        results = [item for item in results
                   if item['id'] in message_ids]
        return results


class MessageTable(table.ajax.IndexedTable):

    @property
    def source(self):
        return IMessageContainer(ISchoolToolApplication(None))

    def columns(self):
        group = table.column.IndexedGetterColumn(
            name='group',
            title=_(u"Group"),
            getter=lambda i, f: i.group,
            cell_formatter=table.table.translate_cell_formatter,
            index='group',
            subsort=True)
        directlyProvides(group, ISortableColumn)
        updated = table.column.IndexedGetterColumn(
            name='updated_on',
            title=_("Received"),
            getter=lambda i, f: i.updated_on,
            cell_formatter=table.table.datetime_formatter,
            index='updated_on',
            subsort=True)
        directlyProvides(updated, ISortableColumn)
        message = MessageColumn(
            name='message',
            title=_("Message"))
        return [message, group, updated]

    def sortOn(self):
        return (('updated_on', True), )


class FlourishRequestPersonProfileView(RequestRemoteReportDialog):

    report_builder = 'person_profile.pdf'


class NewMessageIndicatorViewlet(flourish.page.LinkViewlet):

    css_class = 'new-messages'

    @property
    def authenticated_person(self):
        principal = getattr(self.request, 'principal', None)
        if principal is None:
            return None
        if IUnauthenticatedPrincipal.providedBy(principal):
            return None
        return IPerson(principal, None)

    @property
    def authenticated_person_intid(self):
        person = self.authenticated_person
        if person is None:
            return None
        int_ids = getUtility(IIntIds)
        person_intid = int_ids.queryId(person, None)
        return person_intid

    @property
    def new_messages(self):
        person = self.authenticated_person
        if person is None:
            return None
        person_intid = self.authenticated_person_intid
        if person_intid is None:
            return None
        dt = getLastMessagesReadTime(person)
        catalog = MessageCatalog.get()
        new_ids = catalog['updated_on'].apply(
            {'between': (dt, None)})
        my_ids = catalog['recipient_ids'].apply(
            {'any_of': set([person_intid])})
        new_messages = len(set(my_ids).intersection(new_ids))
        return new_messages

    @property
    def title(self):
        person = self.authenticated_person
        if person is None:
            return ''
        new_messages = self.new_messages
        if not new_messages:
            return ''
        title = _('(${number} new)',
                  mapping={'number': new_messages})
        return title

    @property
    def url(self):
        person = self.authenticated_person
        if person is None:
            return None
        url = absoluteURL(person, self.request) + '#messages'
        return url


class FlourishLeaderView(EditPersonTemporalRelationships):

    app_states_name = 'asset-leaders'
    current_title = _("Current responsible parties")
    available_title = _("Available responsible parties")

    def getCollection(self):
        return self.context.leaders

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']


class StatusPersonListTable(PersonListTable):

    app_states_name = None

    def columns(self):
        default = super(StatusPersonListTable, self).columns()
        status = zc.table.column.GetterColumn(
            name='status',
            title=_('Status'),
            getter=self.makeStatusGetter())
        return default + [status]

    def getCollection(self):
        return self.context.all()

    def items(self):
        return self.indexItems(self.getCollection())

    def makeStatusGetter(self):
        if self.app_states is None:
            return None
        collection = self.getCollection()
        def getter(item, formatter):
            state = collection.state(removeSecurityProxy(item))
            if state is None:
                return ''
            state_today = state.today
            if state_today is None:
                return ''
            active, code = state_today
            description = self.app_states.states.get(code)
            if description is None:
                return ''
            return description.title
        return getter

    @Lazy
    def app_states(self):
        if self.app_states_name is None:
            return None
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        return container.get(self.app_states_name, None)


class LeaveSchoolView(flourish.form.Form,
                      form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Un-enroll Information')

    @property
    def fields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        for name in LEAVE_SCHOOL_FIELDS:
            if name in field_descriptions:
                fields += field_descriptions[name].makeField()
        return fields

    @property
    def title(self):
        return self.context.title

    def update(self):
        form.EditForm.update(self)

    def updateActions(self):
        super(LeaveSchoolView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self, *args, **kw):
        super(LeaveSchoolView, self).updateWidgets(*args, **kw)
        self.widgets['leave_date'].value = self.request.util.today

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(LeaveSchoolView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            data, errors = self.extractData()
            person = removeSecurityProxy(self.context)
            leave_date = data['leave_date']
            relationships = Membership.bind(member=person).all().relationships
            for link_info in relationships:
                target = removeSecurityProxy(link_info.target)
                if ISection.providedBy(target):
                    term = ITerm(target)
                    if leave_date in term or leave_date < term.first:
                        collection = removeSecurityProxy(target.members)
                        if leave_date < term.first:
                            link_info.state.replace({})
                        collection.on(leave_date).relate(person, INACTIVE, 'i')
                else:
                    schoolyear = ISchoolYear(target.__parent__)
                    if ((schoolyear.first <= leave_date <= schoolyear.last) or
                        leave_date < schoolyear.first):
                        collection = removeSecurityProxy(target.members)
                        code = 'w' if target.__name__ == 'students' else 'r'
                        if leave_date < schoolyear.first:
                            link_info.state.replace({})
                        collection.on(leave_date).relate(person, INACTIVE, code)
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class LeaveSchoolLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return is_student(self.context)


class LevelAccordionViewlet(Viewlet):

    template = ViewPageTemplateFile('templates/f_levelViewlet.pt')

    @property
    def title(self):
        result = _('Grade Level')
        today = self.request.util.today
        levels = [level.title
                  for level in self.context.levels.on(today).any(ACTIVE)]
        if levels:
            result = _('Grade Level: ${level}',
                       mapping={'level': ', '.join(levels)})
        return result

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    def render(self, *args, **kw):
        if is_student(self.context):
            return self.template(*args, **kw)
        return ''


class PersonEditLevelView(flourish.form.Form,
                          form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Level Information')

    @property
    def fields(self):
        result = field.Fields(Date(__name__='date', title=_('Date')))
        result += field.Fields(ILevelField)
        return result

    @property
    def current_level(self):
        today = self.request.util.today
        levels = [level
                  for level in self.context.levels.on(today).any(ACTIVE)]
        if levels:
            return levels[0]

    def getContent(self):
        return {
            'date': self.request.util.today,
            'level': self.current_level,
        }

    @property
    def title(self):
        return self.context.title

    def update(self):
        form.EditForm.update(self)

    def updateActions(self):
        super(PersonEditLevelView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self, *args, **kw):
        super(PersonEditLevelView, self).updateWidgets(*args, **kw)
        self.widgets['level'].prompt = True
        self.widgets['level'].promptMessage = _('No Level')

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(PersonEditLevelView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            data, errors = self.extractData()
            person = removeSecurityProxy(self.context)
            date = data['date']
            current_level = removeSecurityProxy(self.current_level)
            new_level = removeSecurityProxy(data['level'])
            if current_level != new_level:
                if current_level is not None:
                    person.levels.on(date).relate(current_level, INACTIVE, 'i')
                if new_level is not None:
                    person.levels.on(date).relate(new_level)
        self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request)
