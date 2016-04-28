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
Basic stubs for testing SchoolTool.
"""

from persistent.interfaces import IPersistent
from transaction import commit

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.publication.zopepublication import ZopePublication
from zope.app.testing.setup import createSiteManager
from zope.interface import implements
from zope.component import adapts
from zope.component import provideAdapter
from zope.container.btree import BTreeContainer
from zope.event import notify
from zope.keyreference.interfaces import IKeyReference
from zope.site import SiteManagerContainer
from zope.traversing.interfaces import IContainmentRoot

from ZODB.tests.util import DB

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ApplicationInitializationEvent
from schooltool.app.interfaces import CatalogStartUpEvent
from schooltool.app.main import initializeSchoolToolPlugins


class KeyReferenceStub(object):
    implements(IKeyReference)
    adapts(IPersistent)

    key_type_id = 'schooltool.testing.stubs.KeyReferenceStub'

    def __init__(self, obj):
        self.object = obj
        self.uid = id(obj)

    def __call__(self):
        return self.object

    def __hash__(self):
        return hash(self.uid)

    def __cmp__(self, other):
        if self.key_type_id != other.key_type_id:
            return cmp(self.key_type_id, other.key_type_id)
        return cmp(self.uid, other.uid)


class AppStub(BTreeContainer, SiteManagerContainer):
    implements(ISchoolToolApplication, IAttributeAnnotatable, IContainmentRoot)

    def __init__(self):
        super(AppStub, self).__init__()
        self.setup()

    def setup(self):
        db = DB()
        conn = db.open()
        root = conn.root()
        root[ZopePublication.root_name] = self
        provideAdapter(
            lambda ignored: self,
            adapts=(None,),
            provides=ISchoolToolApplication)
        commit()
        createSiteManager(self, setsite=True)
        initializeSchoolToolPlugins(ApplicationInitializationEvent(self))
        notify(CatalogStartUpEvent(self))
