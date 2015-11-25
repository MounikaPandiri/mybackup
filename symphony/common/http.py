import json
import requests
import logging.config
import subprocess
import tempfile

#from ConfigParser import SafeConfigParser
from oslo_config import cfg

#logging.config.fileConfig('logging.ini')

class HTTPClient(object):

    def __init__(self, service_type, cfg, endpoint_type='publicURL'):
        self.openstack_host = cfg.CONF.openstack.host
        self.auth_url = cfg.CONF.openstack.auth_url #'http://{0}:{1}'.format(self.openstack_host, '5000')
        self.tenant_name = cfg.CONF.openstack.tenant #parser.get('vnfsvc-test', 'tenantname')
        self.username = cfg.CONF.openstack.user_id  #parser.get('vnfsvc-test', 'username')
        self.password = cfg.CONF.openstack.password #parser.get('vnfsvc-test', 'password')
        self.service_type = service_type
        self.endpoint_type = endpoint_type
        self.endpoint_url = None
        self.headers = {'content-type': 'application/json',
                   'Accept': 'application/json'}
        self.auth=(self.username, self.password)
        self._authenticate_keystone()

    @property
    def tenant_id(self):
        return str(self.auth_tenant_id)

    def url_for(self):
        for service in self.service_catalog:
            if service['type'] == self.service_type:
                return service['endpoints'][0][self.endpoint_type]


    def _extract_service_catalog(self, body):
        """Set the client's service catalog from the response data."""
        self.service_catalog = body['access']['serviceCatalog']
        self.auth_token = body['access']['token']['id']
        self.auth_tenant_id = body['access']['token']['tenant']['id']
        self.auth_user_id = body['access']['user']['id']

        if not self.endpoint_url:
            self.endpoint_url = self.url_for()

    def _authenticate_keystone(self):
        creds = {'username': self.username,
                 'password': self.password}

        body = {'auth': {'passwordCredentials': creds,
                         'tenantName': self.tenant_name, }, }

        if self.auth_url is None:
            print "Authentication Failure: Authentication Server URL not found"

        token_url = "v2.0/tokens"
        resp_body = self.do_request(requests.post,
                                          token_url,
                                          data=body,
                                          method='keystone')
        if resp_body:
            try:
                resp_body = resp_body
            except ValueError:
                pass
        else:
            resp_body = None
        self._extract_service_catalog(resp_body)
    
    def do_request(self,
                   requests_method,
                   uri,
                   data=None,
                   params=None,
                   headers=None,
                   auth=None,
                   expected_status_code=200,
                   method=None):
        body = json.dumps(data) if data is not None else None
        if method == "keystone":
            request_url = '{0}{1}'.format(self.auth_url, uri)
            headers = self.headers
        else:
            #if self.expired():
            self.headers['X-Auth-Token'] = self.auth_token
            headers = self.headers
            auth = self.auth
            request_url = '{0}{1}'.format(self.endpoint_url, uri)
       
        response = requests_method(request_url,
                                   data=body,
                                   params=params,
                                   headers=headers,
                                   auth=auth)
        try:
            return response.json()
        except:
            return response

    def get(self, uri, params=None,
            _include=None, expected_status_code=200):
        if _include:
            fields = ','.join(_include)
            if not params:
                params = {}
            params['_include'] = fields

        return self.do_request(requests.get,
                               uri,
                               params=params,
                               expected_status_code=expected_status_code)

    def put(self, uri, data=None, params=None, expected_status_code=200):
        return self.do_request(requests.put,
                               uri,
                               data=data,
                               params=params,
                               expected_status_code=expected_status_code)

    def post(self, uri, data=None, params=None,
             expected_status_code=200):
        return self.do_request(requests.post,
                               uri,
                               data=data,
                               params=params,
                               expected_status_code=expected_status_code)

    def delete(self, uri, data=None, params=None,
               expected_status_code=200):
        return self.do_request(requests.delete,
                               uri,
                               data=data,
                               params=params,
                               expected_status_code=expected_status_code)
