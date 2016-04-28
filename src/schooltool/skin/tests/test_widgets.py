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
Unit tests for common widgets.
"""
import unittest
import doctest

import zope.component
import zope.interface
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest

from z3c import form

from schooltool.schoolyear.ftesting import schoolyear_functional_layer
import schooltool.skin.widgets
from schooltool import skin
from schooltool.schoolyear.testing import setUp, tearDown


class FormRequest(TestRequest):
    zope.interface.implements(skin.skin.ISchoolToolLayer)


def doctest_HTMLFragmentWidget():
    """Tests for HTMLFragmentWidget.

        >>> widget = skin.widgets.HTMLFragmentWidget()
        >>> verifyObject(skin.widgets.IHTMLFragmentWidget, widget)
        True

    """


def doctest_CkeditorZ3CFormWidget_CkeditorConfig():
    """Tests for CkeditorZ3CFormWidget and CkeditorConfig.

    We'll need a field first.

        >>> from zope.html.field import HtmlFragment
        >>> schema_field = HtmlFragment(__name__='html', title=u"Fragment")

    Let's build a widget bound to the field.

        >>> zope.component.provideAdapter(skin.widgets.CkeditorFieldWidget)

        >>> request = FormRequest()
        >>> widget = zope.component.getMultiAdapter(
        ...     (schema_field, request), form.interfaces.IFieldWidget)

        >>> print widget
        <CkeditorZ3CFormWidget 'html'>

        >>> verifyObject(skin.widgets.ICkeditorWidget, widget)
        True

    Widget initially has no config set, so it cannot render the CKEditor
    javascript setup.

        >>> print widget.config
        None

        >>> widget.script
        Traceback (most recent call last):
        ...
        AttributeError: ...

    Config will be set during widget update, as a computed widget value.

        >>> zope.component.provideAdapter(
        ...     skin.widgets.Ckeditor_config, name='config')

        >>> value = zope.component.getMultiAdapter(
        ...     (widget.context, widget.request,
        ...      widget.form, widget.field, widget),
        ...     form.interfaces.IValue, name='config')

        >>> print value
        <ComputedValue <schooltool.skin.widgets.CkeditorConfig
          (430 x 300, u'schooltool' toolbar, u'/@@/editor_config.js')>>

        >>> verifyObject(skin.widgets.ICkeditorConfig, value.get())
        True

        >>> widget.update()

        >>> print widget.config
        <schooltool.skin.widgets.CkeditorConfig
          (430 x 300, u'schooltool' toolbar, u'/@@/editor_config.js')>

    Now we can render the javascript.

        >>> print widget.script
        <script type="text/javascript" language="JavaScript">
            var CKeditor... = new CKEDITOR.replace("html",
                {
                    height: 300,
                    width: 430,
                    customConfig: "http://127.0.0.1/@@/editor_config.js"
                }
            );
        </script>

    Let's set the widget value.

        >>> widget.update()

        >>> widget.value
        u''

        >>> request = FormRequest(
        ...     form={widget.name: '<strong>All hail hypnotoad!</strong>'})

        >>> widget = zope.component.getMultiAdapter(
        ...     (schema_field, request), form.interfaces.IFieldWidget)

        >>> widget.update()
        >>> print widget.value
        <strong>All hail hypnotoad!</strong>

    We also have a different configuration for add and edit forms.

        >>> zope.component.provideAdapter(
        ...     skin.widgets.Ckeditor_addform_config, name='config')
        >>> zope.component.provideAdapter(
        ...     skin.widgets.Ckeditor_editform_config, name='config')

        >>> widget.form = form.form.AddForm(None, request)
        >>> widget.update()
        >>> print widget.config
        <schooltool.skin.widgets.CkeditorConfig
          (306 x 200, u'schooltool' toolbar, u'/@@/editor_config.js')>

        >>> verifyObject(skin.widgets.ICkeditorConfig, widget.config)
        True

        >>> widget.form = form.form.EditForm(None, request)
        >>> widget.update()
        >>> print widget.config
        <schooltool.skin.widgets.CkeditorConfig
          (306 x 200, u'schooltool' toolbar, u'/@@/editor_config.js')>

    """


def doctest_CkeditorZ3CWidget_compatibility():
    r"""Tests for CkeditorZ3CFormWidget compatibility with zope.html.

    We'll need a field first.

        >>> from zope.html.field import HtmlFragment
        >>> schema_field = HtmlFragment(__name__='html', title=u"Fragment")

    Let's build a widget bound to the field.

        >>> zope.component.provideAdapter(skin.widgets.CkeditorFieldWidget)

        >>> request = FormRequest()
        >>> widget = zope.component.getMultiAdapter(
        ...     (schema_field, request), form.interfaces.IFieldWidget)

        >>> verifyObject(skin.widgets.ICkeditorWidget, widget)
        True

    Specify the CkeditorConfig.

        >>> zope.component.provideAdapter(
        ...     skin.widgets.Ckeditor_config, name='config')

    Now we can render the javascript.

        >>> widget.update()
        >>> print widget.script
        <script type="text/javascript" language="JavaScript">
        ...
        </script>

    Let's now look at a fully rendered zope.html widget.

        >>> from zope.html.widget import CkeditorWidget
        >>> editor = CkeditorWidget(schema_field, request)

        >>> print editor()
        <textarea cols="60" id="field.html" name="field.html" rows="15" ></textarea>
        <script type="text/javascript" language="JavaScript">
        var CKeditor_html = new CKEDITOR.replace("field.html",
            {
                height: 400,
                customConfig : "/@@/zope_ckconfig.js",
            }
        );
        </script>

    We can also modify the configuration of the zope.html widget.

        >>> editor.editorWidth = 430
        >>> editor.editorHeight = 300
        >>> editor.toolbarConfiguration = "schooltool"
        >>> editor.configurationPath = '/@@/editor_config.js'

        >>> print editor()
        <textarea cols="60" id="field.html" name="field.html" rows="15" ></textarea>
        <script type="text/javascript" language="JavaScript">
        var CKeditor_html = new CKEDITOR.replace("field.html",
            {
                height: 300,
                customConfig : "/@@/editor_config.js",
            }
        );
        </script>

    You can notice zope.html widget uses relative paths for configuration;
    this breaks the widget if admins start fiddling with Apache's mod-rewrite
    (to put schooltool in http://example.com/schooltool for example).

    Our widget also uses a different mechanism to generate the CKeditor
    variable name.

        >>> import difflib
        >>> def print_diff(old, new):
        ...     stripped = lambda s: [l.strip() for l in s.splitlines()]
        ...     diff = difflib.ndiff(stripped(old), stripped(new))
        ...     print '\n'.join(l.strip() for l in diff)

        >>> widget_text = widget.script
        >>> widget_text = widget_text.replace(
        ...     widget.editor_var_name,
        ...     'CKeditor_html').strip()

        >>> print_diff(editor(), widget_text)
        - <textarea cols="60" id="field.html" name="field.html" rows="15" ></textarea>
        <script type="text/javascript" language="JavaScript">
        - var CKeditor_html = new CKEDITOR.replace("field.html",
        ?                                           ------
        + var CKeditor_html = new CKEDITOR.replace("html",
        {
        height: 300,
        + width: 430,
        - customConfig : "/@@/editor_config.js",
        ?             -                        -
        + customConfig: "http://127.0.0.1/@@/editor_config.js"
        ?                 ++++++++++++++++
        }
        );
        </script>

    """


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = schoolyear_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
