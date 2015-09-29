# -*- coding: utf-8 -*-
"""Pylons environment configuration"""
import os
import logging
import warnings
from urlparse import urlparse

import pylons
from paste.deploy.converters import asbool
import sqlalchemy
from pylons import config
from genshi.template import TemplateLoader
from genshi.filters.i18n import Translator

import ckan.config.routing as routing
import ckan.model as model
import ckan.plugins as p
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.lib.search as search
import ckan.logic as logic
import ckan.authz as authz

from ckan.common import _, ungettext

log = logging.getLogger(__name__)


# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning)


class _Helpers(object):
    ''' Helper object giving access to template helpers stopping
    missing functions from causing template exceptions. Useful if
    templates have helper functions provided by extensions that have
    not been enabled. '''
    def __init__(self, helpers):
        self.helpers = helpers
        self._setup()

    def _setup(self):
        helpers = self.helpers
        functions = {}
        allowed = helpers.__allowed_functions__[:]
        # list of functions due to be deprecated
        self.deprecated = []

        for helper in dir(helpers):
            if helper not in allowed:
                self.deprecated.append(helper)
                continue
            functions[helper] = getattr(helpers, helper)
            if helper in allowed:
                allowed.remove(helper)
        self.functions = functions

        if allowed:
            raise Exception('Template helper function(s) `%s` not defined'
                            % ', '.join(allowed))

        # extend helper functions with ones supplied by plugins
        extra_helpers = []
        for plugin in p.PluginImplementations(p.ITemplateHelpers):
            helpers = plugin.get_helpers()
            for helper in helpers:
                if helper in extra_helpers:
                    raise Exception('overwritting extra helper %s' % helper)
                extra_helpers.append(helper)
                functions[helper] = helpers[helper]
        # logging
        self.log = logging.getLogger('ckan.helpers')

    @classmethod
    def null_function(cls, *args, **kw):
        ''' This function is returned if no helper is found. The idea is
        to try to allow templates to be rendered even if helpers are
        missing.  Returning the empty string seems to work well.'''
        return ''

    def __getattr__(self, name):
        ''' return the function/object requested '''
        if name in self.functions:
            if name in self.deprecated:
                msg = 'Template helper function `%s` is deprecated' % name
                self.log.warn(msg)
            return self.functions[name]
        else:
            if name in self.deprecated:
                msg = ('Template helper function `{0}` is not available '
                       'because it has been deprecated.'.format(name))
                self.log.critical(msg)
            else:
                msg = 'Helper function `%s` could not be found\n ' \
                      '(are you missing an extension?)' % name
                self.log.critical(msg)
            return self.null_function


def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object.  This code should only need to be run once.
    """

    ######  Pylons monkey-patch
    # this must be run at a time when the env is semi-setup, thus inlined here.
    # Required by the deliverance plugin and iATI
    from pylons.wsgiapp import PylonsApp
    import pkg_resources
    find_controller_generic = PylonsApp.find_controller

    # This is from pylons 1.0 source, will monkey-patch into 0.9.7
    def find_controller(self, controller):
        if controller in self.controller_classes:
            return self.controller_classes[controller]
        # Check to see if its a dotted name
        if '.' in controller or ':' in controller:
            mycontroller = pkg_resources \
                .EntryPoint \
                .parse('x=%s' % controller).load(False)
            self.controller_classes[controller] = mycontroller
            return mycontroller
        return find_controller_generic(self, controller)
    PylonsApp.find_controller = find_controller
    ###### END evil monkey-patch

    os.environ['CKAN_CONFIG'] = global_conf['__file__']

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='ckan', paths=paths)

    # Setup the SQLAlchemy database engine
    # Suppress a couple of sqlalchemy warnings
    msgs = ['^Unicode type received non-unicode bind param value',
            "^Did not recognize type 'BIGINT' of column 'size'",
            "^Did not recognize type 'tsvector' of column 'search_vector'"
            ]
    for msg in msgs:
        warnings.filterwarnings('ignore', msg, sqlalchemy.exc.SAWarning)

    # load all CKAN plugins
    p.load_all(config)


# A mapping of config settings that can be overridden by env vars.
# Note: Do not remove the following lines, they are used in the docs
# Start CONFIG_FROM_ENV_VARS
CONFIG_FROM_ENV_VARS = {
    'sqlalchemy.url': 'CKAN_SQLALCHEMY_URL',
    'ckan.datastore.write_url': 'CKAN_DATASTORE_WRITE_URL',
    'ckan.datastore.read_url': 'CKAN_DATASTORE_READ_URL',
    'solr_url': 'CKAN_SOLR_URL',
    'ckan.site_id': 'CKAN_SITE_ID',
    'ckan.site_url': 'CKAN_SITE_URL',
    'ckan.storage_path': 'CKAN_STORAGE_PATH',
    'ckan.datapusher.url': 'CKAN_DATAPUSHER_URL',
    'smtp.server': 'CKAN_SMTP_SERVER',
    'smtp.starttls': 'CKAN_SMTP_STARTTLS',
    'smtp.user': 'CKAN_SMTP_USER',
    'smtp.password': 'CKAN_SMTP_PASSWORD',
    'smtp.mail_from': 'CKAN_SMTP_MAIL_FROM'
}
# End CONFIG_FROM_ENV_VARS


def update_config():
    ''' This code needs to be run when the config is changed to take those
    changes into account. It is called whenever a plugin is loaded as the
    plugin might have changed the config values (for instance it might
    change ckan.site_url) '''

    for plugin in p.PluginImplementations(p.IConfigurer):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)

    # Set whitelisted env vars on config object
    # This is set up before globals are initialized

    ckan_db = os.environ.get('CKAN_DB', None)
    if ckan_db:
        msg = 'Setting CKAN_DB as an env var is deprecated and will be' \
            ' removed in a future release. Use CKAN_SQLALCHEMY_URL instead.'
        log.warn(msg)
        config['sqlalchemy.url'] = ckan_db

    for option in CONFIG_FROM_ENV_VARS:
        from_env = os.environ.get(CONFIG_FROM_ENV_VARS[option], None)
        if from_env:
            config[option] = from_env

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    site_url = config.get('ckan.site_url', '')
    if not site_url:
        raise RuntimeError(
            'ckan.site_url is not configured and it must have a value.'
            ' Please amend your .ini file.')
    if not site_url.lower().startswith('http'):
        raise RuntimeError(
            'ckan.site_url should be a full URL, including the schema '
            '(http or https)')

    # Remove backslash from site_url if present
    config['ckan.site_url'] = config['ckan.site_url'].rstrip('/')

    ckan_host = config['ckan.host'] = urlparse(site_url).netloc
    if config.get('ckan.site_id') is None:
        if ':' in ckan_host:
            ckan_host, port = ckan_host.split(':')
        assert ckan_host, 'You need to configure ckan.site_url or ' \
                          'ckan.site_id for SOLR search-index rebuild to work.'
        config['ckan.site_id'] = ckan_host

    # ensure that a favicon has been set
    favicon = config.get('ckan.favicon', '/images/icons/ckan.ico')
    config['ckan.favicon'] = favicon

    # Init SOLR settings and check if the schema is compatible
    #from ckan.lib.search import SolrSettings, check_solr_schema_version

    # lib.search is imported here as we need the config enabled and parsed
    search.SolrSettings.init(config.get('solr_url'),
                             config.get('solr_user'),
                             config.get('solr_password'))
    search.check_solr_schema_version()

    routes_map = routing.make_map()
    config['routes.map'] = routes_map
    # The RoutesMiddleware needs its mapper updating if it exists
    if 'routes.middleware' in config:
        config['routes.middleware'].mapper = routes_map
    config['routes.named_routes'] = routing.named_routes
    config['pylons.app_globals'] = app_globals.app_globals
    # initialise the globals
    config['pylons.app_globals']._init()

    # add helper functions
    helpers = _Helpers(h)
    config['pylons.h'] = helpers

    # Translator (i18n)
    translator = Translator(pylons.translator)

    def template_loaded(template):
        translator.setup(template)

    # Markdown ignores the logger config, so to get rid of excessive
    # markdown debug messages in the log, set it to the level of the
    # root logger.
    logging.getLogger("MARKDOWN").setLevel(logging.getLogger().level)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # for postgresql we want to enforce utf-8
    sqlalchemy_url = config.get('sqlalchemy.url', '')
    if sqlalchemy_url.startswith('postgresql://'):
        extras = {'client_encoding': 'utf8'}
    else:
        extras = {}

    engine = sqlalchemy.engine_from_config(config, 'sqlalchemy.', **extras)

    if not model.meta.engine:
        model.init_model(engine)

    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)

    # clear other caches
    logic.clear_actions_cache()
    logic.clear_validators_cache()
    authz.clear_auth_functions_cache()

    # Here we create the site user if they are not already in the database
    try:
        logic.get_action('get_site_user')({'ignore_auth': True}, None)
    except (sqlalchemy.exc.ProgrammingError, sqlalchemy.exc.OperationalError):
        # (ProgrammingError for Postgres, OperationalError for SQLite)
        # The database is not initialised.  This is a bit dirty.  This occurs
        # when running tests.
        pass
    except sqlalchemy.exc.InternalError:
        # The database is not initialised.  Travis hits this
        pass
    # if an extension or our code does not finish
    # transaction properly db cli commands can fail
    model.Session.remove()
