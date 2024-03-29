# Copyright 2014 Tata Consultancy Services Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg
import routes as routes_mapper
import six.moves.urllib.parse as urlparse
import webob
import webob.dec
import webob.exc

from vnfsvc.api.v2 import attributes
from vnfsvc.api.v2 import base
from vnfsvc import manager
from vnfsvc.openstack.common import log as logging
from vnfsvc import wsgi
from vnfsvc.api.v2 import vnf

LOG = logging.getLogger(__name__)

RESOURCES = {'vnf': 'vnfs',
             'vnf_template': 'vnf_templates',
             'connection': 'connections',
             'service': 'services',
             'template': 'templates',
             'scale': 'scales',
             'metric': 'metrics',
             'diagnostic': 'diagnostics',
             'configuration': 'configurations',
             'register': 'registers',
             'dumpxml': 'dumpxmls',
             'mount': 'mounts',
             'log_file': 'log_files'}
SUB_RESOURCES = {}
COLLECTION_ACTIONS = ['index', 'create']
MEMBER_ACTIONS = ['show', 'update', 'delete']
REQUIREMENTS = {'id': attributes.UUID_PATTERN, 'format': 'xml|json'}


class Index(wsgi.Application):
    def __init__(self, resources):
        self.resources = resources

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        metadata = {'application/xml': {'attributes': {
                    'resource': ['name', 'collection'],
                    'link': ['href', 'rel']}}}

        layout = []
        for name, collection in self.resources.iteritems():
            href = urlparse.urljoin(req.path_url, collection)
            resource = {'name': name,
                        'collection': collection,
                        'links': [{'rel': 'self',
                                   'href': href}]}
            layout.append(resource)
        response = dict(resources=layout)
        content_type = req.best_match_content_type()
        body = wsgi.Serializer(metadata=metadata).serialize(response,
                                                            content_type)
        return webob.Response(body=body, content_type=content_type)


class APIRouter(wsgi.Router):

    @classmethod
    def factory(cls, global_config, **local_config):
        return cls(**local_config)

    def __init__(self, **local_config):
        mapper = routes_mapper.Mapper()
        plugin = manager.VNFSvcManager.get_plugin()

        col_kwargs = dict(collection_actions=COLLECTION_ACTIONS,
                          member_actions=MEMBER_ACTIONS)

        def _map_resource(collection, resource, params, parent=None):
            allow_bulk = cfg.CONF.allow_bulk
            allow_pagination = cfg.CONF.allow_pagination
            allow_sorting = cfg.CONF.allow_sorting
            controller = base.create_resource(
                collection, resource, plugin, params, allow_bulk=allow_bulk,
                parent=parent, allow_pagination=allow_pagination,
                allow_sorting=allow_sorting)
            path_prefix = None
            if parent:
                path_prefix = "/%s/{%s_id}/%s" % (parent['collection_name'],
                                                  parent['member_name'],
                                                  collection)
            mapper_kwargs = dict(controller=controller,
                                 requirements=REQUIREMENTS,
                                 path_prefix=path_prefix,
                                 **col_kwargs)
            return mapper.collection(collection, resource,
                                     **mapper_kwargs)

        mapper.connect('index', '/', controller=Index(RESOURCES))
        for resource in RESOURCES:
            _map_resource(RESOURCES[resource], resource,
                          vnf.RESOURCE_ATTRIBUTE_MAP.get(
                              RESOURCES[resource], dict()))


        super(APIRouter, self).__init__(mapper)
