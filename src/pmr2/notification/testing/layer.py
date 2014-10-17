from plone.app.testing import PloneSandboxLayer
from plone.app.testing import IntegrationTesting
from plone.testing import z2

from pmr2.app.workspace.tests import layer


class NotificationLayer(PloneSandboxLayer):

    defaultBases = (layer.WORKSPACE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import pmr2.notification
        self.loadZCML(package=pmr2.notification)
        z2.installProduct(app, 'pmr2.notification')

        # until pmr2.z3cform has a layer, this is needed to fully render
        # the forms.
        import pmr2.z3cform.tests
        self.loadZCML('testing.zcml', package=pmr2.z3cform.tests)

    def setUpPloneSite(self, portal):
        """
        Apply the default pmr2.notification profile and ensure that the
        settings have the tmpdir applied in.
        """

        # install pmr2.notification
        self.applyProfile(portal, 'pmr2.notification:default')

    def tearDownZope(self, app):
        z2.uninstallProduct(app, 'pmr2.notification')


NOTIFICATION_FIXTURE = NotificationLayer()

NOTIFICATION_INTEGRATION_LAYER = IntegrationTesting(
    bases=(NOTIFICATION_FIXTURE,), name="pmr2.notification:integration")
