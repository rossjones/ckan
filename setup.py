try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import (__version__, __description__, __long_description__,
                  __license__)

entry_points = {
    'nose.plugins.0.10': [
        'main = ckan.ckan_nose_plugin:CkanNose',
    ],
    'paste.app_factory': [
        'main = ckan.config.middleware:make_app',
    ],
    'paste.app_install': [
        'main = ckan.config.install:CKANInstaller',
    ],
    'paste.paster_command': [
        'db = ckan.lib.cli:ManageDb',
        'create-test-data = ckan.lib.cli:CreateTestDataCommand',
        'sysadmin = ckan.lib.cli:Sysadmin',
        'user = ckan.lib.cli:UserCmd',
        'dataset = ckan.lib.cli:DatasetCmd',
        'search-index = ckan.lib.cli:SearchIndexCommand',
        'ratings = ckan.lib.cli:Ratings',
        'notify = ckan.lib.cli:Notification',
        'celeryd = ckan.lib.cli:Celery',
        'rdf-export = ckan.lib.cli:RDFExport',
        'tracking = ckan.lib.cli:Tracking',
        'plugin-info = ckan.lib.cli:PluginInfo',
        'profile = ckan.lib.cli:Profile',
        'color = ckan.lib.cli:CreateColorSchemeCommand',
        'check-po-files = ckan.i18n.check_po_files:CheckPoFiles',
        'trans = ckan.lib.cli:TranslationsCommand',
        'minify = ckan.lib.cli:MinifyCommand',
        'less = ckan.lib.cli:LessCommand',
        'datastore = ckanext.datastore.commands:SetupDatastoreCommand',
        'datapusher = ckanext.datapusher.cli:DatapusherCommand',
        'front-end-build = ckan.lib.cli:FrontEndBuildCommand',
        'views = ckan.lib.cli:ViewsCommand',
        'config-tool = ckan.lib.cli:ConfigToolCommand',
    ],
    'console_scripts': [
        'ckan-admin = bin.ckan_admin:Command',
    ],
    'paste.paster_create_template': [
        'ckanext = ckan.pastertemplates:CkanextTemplate',
    ],
    'ckan.plugins': [
        'synchronous_search = ckan.lib.search:SynchronousSearchPlugin',
        'publisher_form = ckanext.publisher_form.forms:PublisherForm',
        'publisher_dataset_form = ckanext.publisher_form.forms:PublisherDatasetForm',
        'multilingual_dataset = ckanext.multilingual.plugin:MultilingualDataset',
        'multilingual_group = ckanext.multilingual.plugin:MultilingualGroup',
        'multilingual_tag = ckanext.multilingual.plugin:MultilingualTag',
        'multilingual_resource = ckanext.multilingual.plugin:MultilingualResource',
        'organizations = ckanext.organizations.forms:OrganizationForm',
        'organizations_dataset = ckanext.organizations.forms:OrganizationDatasetForm',
        'datastore = ckanext.datastore.plugin:DatastorePlugin',
        'datapusher=ckanext.datapusher.plugin:DatapusherPlugin',
    ],
    'ckan.system_plugins': [
        'domain_object_mods = ckan.model.modification:DomainObjectModificationExtension',
    ],
    'ckan.test_plugins': [
        'routes_plugin = tests.legacy.ckantestplugins:RoutesPlugin',
        'mapper_plugin = tests.legacy.ckantestplugins:MapperPlugin',
        'session_plugin = tests.legacy.ckantestplugins:SessionPlugin',
        'mapper_plugin2 = tests.legacy.ckantestplugins:MapperPlugin2',
        'authorizer_plugin = tests.legacy.ckantestplugins:AuthorizerPlugin',
        'test_observer_plugin = tests.legacy.ckantestplugins:PluginObserverPlugin',
        'action_plugin = tests.legacy.ckantestplugins:ActionPlugin',
        'auth_plugin = tests.legacy.ckantestplugins:AuthPlugin',
        'test_group_plugin = tests.legacy.ckantestplugins:MockGroupControllerPlugin',
        'test_package_controller_plugin = tests.legacy.ckantestplugins:MockPackageControllerPlugin',
        'test_resource_preview = tests.legacy.ckantestplugins:MockResourcePreviewExtension',
        'test_json_resource_preview = tests.legacy.ckantestplugins:JsonMockResourcePreviewExtension',
        'sample_datastore_plugin = ckanext.datastore.tests.sample_datastore_plugin:SampleDataStorePlugin',
        'test_datastore_view = ckan.tests.lib.test_datapreview:MockDatastoreBasedResourceView',
    ],
    'babel.extractors': [
        'ckan = ckan.lib.extract:extract_ckan',
    ],
}

setup(
    name='ckan',
    version=__version__,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license=__license__,
    url='http://ckan.org/',
    description=__description__,
    keywords='data packaging component tool server',
    long_description=__long_description__,
    zip_safe=False,
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    package_data={'ckan': [
        'i18n/*/LC_MESSAGES/*.mo',
        'migration/migrate.cfg',
        'migration/README',
        'migration/tests/test_dumps/*',
        'migration/versions/*',
    ]},
    message_extractors={
        'ckan': [
            ('**.py', 'python', None),
        ],
        'ckanext': [
            ('**.py', 'python', None),
            ('multilingual/solr/*.txt', 'ignore', None),
        ]
    },
    entry_points=entry_points,
)
