#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Selenium functional tests setup for schooltool.basicperson
"""

import os

from schooltool.testing.selenium import SeleniumLayer
from schooltool.testing.selenium import add_temporal_relationship
from schooltool.testing.selenium import print_tree

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

basicperson_selenium_layer = SeleniumLayer(filename,
                                           __name__,
                                           'basicperson_selenium_layer')

def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def login(browser, username, password):
        browser.open('http://localhost')
        browser.query.link('Log in').click()
        browser.query.name('username').type(username)
        browser.query.name('password').type(password)
        page = browser.query.tag('html')
        browser.query.button('Log in').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'login', login))

    def addPerson(browser, first_name, last_name, username, password, **kw):
        optional = (
            'prefix',
            'middle_name',
            'suffix',
            'preferred_name',
            'gender',
            'birth_date',
            'ID',
            'ethnicity',
            'language',
            'placeofbirth',
            'citizenship',
            'group',
            'advisor',
            )
        browser.open('http://localhost/persons')
        page = browser.query.tag('html')
        browser.query.link('Person').click()
        browser.wait(lambda: page.expired)
        browser.query.name('form.widgets.first_name').type(first_name)
        browser.query.name('form.widgets.last_name').type(last_name)
        browser.query.name('form.widgets.username').type(username)
        browser.query.name('form.widgets.password').type(password)
        browser.query.name('form.widgets.confirm').type(password)
        for name in optional:
            if name in kw:
                value = kw[name]
                widget_id = ''.join(['form-widgets-', name])
                browser.query.id(widget_id).ui.set_value(value)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.add', addPerson))

    def addAdvisors(browser, username, advisors, state=None, date=None):
        browser.open('http://localhost/persons/%s/advisors.html' % username)
        add_temporal_relationship(browser, advisors, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.advisors.add', addAdvisors))

    def addAdvisees(browser, username, advisees, state=None, date=None):
        browser.open('http://localhost/persons/%s/advisees.html' % username)
        add_temporal_relationship(browser, advisees, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.advisees.add', addAdvisees))

    def printSectionTrees(browser):
        accordion_header = browser.query_all.css('.ui-accordion-header')[3]
        accordion_header.click()
        accordion_content = browser.query_all.css('div.ui-accordion-content')[3]
        browser.wait(accordion_content.is_displayed)
        for block in accordion_content.query_all.css('.info-block'):
            print block.query.tag('h3').text
            tree = block.query.css('.tree_list > ul')
            print_tree(tree)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.print_section_trees', printSectionTrees))

    def printGroupTrees(browser):
        accordion_header = browser.query_all.css('.ui-accordion-header')[4]
        accordion_header.click()
        accordion_content = browser.query_all.css('div.ui-accordion-content')[4]
        browser.wait(accordion_content.is_displayed)
        print accordion_content.query.tag('h3').text
        tree = accordion_content.query.css('.tree_list > ul')
        print_tree(tree)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.print_group_trees', printGroupTrees))


registerSeleniumSetup()
del registerSeleniumSetup
