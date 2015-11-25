# Copyright 2014 Tata Consultancy Services Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
###############################################################################
# This module provides the core api to communicate with the execution engine
###############################################################################
from oslo_config import cfg
from common import openstack
import inspect
import os
import sys

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
class API():
	def __init__(self, cfg):
		#read the credentials to get token from keystone
		self.user = cfg.CONF.openstack.user_id
		self.tenant = cfg.CONF.openstack.tenant
		self.password = cfg.CONF.openstack.password
		self.auth_url = cfg.CONF.openstack.auth_url
		self.host= cfg.CONF.openstack.host
		self.api_version = cfg.CONF.api_version
		#load the right catalog file for this mentioned API
		path = os.path.dirname(os.path.abspath(__file__))
		path2 = os.path.join(path,self.api_version)
		sys.path.append(path2)
		#remove the file name at the end and append to sys.path
	
        	#_catalog_ = __import__(self.api_version, globals(), locals(), [], -1)
        	_catalog_ = __import__('catalog', globals(), locals(), [], -1)
		self.catalogObj = _catalog_.catalog() #catalog.MandatoryParams()
		self.novaClient = openstack.NovaClient(cfg)
		self.neutronClient = openstack.NeutronClient(cfg)
		self.vnfsvc = openstack.VnfsvcClient(cfg)
		#connect to openstack
		try:
			self.__connect__()
		except:
			raise ValueError('Unknown Error: Unable to connect to Openstack')
		
	def __connect__(self):
		"""Connect to Keystone and get the endpoint list"""
		pass
		
	def __flavor_create__(self,**kwargs):
		"""create a new flavor in openstack"""

		self.validate_args(**kwargs)
		vcpus = kwargs["vcpus"]
		disk  = kwargs["disk"]
		name  = kwargs["name"]
		ram   = kwargs["ram"]
		is_public = kwargs["is_public"] if "is_public" in kwargs else "true"
		rx_tx = kwargs["rxtx_factor"] if "rxtx_factor" in kwargs else "1.0"
		#flavor_id = kwargs["id"] if "id" in kwargs else "auto"
		ephemeral = kwargs["OS-FLV-EXT-DATA:ephemeral"] if "OS-FLV-EXT-DATA:ephemeral" in kwargs else '0'
		swap = kwargs["swap"] if "swap" in kwargs else '0'

		return self.novaClient.flavor_create(vcpus,disk,name,ram,is_public,rx_tx,ephemeral,swap)

	def __flavor_delete__(self,flavorID):
		return self.novaClient.flavor_delete(flavorID)

	def __flavor_list__(self):
		return self.novaClient.flavor_list()
      
        def __create_serial_console__(self,**kwargs):
                name = kwargs["server"]
        	return self.novaClient.get_serial_console(name)

	def __create_network__(self,**kwargs):
		"""Create Network and subnet. If it already exists then retrieve and return the values"""
		self.validate_args(**kwargs)
		#first create the network
		existing_networks = self.neutronClient.get_networks()
		new_network = kwargs["network"]
		new_subnet_cidr = kwargs["cidr"]
		subnet_name = kwargs["subnet_name"]
                enable_dhcp = kwargs.get("enable_dhcp", True)

		netVal = {}
		subnetVal = {}
		net_id = None
		#check if the network with the same name exists
		if not any(network.get('name',None) == new_network for network in existing_networks['networks']) :
			#did not find the network. go ahead and create the network and subnet
			netVal = self.neutronClient.create_network(new_network)
			subnetVal = self.neutronClient.create_subnet(netVal['network']['id'],new_subnet_cidr,subnet_name,enable_dhcp)
                        netVal = netVal['network']
                        subnetVal = subnetVal['subnet']
			#return the dict with the network and subnet details
		else :
			#network name exists. get network id
			for network in existing_networks['networks']:
                                if new_network == network['name']:
					net_id = network['id']
					netVal = network
					break
			
			#check if the required subnet also exists
			existing_subnet = self.neutronClient.get_subnets()
			if not any(subnet.get('cidr',None) == new_subnet_cidr for subnet in existing_subnet['subnets']):
				#subnet needs to be created under this network
				subnetVal = self.neutronClient.create_subnet(net_id,new_subnet_cidr,subnet_name, enable_dhcp)
                                subnetVal = subnetVal['subnet']
			else :
				for subnet in existing_subnet['subnets']:
                                        #TOCHK: Dont use in for string comparisons
                                	#if new_subnet_cidr in subnet['cidr'] :
                                        if new_subnet_cidr == subnet['cidr']:
                                        	subnetVal = subnet
						break
		netVal['subnets'] = subnetVal
		return netVal

	def __create_router__(self,**kwargs):
		"""Create a router if does not exist. Attach an interface to this router"""
		self.validate_args(**kwargs)
		routerName = kwargs['router_name']
		external_network_name = kwargs['external_network_name'] if 'external_network_name' in kwargs else 'None'
		external_network_id = 'None'
		#fetch the network ID for this network
		extNetDetails = self.neutronClient.get_network_details(external_network_name)
		
		if 'networks' in extNetDetails :
			external_network_id = extNetDetails['networks'][0]['id'] #if multiple networks with same name exist use the first one
		else :
			raise Exception('invalid network. Cannot be attached to router')
		routerList = self.neutronClient.get_router(routerName)
		if not routerList['routers'] :
			return self.neutronClient.create_router(routerName,external_network_id)
		else :	
			return self.neutronClient.get_router_details(routerList['routers'][0]['id'])

        def __create_tap_service__(self, data):
            return self.neutronClient.create_tap_service(data)

        def __delete_tap_service__(self, svcID):
            return self.neutronClient.delete_tap_service(svcID)

        def __create_tap_flow__(self, data):
            return self.neutronClient.create_tap_flow(data)

        def __delete_tap_flow__(self, flowID):
            return self.neutronClient.delete_tap_flow(flowID)

        def __list_ports__(self):
            return self.neutronClient.list_ports()

	def __onboard__(self, serviceName='None',path='None'):
		return self.vnfsvc.template_upload(serviceName,path)

        def __register__(self, username, password, endpoint, templateid):
                return self.vnfsvc.register(username, password, endpoint, templateid)
	
        def __del_template__(self,templateID) :
		return self.vnfsvc.template_delete(templateID)	

	def __create_service__(self, serviceName,**kwargs):
		self.validate_args(**kwargs)
		return  self.vnfsvc.create_service(**kwargs)

        def __delete_service__(self, serviceId):
                return self.vnfsvc.delete_service(serviceId)

        def __start_diagnostics__(self, **kwargs):
                self.validate_args(**kwargs)
                return  self.vnfsvc.start_diagnostics(**kwargs)


	def validate_args(self,**kwargs):
		#get the name of the calling method
		callerName = inspect.stack()[1][3]
		#from loaded catalog module invoke the callerName method
		#for now we are validating only mandatory_params
		dict_args = getattr(self.catalogObj,callerName)('mandatory_params')
		valid_arg = list()
		#retrive the keywords for mandatory params 
		if 'mandatory_params' in dict_args.keys():
			mandatory_args = dict_args['mandatory_params']
			for each_arg in mandatory_args :
				if each_arg in kwargs :
					valid_arg.append(each_arg)
				else :
					raise
		return valid_arg


