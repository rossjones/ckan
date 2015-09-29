'''Unit tests for ckan/logic/auth/create.py.

'''

from pylons import config
import mock
import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestResourceCreate(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_resource_create(self):
        context = {}
        params = {
            'package_id': factories.Dataset()['id'],
            'url': 'http://data',
            'name': 'A nice resource',
        }
        result = helpers.call_action('resource_create', context, **params)

        id = result.pop('id')

        assert id

        params.pop('package_id')
        for key in params.keys():
            assert_equals(params[key], result[key])

    def test_it_requires_package_id(self):

        data_dict = {
            'url': 'http://data',
        }

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_create', **data_dict)

    def test_it_requires_url(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        data_dict = {
            'package_id': dataset['id']
        }

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_create', **data_dict)


class TestMemberCreate(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_group_member_creation(self):
        user = factories.User()
        group = factories.Group()

        new_membership = helpers.call_action(
            'group_member_create',
            id=group['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], group['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')

    def test_organization_member_creation(self):
        user = factories.User()
        organization = factories.Organization()

        new_membership = helpers.call_action(
            'organization_member_create',
            id=organization['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], organization['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')


class TestDatasetCreate(helpers.FunctionalTestBase):

    def test_normal_user_cant_set_id(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': False,
        }
        assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'package_create',
            context=context,
            id='1234',
            name='test-dataset',
        )

    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'ignore_auth': False,
        }
        dataset = helpers.call_action(
            'package_create',
            context=context,
            id='1234',
            name='test-dataset',
        )
        assert_equals(dataset['id'], '1234')

    def test_id_cant_already_exist(self):
        dataset = factories.Dataset()
        user = factories.Sysadmin()
        assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'package_create',
            id=dataset['id'],
            name='test-dataset',
        )


class TestGroupCreate(helpers.FunctionalTestBase):

    def test_create_group(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='test-group',
        )

        assert len(group['users']) == 1
        assert group['display_name'] == u'test-group'
        assert group['package_count'] == 0
        assert not group['is_organization']
        assert group['type'] == 'group'

    @nose.tools.raises(logic.ValidationError)
    def test_create_group_validation_fail(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='',
        )

    def test_create_group_return_id(self):
        import re

        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
            'return_id_only': True
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='test-group',
        )

        assert isinstance(group, str)
        assert re.match('([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)', group)

    def test_create_matches_show(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        created = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        shown = helpers.call_action(
            'organization_show',
            context=context,
            id='test-organization',
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k


class TestOrganizationCreate(helpers.FunctionalTestBase):

    def test_create_organization(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        assert len(org['users']) == 1
        assert org['display_name'] == u'test-organization'
        assert org['package_count'] == 0
        assert org['is_organization']
        assert org['type'] == 'organization'

    @nose.tools.raises(logic.ValidationError)
    def test_create_organization_validation_fail(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='',
        )

    def test_create_organization_return_id(self):
        import re

        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
            'return_id_only': True
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        assert isinstance(org, str)
        assert re.match('([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)', org)

    def test_create_matches_show(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        created = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        shown = helpers.call_action(
            'organization_show',
            context=context,
            id='test-organization',
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k
