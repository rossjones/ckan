import ckan.tests.helpers as helpers

from nose.tools import assert_equals, assert_not_equals
from routes import url_for


class TestPylonsResponseCleanupMiddleware(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, config):
        config['ckan.use_pylons_response_cleanup_middleware'] = True

