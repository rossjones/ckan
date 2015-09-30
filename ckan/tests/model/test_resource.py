import nose.tools

import ckan.model as model
import ckan.plugins as p

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals
Resource = model.Resource


class TestResource(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_edit_url(self):
        res_dict = factories.Resource(url='http://first')
        res = Resource.get(res_dict['id'])
        res.url = 'http://second'
        model.repo.new_revision()
        model.repo.commit_and_remove()
        res = Resource.get(res_dict['id'])
        assert_equals(res.url, 'http://second')

    def test_edit_extra(self):
        res_dict = factories.Resource(newfield='first')
        res = Resource.get(res_dict['id'])
        res.extras = {'newfield': 'second'}
        res.url
        model.repo.new_revision()
        model.repo.commit_and_remove()
        res = Resource.get(res_dict['id'])
        assert_equals(res.extras['newfield'], 'second')
