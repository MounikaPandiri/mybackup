import json
import yaml
import requests
import logging.config
import subprocess
import tempfile
import zipfile
import sys,os

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
from http import HTTPClient
from oslo_config import cfg
from common import utils
class NovaClient(HTTPClient):

    """Nova's management client."""

    def __init__(self, cfg):
        self.service_type = 'compute'
        super(NovaClient, self).__init__(self.service_type, cfg)

    def get_servers(self):
        res = self.get('/servers/detail')
        return res

    def get_interfaces(self, servier_id):
        return self.get('/servers/' + server_id + '/os-interface')

    def get_server(self, server_name):
        server_details = self.get('/servers?name=' + server_name)
        server_id = server_details['servers'][0]['id']
        return self.get('/servers/' + server_id)

    def get_server_details(self, server_id):
        server_details = self.get('/servers/' + server_id)
        return server_details

    def flavor_show(self, flavor_id):
        return self.get('/flavors/' + flavor_id)

    def flavor_list(self):
        return self.get('/flavors/detail')

    def create_server(self, data):
        server_details = self.post('/servers',data=data)
        return server_details

    def delete_server(self, server_id):
        return self.delete('/servers/' + server_id)

    def flavor_create(self, vcpus,disk,name,ram,is_public='true',rx_tx='0',ephemeral='0',swap=''):
	"""Add a new flavor to openstack"""
	#Extract the required arguments into data
	data = {"flavor": {
			"vcpus":vcpus,
			"disk":disk,
			"name":name,
 		        "os-flavor-access:is_public": is_public, 
			"rxtx_factor": rx_tx, 
			"OS-FLV-EXT-DATA:ephemeral": ephemeral, 
			"ram": ram, 
			#"id": 'auto', 
			"swap": swap}
		}			
	return self.post('/flavors',data=data)

    def flavor_delete(self,flavorID):
	return self.delete('/flavors/'+flavorID)

    def get_serial_console(self, server_name):
        """Gets New Serial Console"""
        data = {"os-getSerialConsole": {
                       "type": "serial"
                   }
               }
        server_details = self.get('/servers?name=' + server_name)
        if not server_details['servers']: 
            return None
        server_id = server_details['servers'][0]['id']
        return self.post('/servers/'+server_id+'/action',data=data)

class NeutronClient(HTTPClient):

    """Neutron's management client."""

    def __init__(self, cfg):
        self.service_type = 'network'
        super(NeutronClient, self).__init__(self.service_type, cfg)

    def create_network(self, network):
        data = {'network': {'name': network}}
        return self.post('/v2.0/networks', data=data)

    def create_subnet(self, network_id, cidr, name=None, enable_dhcp=True):
        if name:
            data = {"subnet": {"network_id": network_id, "ip_version": 4, "cidr": cidr, "name": name, "enable_dhcp": enable_dhcp}}
        else:
            data = {"subnet": {"network_id": network_id, "ip_version": 4, "cidr": cidr, "enable_dhcp": enable_dhcp}}
        return self.post('/v2.0/subnets', data=data)

    def create_router(self, router_name, external_network_id):
        if external_network_id == 'None':
            data = {"router": {"name": router_name}}
        else:
            data = {"router": {"name": router_name, "external_gateway_info": {"network_id": external_network_id}}}
        return self.post('/v2.0/routers', data=data)

    def add_router_interface(self, router_id, subnet_id):
        data = {"subnet_id": subnet_id}
        return self.put('/v2.0/routers/'+router_id+'/add_router_interface', data=data)

    def create_networks(self, networks):
        network_resps = dict()
        for network in networks:
            temp = self.create_network(network)
            network_resps[temp['network']['id']] = temp['network']
        return network_resps

    def create_subnets(self, subnets):
        subnet_resps = dict()
        for subnet in subnets.keys():
            temp = self.create_subnet(subnet, subnets[subnet])
            subnet_resps[temp['subnet']['id']] = temp['subnet']
        return subnet_resps

    def create_routers(self, router_infos):
        router_resps = dict()
        for router_info in router_infos.keys():
            temp = self.create_router(router_info, router_infos[router_info])
            router_resps[temp['router']['id']] = temp['router']
        return router_resps

    def create_router_interfaces(self, router_id, subnets):
        interface_resps = dict()
        for subnet in subnets:
            temp = self.add_router_interface(router_id, subnet)
            interface_resps[temp['port_id']] = temp
        return interface_resps
 
    def get_networks(self):
        return self.get('/v2.0/networks')

    def get_subnets(self):
        return self.get('/v2.0/subnets')

    def get_ports(self, server_id):
        return self.get('/v2.0/ports.json?device_id=' + server_id)

    def get_routers(self):
        return self.get('/v2.0/routers')

    def get_router(self,name):
        return self.get('/v2.0/routers.json?fields=id&name='+name)

    def get_router_details(self,id):
	return self.get('v2.0/routers/'+id)

    def get_subnet_detail(self, subnet_id):
        return self.get('/v2.0/subnets/' + subnet_id)

    def get_network_details(self, network_name):
        return self.get('/v2.0/networks.json?fields=id&name=' + network_name)

    def create_tap_service(self, data):
        return self.post('/v2.0/taas/tap-services', data=data)

    def create_tap_flow(self, data):
        return self.post('/v2.0/taas/tap-flows', data=data)

    def list_ports(self):
        return self.get('/v2.0/ports.json')

    def delete_tap_flow(self, tapFlowid):
        return self.delete('/v2.0/taas/tap-flows/'+tapFlowid)

    def delete_tap_service(self, tapSvcid):
        return self.delete(' /v2.0/taas/tap-services/'+tapSvcid)

class VnfsvcClient(HTTPClient):

    """ Vnfsvc's management client. """

    def __init__(self, cfg):
        self.service_type = 'vnfservice'
        super(VnfsvcClient, self).__init__(self.service_type, cfg)

    def create_service(self, name, qos, attributes, description=None):
        data = {"service": {"name": name, "quality_of_service": qos, "attributes": attributes}}
        if description:
            data["service"]["description"] = description
        return self.post('/v1.0/services', data=data)

    def start_diagnostics(self, **kwargs):
        data = {'diagnostic': {'nsd_id': kwargs['nsd_id'], 'files_dict': str(kwargs['files'])}}
        return self.post('/v1.0/diagnostics.json', data=data)

    def get_service(self, service):
        return self.get('/v1.0/services/'+service)
 
    def delete_service(self, service):
        return self.delete('/v1.0/services/'+service+".json")

    def monitor_kpi(self, nsd):
        vnfm_details = self.get('/v1.0/services.json', headers=headers)
 
        monitor_result = self.get('/v1.0/metrics/' + nsd + '.json')
        try:
            return monitor_result['metric']['kpi']
        except:
            return 0
    """
    def start_diagnostics(self, nsd, vdus=None):
        if isinstance(vdus, list):
             vdu_data = vdus
        else:
             vdu_data = {}
        data = {"diagnostic": {"vdus": vdu_data, "nsd_id": nsd}}
        return self.post('/v1.0/diagnostics.json', data=data)
    """
    def stop_diagnostics(self, nsd):
        " Stops the diganostics on specified nsd."
        return self.delete('/v1.0/diagnostics/'+nsd+'.json')

    def get_services(self, stack_id):
        "Returns the Network Service details."
        pass
        #service_dict = self._client.get('/v1.0/services.json', headers=headers,
        #                                auth=(self.username, self.password))

        #return self._heat_client.get_stack_service_resource_id(stack_id)

    def scale_in(self, nsd, policy):
        " Scales the Network Service."
        data = {"scale": {
                   "policy_name": policy, 
                   "nsd_id": nsd
                   }
               }
        return self.post('/v1.0/scales.json', data=data)

    def template_upload(self, name, files):
        params = {
            "template": {
                "name": name,
                "files": {}
            }
        }
        newpath = tempfile.mkdtemp()
        with zipfile.ZipFile(files) as zipfi:
             zipfi.extractall(newpath)

        for filename in zipfi.namelist():
            params['template']['files'][filename] = json.dumps(utils.ordered_load(open(os.path.join(newpath, filename),'r'),\
								yaml.SafeLoader))
        result  = self.post('/v1.0/templates.json', data=params)
        return result

    def template_delete(self, template_id):
        result  = self.delete('/v1.0/templates/'+template_id+'.json')
        return result

    def register(self, username, password, endpoint, templateid):
        params = {
            "register": {
              "user":{
                "username": username,
                "password": password,
                "endpoints": endpoint,
                "template_id": templateid
                }
              }
          }
        result = self.post('/v1.0/registers.json', data=params)
        return result
