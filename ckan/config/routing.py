"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/

"""
import re

from pylons import config
from routes.mapper import SubMapper, Mapper as _Mapper

import ckan.plugins as p

named_routes = {}


class Mapper(_Mapper):
    ''' This Mapper allows us to intercept the connect calls used by routes
    so that we can collect named routes and later use them to create links
    via some helper functions like build_nav(). '''

    def connect(self, *args, **kw):
        '''Connect a new route, storing any named routes for later.

        This custom connect() method wraps the standard connect() method,
        and additionally saves any named routes that are connected in a dict
        ckan.routing.named_routes, which ends up being accessible via the
        Pylons config as config['routes.named_routes'].

        Also takes some additional params:

        :param ckan_icon: name of the icon to be associated with this route,
            e.g. 'group', 'time'
        :type ckan_icon: string
        :param highlight_actions: space-separated list of controller actions
            that should be treated as the same as this named route for menu
            highlighting purposes, e.g. 'index search'
        :type highlight_actions: string

        '''
        ckan_icon = kw.pop('ckan_icon', None)
        highlight_actions = kw.pop('highlight_actions', kw.get('action', ''))
        out = _Mapper.connect(self, *args, **kw)
        if len(args) == 1 or args[0].startswith('_redirect_'):
            return out
        # we have a named route
        needed = []
        matches = re.findall('\{([^:}]*)(\}|:)', args[1])
        for match in matches:
            needed.append(match[0])
        route_data = {
            'icon': ckan_icon,
            # needed lists the names of the parameters that need defining
            # for the route to be generated
            'needed': needed,
            'controller': kw.get('controller'),
            'action': kw.get('action', ''),
            'highlight_actions': highlight_actions
        }
        named_routes[args[0]] = route_data
        return out


def make_map():
    """Create, configure and return the routes Mapper"""
    # import controllers here rather than at root level because
    # pylons config is initialised by this point.

    # Helpers to reduce code clutter
    GET = dict(method=['GET'])
    PUT = dict(method=['PUT'])
    POST = dict(method=['POST'])
    DELETE = dict(method=['DELETE'])
    GET_POST = dict(method=['GET', 'POST'])
    PUT_POST = dict(method=['PUT', 'POST'])
    PUT_POST_DELETE = dict(method=['PUT', 'POST', 'DELETE'])
    OPTIONS = dict(method=['OPTIONS'])

    import ckan.lib.plugins as lib_plugins
    lib_plugins.reset_package_plugins()

    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.explicit = True

    # CKAN API versioned.
    register_list = [
        'package',
        'dataset',
        'resource',
        'tag',
        'group',
        'related',
        'revision',
        'licenses',
        'rating',
        'user',
        'activity'
    ]
    register_list_str = '|'.join(register_list)

    # /api ver 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/3|}',
                   ver='/3') as m:
        m.connect('/action/{logic_function}', action='action',
                  conditions=GET_POST)

    # /api ver 1, 2, 3 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|/3|}',
                   ver='/1') as m:
        m.connect('', action='get_api')
        m.connect('/search/{register}', action='search')

    # /api ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1') as m:
        m.connect('/tag_counts', action='tag_counts')
        m.connect('/rest', action='index')
        m.connect('/qos/throughput/', action='throughput', conditions=GET)

    # /api/rest ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1', requirements=dict(register=register_list_str)
                   ) as m:

        m.connect('/rest/{register}', action='list', conditions=GET)
        m.connect('/rest/{register}', action='create', conditions=POST)
        m.connect('/rest/{register}/{id}', action='show', conditions=GET)
        m.connect('/rest/{register}/{id}', action='update', conditions=PUT)
        m.connect('/rest/{register}/{id}', action='update', conditions=POST)
        m.connect('/rest/{register}/{id}', action='delete', conditions=DELETE)
        m.connect('/rest/{register}/{id}/:subregister', action='list',
                  conditions=GET)
        m.connect('/rest/{register}/{id}/:subregister', action='create',
                  conditions=POST)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='create',
                  conditions=POST)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='show',
                  conditions=GET)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='update',
                  conditions=PUT)
        m.connect('/rest/{register}/{id}/:subregister/{id2}', action='delete',
                  conditions=DELETE)

    # /api/util ver 1, 2 or none
    with SubMapper(map, controller='api', path_prefix='/api{ver:/1|/2|}',
                   ver='/1') as m:
        m.connect('/util/user/autocomplete', action='user_autocomplete')
        m.connect('/util/is_slug_valid', action='is_slug_valid',
                  conditions=GET)
        m.connect('/util/dataset/autocomplete', action='dataset_autocomplete',
                  conditions=GET)
        m.connect('/util/tag/autocomplete', action='tag_autocomplete',
                  conditions=GET)
        m.connect('/util/resource/format_autocomplete',
                  action='format_autocomplete', conditions=GET)
        m.connect('/util/resource/format_icon',
                  action='format_icon', conditions=GET)
        m.connect('/util/group/autocomplete', action='group_autocomplete')
        m.connect('/util/organization/autocomplete', action='organization_autocomplete',
                  conditions=GET)
        m.connect('/util/markdown', action='markdown')
        m.connect('/util/dataset/munge_name', action='munge_package_name')
        m.connect('/util/dataset/munge_title_to_name',
                  action='munge_title_to_package_name')
        m.connect('/util/tag/munge', action='munge_tag')
        m.connect('/util/status', action='status')
        m.connect('/util/snippet/{snippet_path:.*}', action='snippet')
        m.connect('/i18n/{lang}', action='i18n_js_translations')

    ###########
    ## /END API
    ###########

    # Storage routes
    with SubMapper(map, controller='ckan.controllers.storage:StorageAPIController') as m:
        m.connect('storage_api', '/api/storage', action='index')
        m.connect('storage_api_set_metadata', '/api/storage/metadata/{label:.*}',
                  action='set_metadata', conditions=PUT_POST)
        m.connect('storage_api_get_metadata', '/api/storage/metadata/{label:.*}',
                  action='get_metadata', conditions=GET)
        m.connect('storage_api_auth_request',
                  '/api/storage/auth/request/{label:.*}',
                  action='auth_request')
        m.connect('storage_api_auth_form',
                  '/api/storage/auth/form/{label:.*}',
                  action='auth_form')

    with SubMapper(map, controller='util') as m:
        m.connect('/i18n/strings_{lang}.js', action='i18n_js_strings')


    map.redirect('/*(url)/', '/{url}',
                 _redirect_code='301 Moved Permanently')
    return map
