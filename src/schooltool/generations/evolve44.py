#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2014 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 44.

Add leave school demographics fields
"""

from zope.app.generations.utility import getRootFolder
from zope.component.hooks import getSite, setSite

from schooltool.basicperson.demographics import setUpLeaveSchoolDemographics


def evolve(context):
    root = getRootFolder(context)
    old_site = getSite()
    app = root
    setSite(app)
    setUpLeaveSchoolDemographics(app)
    setSite(old_site)
