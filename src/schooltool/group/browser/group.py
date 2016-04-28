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
group views.
"""
from urllib import urlencode

from reportlab.lib import units, pagesizes

import zc.table.table
import zc.table.column
from zope.app.dependable.interfaces import IDependable
from zope.cachedescriptors.property import Lazy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import Attribute
from zope.interface import Interface
from zope.intid.interfaces import IIntIds
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.interface import implements, directlyProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.component import adapts
from zope.component import getAdapter
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component import getAdapters
from zope.security.checker import canAccess
from zope.i18n.interfaces.locales import ICollator
from zope.viewlet.viewlet import ViewletBase
from zope.container.interfaces import INameChooser
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.proxy import sameProxiedObjects
from zope.i18n import translate
from z3c.form import field, button, form
from z3c.form.interfaces import HIDDEN_MODE
from zc.table.interfaces import ISortableColumn
from zope.security.interfaces import Unauthorized
from zope.schema import Choice, Int
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary

from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.skin.containers import TableContainerView
from schooltool.app.browser.app import BaseAddView, BaseEditView
from schooltool.app.browser.app import ContentTitle
from schooltool.app.browser.states import EditTemporalRelationships
from schooltool.app.browser.states import TemporalRelationshipAddTableMixin
from schooltool.app.browser.states import TemporalRelationshipRemoveTableMixin
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.membership import Membership
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonFactory
from schooltool.person.browser.person import PersonTableFilter
from schooltool.basicperson.browser.person import StatusPersonListTable
from schooltool.basicperson.browser.person import EditPersonTemporalRelationships
from schooltool.basicperson.browser.person import BasicPersonTable
from schooltool.basicperson.demographics import LEAVE_SCHOOL_FIELDS
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.contact.interfaces import IAddress
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactable
from schooltool.course.interfaces import ISection
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroup
from schooltool.group.interfaces import IGroupMember
from schooltool.group.interfaces import IGroupContainer, IGroupContained
from schooltool.skin.flourish.viewlet import Viewlet
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool import table
from schooltool.app.utils import vocabulary
from schooltool.term.interfaces import IDateManager
from schooltool.relationship.temporal import ACTIVE

from schooltool.common import SchoolToolMessage as _
from schooltool.basicperson.browser.person import FlourishPersonIDCardsViewBase
from schooltool.report.report import OldReportTask
from schooltool.report.browser.report import RequestRemoteReportDialog


class GroupContainerAbsoluteURLAdapter(BrowserView):

    adapts(IGroupContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/groups'

    __call__ = __str__


class GroupContainerView(TableContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")


class GroupListView(RelationshipViewBase):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    @property
    def title(self):
        return _("Groups of ${person}", mapping={'person': self.context.title})
    current_title = _("Current Groups")
    available_title = _("Available Groups")

    def getSelectedItems(self):
        """Return a list of groups the current user is a member of."""
        return [group for group in self.context.groups
                if not ISection.providedBy(group)]

    def getAvailableItemsContainer(self):
        app = ISchoolToolApplication(None)
        groups = IGroupContainer(app, {})
        return groups

    def getCollection(self):
        return self.context.groups


class GroupView(BrowserView):
    """A Group info view."""

    __used_for__ = IGroupContained

    def renderPersonTable(self):
        persons = ISchoolToolApplication(None)['persons']
        formatter = getMultiAdapter((persons, self.request),
                                    table.interfaces.ITableFormatter)
        formatter.setUp(table_formatter=zc.table.table.StandaloneFullFormatter,
                        items=self.getPersons(),
                        batch_size=0)
        return formatter.render()

    def getPersons(self):
        return [member for member in self.context.members
                if canAccess(member, 'title')]

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class MemberViewPersons(RelationshipViewBase):
    """View class for adding / removing members to / from a group."""

    __used_for__ = IGroupContained

    @property
    def title(self):
        return _("Members of ${group}", mapping={'group': self.context.title})
    current_title = _("Current Members")
    available_title = _("Add Members")

    def getSelectedItems(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.members


class GroupAddView(BaseAddView):
    """A view for adding a group."""


class GroupEditView(BaseEditView):
    """A view for editing group info."""

    __used_for__ = IGroupContained


class GroupsViewlet(ViewletBase):
    """A viewlet showing the groups a person is in."""

    def update(self):
        self.collator = ICollator(self.request.locale)
        groups = [
            group for group in self.context.groups
            if (canAccess(group, 'title') and
                not ISection.providedBy(group))]

        schoolyears_data = {}
        for group in groups:
            sy = ISchoolYear(group.__parent__)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = []
            schoolyears_data[sy].append(group)

        self.schoolyears = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy,
                       'groups': sorted(schoolyears_data[sy],
                                        cmp=self.collator.cmp,
                                        key=lambda x:x.title)}
            self.schoolyears.append(sy_info)

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishGroupsViewlet(Viewlet, ActiveSchoolYearContentMixin):
    """A flourish viewlet showing the groups a person is in."""

    template = ViewPageTemplateFile('templates/f_groupsviewlet.pt')
    render = lambda self, *a, **kw: self.template(*a, **kw)

    def app_states(self, key):
        app = ISchoolToolApplication(None)
        states = IRelationshipStateContainer(app)[key]
        return states

    def group_current_states(self, link_info, app_states):
        states = []
        for date, active, code in link_info.state.all():
            state = app_states.states.get(code)
            title = state.title if state is not None else ''
            states.append({
                'date': date,
                'title': title,
                })
        return states

    def update(self):
        self.collator = ICollator(self.request.locale)
        relationships = Membership.bind(member=self.context).all().relationships
        group_states = self.app_states('group-membership')
        student_states = self.app_states('student-enrollment')
        schoolyears_data = {}
        for link_info in relationships:
            group = removeSecurityProxy(link_info.target)
            if ISection.providedBy(group) or not canAccess(group, 'title'):
                continue
            sy = ISchoolYear(group.__parent__)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = []
            schoolyears_data[sy].append((group, link_info))
        self.schoolyears = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {
                'obj': sy,
                'css_class': 'active' if sy is self.schoolyear else 'inactive',
                'groups': [],
                }
            for group, link_info in sorted(schoolyears_data[sy],
                                           key=lambda x:self.collator.key(
                                               x[0].title)):
                is_students = group.__name__ == 'students'
                app_states = student_states if is_students else group_states
                states = self.group_current_states(link_info, app_states)
                group_info = {
                    'obj': group,
                    'title': group.title,
                    'states': states,
                    }
                sy_info['groups'].append(group_info)
            self.schoolyears.append(sy_info)

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishGroupFilterWidget(table.table.FilterWidget):

    template = ViewPageTemplateFile('templates/f_group_filter.pt')


class SchoolYearColumn(zc.table.column.GetterColumn):

    def getter(self, item, formatter):
        schoolyear = ISchoolYear(item.__parent__)
        return schoolyear.title

    def getSortKey(self, item, formatter):
        schoolyear = ISchoolYear(item.__parent__)
        return schoolyear.first


class FlourishGroupTableFormatter(table.table.SchoolToolTableFormatter):

    def columns(self):
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def makeFormatter(self):
        formatter = table.table.SchoolToolTableFormatter.makeFormatter(self)
        formatter.cssClasses['table'] = 'groups-table relationships-table'
        return formatter


class FlourishGroupListView(EditTemporalRelationships):

    app_states_name = "group-membership"
    dialog_title_template = _("Assign to ${target}")

    current_title = _('Current groups')
    available_title = _('Available groups')

    @Lazy
    def schoolyears(self):
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
        active_schoolyear = schoolyears.getActiveSchoolYear()
        return [schoolyear for schoolyear in schoolyears.values()
                if schoolyear.first >= active_schoolyear.first]

    def getSelectedItems(self):
        groups = EditTemporalRelationships.getSelectedItems(self)
        return [group for group in groups
                if not ISection.providedBy(group) and
                ISchoolYear(group.__parent__) in self.schoolyears]

    def getAvailableItemsContainer(self):
        app = ISchoolToolApplication(None)
        groups = IGroupContainer(app, {})
        return groups

    def getAvailableItems(self):
        result = []
        selected_items = set(self.getSelectedItems())
        for schoolyear in self.schoolyears:
            groups = IGroupContainer(schoolyear)
            result.extend([group for group in groups.values()
                           if group not in selected_items])
        return result

    def getCollection(self):
        return self.context.groups

    def getColumnsAfter(self, prefix):
        columns = super(FlourishGroupListView, self).getColumnsAfter(prefix)
        schoolyear = SchoolYearColumn(
            name='schoolyear',
            title=_(u'School Year'),
            subsort=True)
        directlyProvides(schoolyear, ISortableColumn)
        return [schoolyear] + columns

    def sortOn(self):
        return (('schoolyear', True), ("title", False))

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            items=self.getAvailableItems(),
            sort_on=self.sortOn(),
            prefix="add_item")
        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            sort_on=self.sortOn(),
            prefix="remove_item",
            batch_size=0)

    def getKey(self, item):
        schoolyear = ISchoolYear(item.__parent__)
        return "%s.%s" % (schoolyear.__name__, item.__name__)

    def getTargets(self, keys):
        if not keys:
            return []
        result = []
        sy_groups = {}
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
        for key in keys:
            for sy_name, schoolyear in schoolyears.items():
                if not key.startswith(sy_name+'.'):
                    continue
                if sy_name not in sy_groups:
                    sy_groups[sy_name] = IGroupContainer(schoolyear)
                group = sy_groups[sy_name].get(key[len(sy_name)+1:])
                if group is not None:
                    result.append(group)
        return result


class GroupsTertiaryNavigationManager(flourish.page.TertiaryNavigationManager,
                                      ActiveSchoolYearContentMixin):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        active = self.schoolyear
        schoolyears = active.__parent__ if active is not None else {}
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'groups',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class GroupsAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in GroupsView"""


class GroupImportLinks(flourish.page.RefineLinksViewlet):
    """Manager for group import links."""


class GroupLinks(flourish.page.RefineLinksViewlet):
    """Manager for public links in GroupView"""

    @property
    def title(self):
        return self.context.title


class GroupAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in GroupView"""

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context group, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            return super(GroupAddLinks, self).render()


class GroupManageActionsLinks(flourish.page.RefineLinksViewlet):
    """Manager for Action links in GroupView"""

    body_template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/renderable_items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    # We don't want this manager rendered at all
    # if there are no renderable viewlets
    @property
    def renderable_items(self):
        result = []
        for item in self.items:
            render_result = item['viewlet']()
            if render_result and render_result.strip():
                result.append({
                        'class': item['class'],
                        'viewlet': render_result,
                        })
        return result

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context group, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            if self.renderable_items:
                return super(GroupManageActionsLinks, self).render()


class GroupDeleteLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Delete ${group}',
                  mapping={'group': self.context.title})
        return translate(title, context=self.request)

    def render(self, *args, **kw):
        unwrapped = removeSecurityProxy(self.context)
        dependable = IDependable(unwrapped, None)
        if dependable is None or not bool(dependable.dependents()):
            return super(GroupDeleteLink, self).render(*args, **kw)


class GroupAddLinkViewlet(flourish.page.LinkViewlet,
                          ActiveSchoolYearContentMixin):

    @property
    def url(self):
        groups = IGroupContainer(self.schoolyear)
        return '%s/%s' % (absoluteURL(groups, self.request),
                          'addSchoolToolGroup.html')

class GroupAddLinkFromGroupViewlet(GroupAddLinkViewlet):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context.__parent__)

    @property
    def url(self):
        groups = IGroupContainer(self.schoolyear)
        return '%s/%s?camefrom=%s' % (
            absoluteURL(groups, self.request),
            'addSchoolToolGroup.html',
            absoluteURL(self.context, self.request))


class GroupContainerTitle(ContentTitle):

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class FlourishGroupsView(flourish.page.Page,
                         ActiveSchoolYearContentMixin):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
    ''')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @Lazy
    def container(self):
        schoolyear = self.schoolyear
        return IGroupContainer(schoolyear)

    def __call__(self, *args, **kw):
        if not flourish.canView(self.container):
            raise Unauthorized("No permission to view groups.")
        return flourish.page.Page.__call__(self, *args, **kw)


class GroupsTable(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        description = zc.table.column.GetterColumn(
            name='description',
            title=_('Description'),
            getter=lambda i, f: i.description or '',
            )
        return default + [description]


class GroupsTableFilter(table.ajax.TableFilter):

    title = _("Group title")


class GroupsTableSchoolYear(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <input type="hidden" name="schoolyear_id"
             tal:define="schoolyear_id view/view/schoolyear/__name__|nothing"
             tal:condition="schoolyear_id"
             tal:attributes="value schoolyear_id" />
    ''')


class GroupsWithSYTable(GroupsTable):

    def columns(self):
        default = table.ajax.Table.columns(self)
        schoolyear = SchoolYearColumn(
            name='schoolyear',
            title=_(u'School Year'),
            subsort=True)
        directlyProvides(schoolyear, ISortableColumn)
        return default + [schoolyear]

    def sortOn(self):
        return (('schoolyear', True), ("title", False))


class GroupListAddRelationshipTable(TemporalRelationshipAddTableMixin,
                                    GroupsWithSYTable):

    def updateFormatter(self):
        ommit = self.view.getOmmitedItems()
        available = self.view.getAvailableItems()
        columns = self.columns()
        self.setUp(formatters=[table.table.url_cell_formatter],
                   columns=columns,
                   ommit=ommit,
                   items=available,
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data relationships-table'})


class GroupListRemoveRelationshipTable(TemporalRelationshipRemoveTableMixin,
                                       GroupsWithSYTable):
    pass


class FlourishGroupContainerDeleteView(flourish.containers.ContainerDeleteView):

    def nextURL(self):
        if 'CONFIRM' in self.request:
            schoolyear = ISchoolYear(self.context)
            params = {'schoolyear_id': schoolyear.__name__.encode('utf-8')}
            url = '%s/groups?%s' % (
                absoluteURL(ISchoolToolApplication(None), self.request),
                urlencode(params))
            return url
        return flourish.containers.ContainerDeleteView.nextURL(self)


class FlourishGroupView(flourish.form.DisplayForm, ActiveSchoolYearContentMixin):

    template = InheritTemplate(flourish.page.Page.template)
    content_template = ViewPageTemplateFile('templates/f_group_view.pt')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    @property
    def canModify(self):
        return checkPermission('schooltool.edit', self.context)

    @property
    def schoolyear(self):
        return ISchoolYear(self.context.__parent__)

    @property
    def title(self):
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': self.schoolyear.title})

    @property
    def subtitle(self):
        return self.context.title

    def done_link(self):
        url = self.request.get('done_link', None)
        if url is not None:
            return url
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='groups')

    def updateWidgets(self):
        super(FlourishGroupView, self).updateWidgets()
        for widget in self.widgets.values():
            if not widget.value:
                widget.mode = HIDDEN_MODE

    def has_members(self):
        return bool(self.context.members)

    def has_leaders(self):
        return bool(self.context.leaders)


class FlourishGroupAddView(flourish.form.AddForm, ActiveSchoolYearContentMixin):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Group Information')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    def updateActions(self):
        super(FlourishGroupAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishGroupAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        app = ISchoolToolApplication(None)
        url = self.url_with_schoolyear_id(app, view_name='groups')
        self.request.response.redirect(url)

    def create(self, data):
        group = Group(data['title'], data.get('description'))
        form.applyChanges(self, group, data)
        return group

    def add(self, group):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', group)
        self.context[name] = group
        self._group = group
        return group

    def nextURL(self):
        return absoluteURL(self._group, self.request)

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    @property
    def title(self):
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': self.schoolyear.title})


class FlourishGroupEditView(flourish.form.Form, form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Group Information')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    @property
    def title(self):
        return self.context.title

    def update(self):
        return form.EditForm.update(self)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishGroupEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(FlourishGroupEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishGroupDeleteView(flourish.form.DialogForm, form.EditForm):
    """View used for confirming deletion of a group."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.__name__.encode('utf-8'))
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishGroupDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class GroupMembersTable(BasicPersonTable):

    prefix = "members"

    def items(self):
        return self.makeItems(self.context.members.int_ids)


class GroupLeadersTable(BasicPersonTable):

    prefix = "leaders"

    def items(self):
        return self.makeItems(self.context.leaders.int_ids)


class FlourishMemberViewPersons(EditPersonTemporalRelationships):
    """View class for adding / removing members to / from a group."""

    @property
    def app_states_name(self):
        if self.context.__name__ == 'students':
            return 'student-enrollment'
        return 'group-membership'

    @property
    def title(self):
        return self.context.title

    current_title = _("Current Members")
    available_title = _("Add Members")

    def getSelectedItems(self):
        members = EditPersonTemporalRelationships.getSelectedItems(self)
        return filter(IPerson.providedBy, members)

    def getCollection(self):
        return self.context.members


class FlourishManageGroupsOverview(flourish.page.Content,
                                   ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_groups_overview.pt')

    @property
    def groups(self):
        return IGroupContainer(self.schoolyear, None)

    def groups_url(self):
        return self.url_with_schoolyear_id(self.context, view_name='groups')


class FlourishRequestGroupIDCardsView(RequestRemoteReportDialog):

    report_builder = 'group_id_cards.pdf'
    report_task = OldReportTask


class FlourishGroupIDCardsView(FlourishPersonIDCardsViewBase):

    @property
    def title(self):
        return _('ID Cards for Group: ${group}',
                 mapping={'group': self.context.title})

    @property
    def filename(self):
        sy = ISchoolYear(self.context.__parent__)
        return 'id_cards_%s_%s.pdf' % (
            self.context.title,  sy.title)

    def persons(self):
        collator = ICollator(self.request.locale)
        factory = getUtility(IPersonFactory)
        sorting_key = lambda x: factory.getSortingKey(x, collator)
        sorted_persons = sorted(self.context.members, key=sorting_key)
        result = [self.getPersonData(person)
                  for person in sorted_persons]
        return result


def done_link_url_cell_formatter(group):
    def cell_formatter(value, item, formatter):
        group_url = absoluteURL(group, formatter.request)
        url = '%s?done_link=%s' % (absoluteURL(item, formatter.request),
                                   group_url)
        return '<a href="%s">%s</a>' % (url, value)
    return cell_formatter


class GroupAwarePersonTable(StatusPersonListTable):

    @property
    def app_states_name(self):
        if self.view.context.__name__ == 'students':
            return 'student-enrollment'
        return 'group-membership'

    def updateFormatter(self):
        group = self.view.context
        self.setUp(formatters=[done_link_url_cell_formatter(group),
                               done_link_url_cell_formatter(group)],
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data'})


class GroupAwarePersonTableFilter(PersonTableFilter):

    template = ViewPageTemplateFile('templates/f_group_aware_person_table_filter.pt')


class PersonGroupsTable(table.table.TableContent):

    group_by_column = 'schoolyear'

    @Lazy
    def source(self):
        int_ids = getUtility(IIntIds)
        source = dict([
                ('%s-%d' % (group.__name__, int_ids.getId(group)), group)
                for group in self.context.groups
                ])
        return source

    def columns(self):
        default = table.table.TableContent.columns(self)
        description = zc.table.column.GetterColumn(
            name='description',
            title=_('Description'),
            getter=lambda i, f: i.description or '',
            )
        schoolyear = SchoolYearColumn(
            name='schoolyear',
            title=_(u'School Year'),
            subsort=True)
        directlyProvides(schoolyear, ISortableColumn)
        return default + [description, schoolyear]


class PersonProfileGroupsPart(table.pdf.RMLTablePart):

    table_name = "groups_table"
    title = _("Group memberships")


class GroupPDFViewBase(flourish.report.PlainPDFPage):

    pass


class SignInOutPDFView(GroupPDFViewBase):

    name = _("Sign In & Out")

    @property
    def message_title(self):
        return _("group ${title} sign in & out",
                 mapping={'title': self.context.title})

    @property
    def scope(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return schoolyear.title

    @property
    def title(self):
        return self.context.title

    @property
    def base_filename(self):
        return 'group_sign_in_out_%s' % self.context.__name__


class RequestSignInOutReportView(RequestRemoteReportDialog):

    report_builder = 'sign_in_out.pdf'


def number_getter(person, formatter):
    for i, item in enumerate(formatter.items):
        if sameProxiedObjects(person, item):
            return i + 1


class SignInOutTable(table.ajax.Table):

    batch_size = 0
    visible_column_names = ['number', 'title', 'time_in', 'signing_in',
                            'time_out', 'signing_out']

    def items(self):
        return self.context.members

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()

    def columns(self):
        first_name = table.column.LocaleAwareGetterColumn(
            name='first_name',
            title=_(u'First Name'),
            getter=lambda i, f: i.first_name,
            subsort=True)
        last_name = table.column.LocaleAwareGetterColumn(
            name='last_name',
            title=_(u'Last Name'),
            getter=lambda i, f: i.last_name,
            subsort=True)
        number = zc.table.column.GetterColumn(
            name='number',
            title=u'#',
            getter=number_getter)
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Name'),
            getter=lambda i, f: i.title,
            subsort=True)
        time_in = zc.table.column.GetterColumn(
            name='time_in',
            title=_(u'Time In'),
            getter=lambda i, f: None)
        signing_in = zc.table.column.GetterColumn(
            name='signing_in',
            title=_(u'Person signing in'),
            getter=lambda i, f: None)
        time_out = zc.table.column.GetterColumn(
            name='time_out',
            title=_(u'Time Out'),
            getter=lambda i, f: None)
        signing_out = zc.table.column.GetterColumn(
            name='signing_out',
            title=_(u'Person signing out'),
            getter=lambda i, f: None)
        return [first_name, last_name, number, title,
                time_in, signing_in, time_out, signing_out]


class SignInOutTablePart(table.pdf.RMLTablePart):

    table_name = 'sign_in_out_table'
    table_style = 'sign-in-out'
    template = flourish.templates.XMLFile('rml/sign_in_out.pt')

    def getColumnWidths(self, rml_columns):
        return '5% 25% 10% 25% 10% 25%'


class OptionalRowVocabulary(SimpleVocabulary):

    implements(IContextSourceBinder)

    def __init__(self, context):
        self.context = context
        terms = self.createTerms(self.context.get('options'))
        SimpleVocabulary.__init__(self, terms)

    def createTerms(self, options):
        result = []
        for option in options:
            result.append(self.createTerm(
                option['value'],
                option['token'],
                option['title'],
            ))
        return result


def OptionalRowVocabularyFactory():
    return OptionalRowVocabulary


class IRequestStudentNameLabels(Interface):

    optional = Choice(
        title=_('Optional row'),
        source='schooltool.group.student_name_labels_optional_row',
        required=False)


class IColumnProvider(Interface):

    order = Int(title=u'Order', required=True)

    columns = Attribute('Iterable with zc.table columns')


class ColumnProvider(object):

    implements(IColumnProvider)
    adapts(flourish.page.PageBase)

    def __init__(self, view):
        self.context = view

    def columns(self):
        raise NotImplemented()


class DetailsColumnProvider(ColumnProvider):

    order = 0

    @Lazy
    def columns(self):
        result = []
        fields = ['preferred_name', 'birth_date']
        for name in fields:
            result.append(zc.table.column.GetterColumn(
                name=name,
                title=IBasicPerson[name].title,
                getter=self.get_person_detail(name)
                ))
        return result

    def get_person_detail(self, field):
        def getter(person, formatter):
            return getattr(person, field, None) or ''
        return getter


class DemographicsColumnProvider(ColumnProvider):

    order = 1

    @Lazy
    def columns(self):
        result = []
        limit_keys = ['students']
        dfs = IDemographicsFields(ISchoolToolApplication(None))
        for df in dfs.filter_keys(limit_keys):
            name = df.name
            if name not in LEAVE_SCHOOL_FIELDS:
                result.append(zc.table.column.GetterColumn(
                    name=name,
                    title=df.title,
                    getter=self.get_person_demographics(name)
                    ))
        return result

    def get_person_demographics(self, field):
        def getter(person, formatter):
            return IDemographics(person).get(field) or ''
        return getter


class LevelColumnProvider(ColumnProvider):

    order = 2

    @Lazy
    def columns(self):
        return [
            zc.table.column.GetterColumn(
                name='level',
                title=_('Grade Level'),
                getter=self.get_person_level)
        ]

    def get_person_level(self, person, formatter):
        result = []
        today = getUtility(IDateManager).today
        for level in person.levels.on(today).any(ACTIVE):
            result.append(level)
        return ', '.join([level.title for level in result])


class GroupTitleColumnProvider(ColumnProvider):

    order = 3

    @Lazy
    def columns(self):
        return [
            zc.table.column.GetterColumn(
                name='group',
                title=_('Group title'),
                getter=self.get_group_title)
        ]

    def get_group_title(self, person, formatter):
        view = self.context
        group = view.context
        return group.title


class RequestStudentNameLabelsReportView(RequestRemoteReportDialog):

    report_builder = 'student_name_labels.pdf'

    fields = field.Fields(IRequestStudentNameLabels)

    def resetForm(self):
        RequestRemoteReportDialog.resetForm(self)
        self.form_params['options'] = self.options()

    def options(self):
        result = []
        providers = sorted(getAdapters((self,), IColumnProvider),
                           key=lambda (name, provider): provider.order)
        for name, provider in providers:
            for column in provider.columns:
                token = '%s.%s' % (name, column.name)
                result.append({
                    'token': token,
                    'title': column.title,
                    'value': token,
                    })
        return result

    def updateTaskParams(self, task):
        optional = self.form_params.get('optional')
        if optional is not None:
            task.request_params['optional'] = optional


class StudentNameLabelsPDFView(GroupPDFViewBase):

    page_size = pagesizes.LETTER
    margin = flourish.report.Box(0.5*units.inch, (3.0/16.0)*units.inch)

    @property
    def message_title(self):
        return _("group ${title} student name labels",
                 mapping={'title': self.context.title})

    @property
    def scope(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return schoolyear.title

    @property
    def title(self):
        return self.context.title

    @property
    def base_filename(self):
        return 'group_student_name_labels_%s' % self.context.__name__


class StudentNameLabelsTablePart(table.pdf.RMLTablePart):

    table_name = 'student_name_labels_table'
    table_style = 'student-name-labels'
    paragraph_style = 'label-attr-center'
    template = flourish.templates.XMLFile('rml/student_name_labels.pt')
    column_count = 3
    row_height = 0.99 * units.inch

    def getColumnWidths(self, rml_columns):
        result = ['%.1f%%' % (100.0/self.column_count)] * self.column_count
        return ' '.join(result)

    def getRowHeights(self, rows):
        result = ['%.2f' % self.row_height] * len(rows)
        return ' '.join(result)

    def getRows(self, table):
        rows = table['rows']
        return [rows[i:i+self.column_count]
                for i in range(0, len(rows), self.column_count)]


class StudentNameLabelsTable(table.ajax.Table):

    batch_size = 0

    def items(self):
        return self.context.members

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()

    def columns(self):
        first_name = table.column.LocaleAwareGetterColumn(
            name='first_name',
            title=_(u'First Name'),
            getter=lambda i, f: i.first_name,
            subsort=True)
        last_name = table.column.LocaleAwareGetterColumn(
            name='last_name',
            title=_(u'Last Name'),
            getter=lambda i, f: i.last_name,
            subsort=True)
        result = [first_name, last_name]
        optional_column_token = self.request.get('optional')
        if optional_column_token is not None:
            provider_name, column_name = optional_column_token.split('.')
            provider = getAdapter(self.view, IColumnProvider,
                                  name=provider_name)
            optional_column = None
            for column in provider.columns:
                if column.name == column_name:
                    optional_column = column
                    break
            if optional_column is not None:
                result.append(optional_column)
        return result


class StudentNameLabelsPageTemplate(flourish.report.PlainPageTemplate):

    @Lazy
    def frame(self):
        doc_w, doc_h = self.manager.page_size
        margin = flourish.report.Box(0, 0)
        width = (doc_w - self.manager.margin.left - self.manager.margin.right
                 - margin.left - margin.right)
        height = (doc_h - self.manager.margin.top - self.manager.margin.bottom
                  - margin.top - margin.bottom)
        x = self.manager.margin.left + margin.left
        y = self.manager.margin.bottom + margin.bottom
        return {
            'height': height,
            'margin': margin,
            'width': width,
            'x': x,
            'y': y,
            }


class RequestMailingLabelsReportView(RequestRemoteReportDialog):

    report_builder = 'mailing_labels.pdf'


class MailingLabelsPDFView(StudentNameLabelsPDFView):

    @property
    def message_title(self):
        return _("group ${title} mailing labels",
                 mapping={'title': self.context.title})

    @property
    def scope(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return schoolyear.title

    @property
    def title(self):
        return self.context.title

    @property
    def base_filename(self):
        return 'group_mailing_labels_%s' % self.context.__name__


class MailingLabelsTablePart(StudentNameLabelsTablePart):

    table_name = 'mailing_labels_table'
    table_style = 'mailing-labels'
    paragraph_style = 'label-attr-left'
    column_count = 2
    row_height = 1.99 * units.inch


def city_getter(contact, formatter):
    contact = IContact(contact)
    city = contact.city
    if city is not None:
        city += ','
    state = contact.state
    postal_code = contact.postal_code
    return ' '.join(filter(None, [city, state, postal_code]))


class MailingLabelsTable(table.ajax.Table):

    batch_size = 0

    def has_address(self, contact):
        for field_name in IAddress:
            if getattr(contact, field_name):
                return True
        return False
            
    def items(self):
        result = []
        for member in self.context.members:
            if self.has_address(IContact(member)):
                result.append(member)
            for contact in IContactable(member).contacts:
                if self.has_address(contact):
                    result.append(contact)
        return result

    def columns(self):
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Name'),
            getter=lambda i, f: i.title,
            subsort=True)
        address_1 = zc.table.column.GetterColumn(
            name='address_1',
            title=_(u'Address 1'),
            getter=lambda i, f: IContact(i).address_line_1)
        address_2 = zc.table.column.GetterColumn(
            name='address_2',
            title=_(u'Address 2'),
            getter=lambda i, f: IContact(i).address_line_2)
        city = zc.table.column.GetterColumn(
            name='city',
            title=_(u'City'),
            getter=city_getter)
        country = zc.table.column.GetterColumn(
            name='country',
            title=_(u'Country'),
            getter=lambda i, f: IContact(i).country)
        return [title, address_1, address_2, city, country]
