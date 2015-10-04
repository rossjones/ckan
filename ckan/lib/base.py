"""The base Controller API

Provides the BaseController class for subclassing.
"""
import logging
import time

from paste.deploy.converters import asbool
from pylons import cache, config
from pylons.controllers import WSGIController
from pylons.controllers.util import abort as _abort
from pylons.controllers.util import redirect_to, redirect
from pylons.decorators import jsonify
from pylons.i18n import N_, gettext, ngettext
from pylons.templating import cached_template, pylons_globals
from genshi.template import MarkupTemplate
from genshi.template.text import NewTextTemplate
from webhelpers.html import literal

import ckan.exceptions
import ckan
import ckan.lib.i18n as i18n
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.plugins as p
import ckan.model as model
import ckan.lib.maintain as maintain

# These imports are for legacy usages and will be removed soon these should
# be imported directly from ckan.common for internal ckan code and via the
# plugins.toolkit for extensions.
from ckan.common import json, _, ungettext, c, g, request, response

log = logging.getLogger(__name__)

PAGINATE_ITEMS_PER_PAGE = 50

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

ALLOWED_FIELDSET_PARAMS = ['package_form', 'restrict']


def abort(status_code=None, detail='', headers=None, comment=None):
    '''Abort the current request immediately by returning an HTTP exception.

    This is a wrapper for :py:func:`pylons.controllers.util.abort` that adds
    some CKAN custom behavior, including allowing
    :py:class:`~ckan.plugins.interfaces.IAuthenticator` plugins to alter the
    abort response, and showing flash messages in the web interface.

    '''
    if status_code == 401:
        # Allow IAuthenticator plugins to alter the abort
        for item in p.PluginImplementations(p.IAuthenticator):
            result = item.abort(status_code, detail, headers, comment)
            (status_code, detail, headers, comment) = result

    if detail and status_code != 503:
        h.flash_error(detail)
    # #1267 Convert detail to plain text, since WebOb 0.9.7.1 (which comes
    # with Lucid) causes an exception when unicode is received.
    detail = detail.encode('utf8')
    return _abort(status_code=status_code,
                  detail=detail,
                  headers=headers,
                  comment=comment)


def render_jinja2(template_name, extra_vars):
    env = config['pylons.app_globals'].jinja_env
    template = env.get_template(template_name)
    return template.render(**extra_vars)


def render(template_name, extra_vars=None, cache_key=None, cache_type=None,
           cache_expire=None, method='xhtml', loader_class=MarkupTemplate,
           cache_force=None, renderer=None):
    '''Render a template and return the output.

    This is CKAN's main template rendering function.

    .. todo::

       Document the parameters of :py:func:`ckan.plugins.toolkit.render`.

    '''
    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())
        globs['actions'] = model.Action

        # Using pylons.url() directly destroys the localisation stuff so
        # we remove it so any bad templates crash and burn
        del globs['url']

        try:
            template_path, template_type = render_.template_info(template_name)
        except render_.TemplateNotFound:
            raise

        log.debug('rendering %s [%s]' % (template_path, template_type))
        if config.get('debug'):
            context_vars = globs.get('c')
            if context_vars:
                context_vars = dir(context_vars)
            debug_info = {'template_name': template_name,
                          'template_path': template_path,
                          'template_type': template_type,
                          'vars': globs,
                          'c_vars': context_vars,
                          'renderer': renderer}
            if 'CKAN_DEBUG_INFO' not in request.environ:
                request.environ['CKAN_DEBUG_INFO'] = []
            request.environ['CKAN_DEBUG_INFO'].append(debug_info)

        # Jinja2 templates
        if template_type == 'jinja2':
            # We don't want to have the config in templates it should be
            # accessed via g (app_globals) as this gives us flexability such
            # as changing via database settings.
            del globs['config']
            # TODO should we raise error if genshi filters??
            return render_jinja2(template_name, globs)

        # Genshi templates
        template = globs['app_globals'].genshi_loader.load(
            template_name.encode('utf-8'), cls=loader_class
        )
        stream = template.generate(**globs)

        if loader_class == NewTextTemplate:
            return literal(stream.render(method="text", encoding=None))

        return literal(stream.render(method=method, encoding=None,
                                     strip_whitespace=True))

    if 'Pragma' in response.headers:
        del response.headers["Pragma"]

    ## Caching Logic
    allow_cache = True
    # Force cache or not if explicit.
    if cache_force is not None:
        allow_cache = cache_force
    # Don't cache if based on a non-cachable template used in this.
    elif request.environ.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have set the __no_cache__ param in the query string.
    elif request.params.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have extra vars containing data.
    elif extra_vars:
        for k, v in extra_vars.iteritems():
            allow_cache = False
            break
    # Record cachability for the page cache if enabled
    request.environ['CKAN_PAGE_CACHABLE'] = allow_cache

    if allow_cache:
        response.headers["Cache-Control"] = "public"
        try:
            cache_expire = int(config.get('ckan.cache_expires', 0))
            response.headers["Cache-Control"] += \
                ", max-age=%s, must-revalidate" % cache_expire
        except ValueError:
            pass
    else:
        # We do not want caching.
        response.headers["Cache-Control"] = "private"
        # Prevent any further rendering from being cached.
        request.environ['__no_cache__'] = True

    # Render Time :)
    try:
        return cached_template(template_name, render_template,
                               loader_class=loader_class)
    except ckan.exceptions.CkanUrlException, e:
        raise ckan.exceptions.CkanUrlException(
            '\nAn Exception has been raised for template %s\n%s' %
            (template_name, e.message))
    except render_.TemplateNotFound:
        raise


class ValidationException(Exception):
    pass


class BaseController(WSGIController):
    '''Base class for CKAN controller classes to inherit from.

    '''
    repo = model.repo
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        c.__timer = time.time()
        c.__version__ = ckan.__version__
        app_globals.app_globals._check_uptodate()

        self._identify_user()

        i18n.handle_request(request, c)

        maintain.deprecate_context_item(
            'new_activities',
            'Use `h.new_activities` instead.')

    def _identify_user(self):
        '''Try to identify the user
        If the user is identified then:
          c.user = user name (unicode)
          c.userobj = user object
          c.author = user name
        otherwise:
          c.user = None
          c.userobj = None
          c.author = user's IP address (unicode)'''
        # see if it was proxied first
        c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if not c.remote_addr:
            c.remote_addr = request.environ.get('REMOTE_ADDR',
                                                'Unknown IP Address')

        # Authentication plugins get a chance to run here break as soon as a
        # user is identified.
        authenticators = p.PluginImplementations(p.IAuthenticator)
        if authenticators:
            for item in authenticators:
                item.identify()
                if c.user:
                    break

        # We haven't identified the user so try the default methods
        if not c.user:
            self._identify_user_default()

        # If we have a user but not the userobj let's get the userobj.  This
        # means that IAuthenticator extensions do not need to access the user
        # model directly.
        if c.user and not c.userobj:
            c.userobj = model.User.by_name(c.user)

        # general settings
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr
        c.author = unicode(c.author)

    def _identify_user_default(self):
        '''
        Identifies the user using one method:
            For API calls they may set a header with an API key.
        '''
        c.userobj = self._get_user_for_apikey()
        if c.userobj is not None:
            c.user = c.userobj.name

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        try:
            res = WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

        return res

    def __after__(self, action, **params):
        # Do we have CORS settings in config?
        if config.get('ckan.cors.origin_allow_all') \
                and request.headers.get('Origin'):
            self._set_cors()
        r_time = time.time() - c.__timer
        url = request.environ['CKAN_CURRENT_URL'].split('?')[0]
        log.info(' %s render time %.3f seconds' % (url, r_time))

    def _set_cors(self):
        '''
        Set up Access Control Allow headers if either origin_allow_all is
        True, or the request Origin is in the origin_whitelist.
        '''
        cors_origin_allowed = None
        if asbool(config.get('ckan.cors.origin_allow_all')):
            cors_origin_allowed = "*"
        elif config.get('ckan.cors.origin_whitelist') and \
                request.headers.get('Origin') \
                in config['ckan.cors.origin_whitelist'].split(" "):
            # set var to the origin to allow it.
            cors_origin_allowed = request.headers.get('Origin')

        if cors_origin_allowed is not None:
            response.headers['Access-Control-Allow-Origin'] = \
                cors_origin_allowed
            response.headers['Access-Control-Allow-Methods'] = \
                "POST, PUT, GET, DELETE, OPTIONS"
            response.headers['Access-Control-Allow-Headers'] = \
                "X-CKAN-API-KEY, Authorization, Content-Type"

    def _get_user_for_apikey(self):
        apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
                                        APIKEY_HEADER_NAME_DEFAULT)
        apikey = request.headers.get(apikey_header_name, '')
        if not apikey:
            apikey = request.environ.get(apikey_header_name, '')
        if not apikey:
            # For misunderstanding old documentation (now fixed).
            apikey = request.environ.get('HTTP_AUTHORIZATION', '')
        if not apikey:
            apikey = request.environ.get('Authorization', '')
            # Forget HTTP Auth credentials (they have spaces).
            if ' ' in apikey:
                apikey = ''
        if not apikey:
            return None
        self.log.debug("Received API Key: %s" % apikey)
        apikey = unicode(apikey)
        query = model.Session.query(model.User)
        user = query.filter_by(apikey=apikey).first()
        return user

    def _get_page_number(self, params, key='page', default=1):
        """
        Returns the page number from the provided params after
        verifies that it is an integer.

        If it fails it will abort the request with a 400 error
        """
        p = params.get(key, default)

        try:
            p = int(p)
            if p < 1:
                raise ValueError("Negative number not allowed")
        except ValueError, e:
            abort(400, ('"page" parameter must be a positive integer'))

        return p


# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_')
           or __name == '_']
