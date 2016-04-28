#
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
Contact information of a Person.

Glue between schooltool.basicperson and schooltool.contact.
"""
import urllib

from zope.schema import getFieldsInOrder
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import field

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.contact.basicperson import IBoundContact
from schooltool.contact.contact import getAppContactStates
from schooltool.contact.interfaces import IContactInformation
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactPerson
from schooltool.contact.interfaces import IAddress, IEmails, IPhones, ILanguages
from schooltool.contact.browser.contact import ContactEditView
from schooltool.contact.browser.contact import FlourishContactEditView
from schooltool.contact.browser.contact import FlourishContactDetails
from schooltool.contact.browser.contact import get_relationship_title
from schooltool.skin.flourish.page import Page
from schooltool.common import SchoolToolMessage as _


class ContactOverviewView(BrowserView):
    """View class for listing all relevant contact information of a person."""

    __used_for__ = IBoundContact

    @property
    def person(self):
        return self.context.__parent__

    def _extract_attrs(self, contact, interface,
                       conjunctive=", ", add_title=False):
        parts = []
        for name, field in getFieldsInOrder(interface):
            part = getattr(contact, name, None)
            part = part and part.strip() or part
            if not part:
                continue
            if add_title:
                parts.append("%s (%s)" % (part, field.title))
            else:
                parts.append(part)
        return parts

    @property
    def app_states(self):
        return getAppContactStates()

    def contactInfo(self, contact_context, title):
        contact = IContact(contact_context)
        return {
            'link': absoluteURL(contact_context, self.request),
            'relationship': title,
            'name': " ".join(self._extract_attrs(contact, IContactPerson)),
            'address': ", ".join(self._extract_attrs(contact, IAddress)),
            'emails': ", ".join(self._extract_attrs(contact, IEmails)),
            'phones': list(self._extract_attrs(contact, IPhones,
                                               add_title=True)),
            'languages': ", ".join(self._extract_attrs(contact, ILanguages)),
            '__parent__': contact_context,
            }

    def buildInfo(self, contact):
        contact = IContact(contact)
        title = get_relationship_title(self.person, contact)
        return self.contactInfo(contact, title)

    def buildPersonInfo(self, info):
        contact = info.target
        title = self.app_states.getTitle(info.state.today) or u''
        return self.contactInfo(contact, title)

    def getContacts(self):
        contacts = IContactable(removeSecurityProxy(self.person)).contacts
        return [self.buildInfo(contact) for contact in contacts]

    def getRelationships(self):
        return [self.buildPersonInfo(info)
                for info in self.context.persons.any().relationships]

    def getPerson(self):
        bound = IContact(self.person)
        return self.buildInfo(bound)


class BoundContactEditView(ContactEditView):
    """Edit form for a bound contact."""
    fields = field.Fields(IContactInformation).omit('photo')


class FlourishBoundContactView(Page):

    pass


class FlourishBoundContactDetails(FlourishContactDetails):

    def canModify(self):
        return checkPermission("schooltool.edit", self.context)


class FlourishBoundContactEditView(FlourishContactEditView):

    fields = field.Fields(IContactInformation).omit('photo')

    def buildFieldsetGroups(self):
        self.fieldset_groups = {
            'address': (
                _('Address'),
                ['address_line_1', 'address_line_2', 'city', 'state',
                 'country', 'postal_code']),
            'contact_information': (
                _('Contact Information'),
                ['home_phone', 'work_phone', 'mobile_phone', 'email',
                 'other_1', 'other_2',
                 'language']),
            }
        self.fieldset_order = (
            'address', 'contact_information')

    def nextURL(self):
        if 'person_id' in self.request:
            person_id = self.request['person_id']
            app = ISchoolToolApplication(None)
            persons = app['persons']
            if person_id in persons:
                return absoluteURL(persons[person_id], self.request)
        base_url = absoluteURL(self.context.__parent__, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_TITLE',
                               self.context.last_name.encode("utf-8"))]))


class ManageContactsActionViewlet(object):
    @property
    def link(self):
        base_url = absoluteURL(self.context.__parent__, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_LAST_NAME',
                               self.context.last_name.encode("utf-8"))]))
