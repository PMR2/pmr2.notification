import unittest
import warnings
from email import message_from_string
from email.header import decode_header

import zope.component

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from Products.PloneTestCase import ptc
from Products.MailHost.interfaces import IMailHost
from Products.CMFPlone.tests.utils import MockMailHost
from plone.registry.interfaces import IRegistry

from plone.app.testing import TEST_USER_ID, setRoles

from pmr2.testing.base import TestRequest
from pmr2.notification.testing.layer import NOTIFICATION_INTEGRATION_LAYER

from pmr2.notification.workflow.interfaces import ISettings
from pmr2.notification.workflow.browser import SettingsEditForm
from pmr2.notification.workflow.subscriber import workflow_email



class SettingsTestCase(unittest.TestCase):
    """
    Test that the settings is set up correctly.
    """

    layer = NOTIFICATION_INTEGRATION_LAYER

    def setUp(self):
        self.registry = zope.component.getUtility(IRegistry)
        self.settings = self.registry.forInterface(ISettings,
            prefix='pmr2.notification.workflow.settings')

    def test_basic_render_form(self):
        request = TestRequest()
        form = SettingsEditForm(self.layer['portal'], request)
        form.update()
        result = form.render()
        self.assertTrue(result)

    def test_edit_field(self):
        request = TestRequest(form={
            'form.widgets.wf_change_recipient': 'user@example.com',
            'form.widgets.wf_send_email': 'selected',
            'form.widgets.subject_template': 'subject',
            'form.widgets.message_template': 'message',
            'form.buttons.apply': 1,
        })
        form = SettingsEditForm(self.layer['portal'], request)
        form.update()
        self.assertEqual(self.settings.wf_change_recipient, 'user@example.com')
        self.assertTrue(self.settings.wf_send_email)

    def test_render_field(self):
        self.settings.wf_change_recipient = u'tester@example.com'

        request = TestRequest()
        form = SettingsEditForm(self.layer['portal'], request)
        form.update()
        result = form.render()
        self.assertIn('tester@example.com', result)


class MailTestCase(unittest.TestCase):
    """
    Test to see that emails are sent.
    """

    layer = NOTIFICATION_INTEGRATION_LAYER

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

        self.registry = zope.component.getUtility(IRegistry)
        self.settings = self.registry.forInterface(ISettings,
            prefix='pmr2.notification.workflow.settings')
        self.settings.wf_change_recipient = u'tester@example.com'
        self.settings.wf_send_email = True

        self.portal._original_MailHost = self.portal.MailHost
        self.portal.MailHost = mailhost = MockMailHost('MailHost')
        sm = zope.component.getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(mailhost, provided=IMailHost)
        # We need to fake a valid mail setup
        self.portal.email_from_address = 'admin@example.com'
        self.mailhost = self.portal.MailHost

    def tearDown(self):
        self.portal.MailHost = self.portal._original_MailHost
        sm = zope.component.getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(aq_base(self.portal._original_MailHost),
                           provided=IMailHost)

    def test_workflow_email_success(self):
        self.settings.wf_change_states = [u'pending']
        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.test, "submit")
        msg = message_from_string(self.mailhost.messages[0])
        self.assertEqual(
            'Workspace `test` is now pending',
            decode_header(msg.get('Subject'))[0][0]
        )
        self.assertEqual('tester@example.com', msg.get('To'))
        self.assertEqual('admin@example.com', msg.get('From'))
        self.assertEqual(
            'Visit http://nohost/plone/workspace/test for more details.',
            msg.get_payload()
        )

    def test_workflow_email_custom_format_success(self):
        self.settings.wf_change_states = [u'published']
        self.settings.subject_template = u'Item: ({not_exist})'
        self.settings.message_template = (u'{obj.id} is now '
            '{event.transition.new_state_id} at site <{portal_url}>.')

        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.cake, "publish")
        msg = message_from_string(self.mailhost.messages[0])
        self.assertEqual('Item: ()', decode_header(msg.get('Subject'))[0][0])
        self.assertEqual('tester@example.com', msg.get('To'))
        self.assertEqual('admin@example.com', msg.get('From'))
        self.assertEqual(
            'cake is now published at site <http://nohost/plone>.',
            msg.get_payload()
        )

    def test_workflow_email_custom_format_malformed(self):
        self.settings.wf_change_states = [u'published']
        self.settings.subject_template = u'Item: not_exist}'
        self.settings.message_template = \
            u'{obj.not_attribute} is now {event.transition.new_state_id}'
        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.cake, "publish")
        msg = message_from_string(self.mailhost.messages[0])
        # None of the message templates will be processed here.
        self.assertEqual(
            'Item: not_exist}', decode_header(msg.get('Subject'))[0][0])
        self.assertEqual('tester@example.com', msg.get('To'))
        self.assertEqual('admin@example.com', msg.get('From'))
        self.assertEqual(
            '{obj.not_attribute} is now {event.transition.new_state_id}',
            msg.get_payload(),
        )

    def test_workflow_email_skipped_wf_state(self):
        self.settings.wf_change_states = [u'pending']
        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.test, "publish")
        self.assertEqual(len(self.mailhost.messages), 0)

    def test_workflow_email_not_in_state(self):
        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.test, "submit")
        self.assertEqual(len(self.mailhost.messages), 0)

    def test_workflow_email_disabled(self):
        self.settings.wf_send_email = False
        pw = getToolByName(self.portal, "portal_workflow")
        pw.doActionFor(self.portal.workspace.test, "submit")
        self.assertEqual(len(self.mailhost.messages), 0)

    def test_workflow_email_create_nofailure(self):
        # There will be a case where object is created but no transition
        # states will be available.  It should not fail.
        self.settings.wf_change_states = [u'published']
        from pmr2.app.workspace.content import Workspace
        wks = Workspace('wf_mail_test')
        self.portal.workspace['wf_mail_test'] = wks
        wks.notifyWorkflowCreated()
        self.assertEqual(len(self.mailhost.messages), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(SettingsTestCase))
    suite.addTest(makeSuite(MailTestCase))
    return suite
