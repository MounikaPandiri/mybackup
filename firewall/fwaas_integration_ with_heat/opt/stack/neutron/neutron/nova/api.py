# Copyright 2012 (c) Tata Consultancy Services Limited
# All Rights Reserved
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
#
# @author: anirudh vedantam, anirudh.vedantam@tcs.com, Tata Consultancy Services Limited

from novaclient.v1_1 import client as nova_client
from nova.openstack.common import importutils
from oslo.config import cfg

from neutron.openstack.common.gettextutils import _
from neutron.openstack.common import local
from neutron.openstack.common import log as logging
from neutron import manager
from neutron.api.v2 import attributes
import xml.etree.ElementTree as ET
import os

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_novaclient_opts = [#cfg.StrOpt('nova_url',
                    #       default='http://127.0.0.1:8774',
                    #       help='The full class name of the '
                    #            'network API class to use'),
                    cfg.StrOpt('nova_url_timeout',
                           default='30',
                           help='The full class name of the '
                                'network API class to use'), 
                    cfg.StrOpt('nova_url_timeout',
                           default='30',
                           help='The full class name of the '
                                'network API class to use'),
                    cfg.BoolOpt('nova_api_insecure',
                           default=False,
                           help='The full class name of the '
                                'network API class to use'),
                    cfg.StrOpt('nova_ca_certificates_file',
                           help='The full class name of the '
                                'network API class to use'),
                    cfg.StrOpt('nova_admin_user_fw',
                           default='admin',
                           help='The full class name of the '
                                'network API class to use'),
                    #cfg.StrOpt('nova_admin_password',
                    #       default='openstack',
                    #       secret=True,
                    #       help='The full class name of the '
                    #            'network API class to use'),
                    #cfg.StrOpt('nova_admin_tenant_id',
                    #       help='Tenant id for connecting to '
                    #            'neutron in admin context'),
                    cfg.StrOpt('nova_admin_tenant_name',
                           help='DEPRECATED: Tenant name for '
                                'connecting to neutron in admin context.'
                                'This option is deprecated.  Please use '
                                'neutron_admin_tenant_id instead. '
                                'Note that with Keystone '
                                'V3 tenant names may not be unique.'),
                    #cfg.StrOpt('nova_region_name',
                    #       help='Region name for connecting to neutron '
                    #            'in admin context'),
                    #cfg.StrOpt('nova_admin_auth_url',
                    #       default='http://localhost:5000/v2.0',
                    #       help='Authorization URL for connecting to neutron in admin '
                    #            'context'),
                    cfg.StrOpt('nova_auth_strategy',
                           default='keystone',
                           help='Authorization strategy for connecting to '
                                'neutron in admin context'),
]

FWapplianceOpts = [
    cfg.StrOpt(
        'Gateway_Net',
        help=_("IDs of the Internal Networks-that in the Trusted Zone")),
    cfg.StrOpt(
        'Net',
        help=_("ID of the External Network-that in the Untrusted Zone")),
    cfg.StrOpt(
        'Image',
        help=_("Image ID for the Firewall VM")),
    cfg.StrOpt(
        'Name',
        help=_("Name for the Firewall VM")),
    cfg.StrOpt(
        'Flavor',
        help=_("Flavor ID that would be sufficient for the Image provied for Firewall VM")),
]

cfg.CONF.register_opts(FWapplianceOpts, 'fw_appliance')

cfg.CONF.register_opts(_novaclient_opts)

class API():

   def __init__(self):
       pass

   def _get_client(self, context, token=None):

       params = {
        'timeout': CONF.nova_url_timeout,
        'insecure': CONF.nova_api_insecure,
        'cacert': CONF.nova_ca_certificates_file,
       }

       if token:
           params['token'] = token
           params['auth_strategy'] = None
       else:
           params['username'] = CONF.nova_admin_user_fw
           params['project_id'] = CONF.nova_admin_tenant_name      #context.tenant_id 
                                                                   #** Don't know whether this is deprecated 
           params['api_key'] = CONF.nova_admin_password
           params['auth_url'] = CONF.nova_admin_auth_url
           params['auth_system'] = CONF.nova_auth_strategy
       return nova_client.Client(**params)

   def get_client(self, context, admin=False):

    # NOTE(anirudh): The nova client is created by the supplied arguments
    #                in the neutron.conf file.
    local.strong_store.nova_client = self._get_client(context, token=None)
    return local.strong_store.nova_client

   def get_servers(self, context):
       nova_client = self.get_client(context)
       return nova_client.servers.list()

   def get_server(self, context, id):
       nova_client = self.get_client(context)
       return nova_client.servers.get(id)

   def delete_server(self, context, id):
       nova_client = self.get_client(context)
       return nova_client.servers.delete(id)

   def launch_fw_vm(self, context,source_addr,dest_addr,instance_name):
        nova_client = self.get_client(context)
        test_plugin1 = manager.NeutronManager.get_plugin()
        try:
                path=os.environ['HOME']+"/"+'vyatta.xml'
                #path='/etc/neutron/xml/'+instance_name+'.xml'
                tree=ET.parse(path)
                root=tree.getroot()
        except (IOError):
                """File not found error"""
                raise exceptions.CommandError("File not found")

        for child in root :
          if child.tag=='net-name':
            mgnt_network_name=child.text
          if child.tag=='name':
            server_instance_name=child.text
          if child.tag=='image-id':
            image_id=child.text
          if child.tag=='flavor-id':
            flavor_id=child.text
          if child.tag=='subnet-name':
            mgnt_subnet_name=child.text 
          if child.tag=='subnet-cidr':
            mgnt_subnet_cidr=child.text

        #mgnt_network=test_plugin1.create_network(context,{'network':{'name':mgnt_network_name,'admin_state_up':True,'shared':False}})
        #   /opt/stack/neutron/neutron/plugins/openvswitch/ovs_neutron_plugin.py

        #gateway_ip = attributes.ATTR_NOT_SPECIFIED
        #allocation_pools = attributes.ATTR_NOT_SPECIFIED
        #dns_nameservers = attributes.ATTR_NOT_SPECIFIED
        #host_routes= attributes.ATTR_NOT_SPECIFIED
        #   check pictures for error snapshot
        #mgnt_subnet=test_plugin1.create_subnet(context,{'subnet':{'name':mgnt_subnet_name,'network_id':mgnt_network['id'],'ip_version':4,'cidr':subnet_cidr,'gateway_ip':gateway_ip,'enable_dhcp':True,'allocation_pools':allocation_pools,'dns_nameservers':dns_nameservers,'host_routes':host_routes}})        #   /opt/stack/neutron/neutron/db/db_base_plugin_v2.py

  #added by padmaja
        flag = 0
        subnets_list=test_plugin1.get_subnets(context)
        for subnet in subnets_list:
            if source_addr==subnet['cidr']:
                source_subnet_id=subnet['id']
                fw_ip_address = subnet['gateway_ip']

            if dest_addr==subnet['cidr']:
                destination_subnet_id=subnet['id']

            if mgnt_subnet_cidr==subnet['cidr']:
                mgnt_subnet_id=subnet['id']
                flag = 1

        if flag == 0:
            mgnt_network=test_plugin1.create_network(context,{'network':{'name':mgnt_network_name,'admin_state_up':True,'shared':False}})
            mgnt_net_id=mgnt_network['id']
            gateway_ip = attributes.ATTR_NOT_SPECIFIED
            allocation_pools = attributes.ATTR_NOT_SPECIFIED
            dns_nameservers = attributes.ATTR_NOT_SPECIFIED
            host_routes= attributes.ATTR_NOT_SPECIFIED
            mgnt_subnet=test_plugin1.create_subnet(context,{'subnet':{'name':mgnt_subnet_name,'network_id':mgnt_network['id'],'ip_version':4,'cidr':mgnt_subnet_cidr,'gateway_ip':gateway_ip,'enable_dhcp':True,'allocation_pools':allocation_pools,'dns_nameservers':dns_nameservers,'host_routes':host_routes}})
            mgnt_subnet_id=mgnt_subnet['id']

        networks_list=test_plugin1.get_networks(context)
        for net in networks_list:
                if source_subnet_id==net['subnets'][0]:
                    source_net_id=net['id']

                if destination_subnet_id==net['subnets'][0]:
                    destination_net_id=net['id']
		
                if mgnt_subnet_id==net['subnets'][0]:
                    mgnt_net_id=net['id']
        #server_nics = [{"net-id":source_net_id},{"net-id":destination_net_id},{"net-id":mgnt_network['id']}]
        #end here
        # subnets = test_plugin1._get_subnets_by_network(context, cfg.CONF.fw_appliance.Gateway_Net)  
        # count = 0
        # if subnets_list is not None:
        #    for subnet in subnets_list:
        #        if subnet['gateway_ip'] is not None:
        #            fw_ip_address = subnet['gateway_ip']
        #            break
        #        else:
        #            raise attr_invalid()
        # else:
        #    raise Exception()


        # mac =  attributes.ATTR_NOT_SPECIFIED
        # ips = [{"ip_address":fw_ip_address}]
        # name = ''
        # device_id = ''
        # device_owner = ''
        # admin_state_up = True
        # test_port = {'port':{'name':name,
        #              'network_id':source_net_id,
        #              'mac_address':mac,
        #              'fixed_ips':ips,
        #              'device_id':device_id,
        #              'device_owner':device_owner,
        #              'admin_state_up':admin_state_up}}
        # firewall_port = test_plugin1.create_port(context,test_port)
        #   Port-id updation after server create is not working 

        server_nics = [{"net-id":destination_net_id},{"net-id":mgnt_net_id},{"net-id":source_net_id,"v4-fixed-ip":fw_ip_address}]
        #server_nics = [{"net-id":destination_net_id},{"net-id":mgnt_net_id},{"net-id":source_net_id}]
        #server_nics.append({"port-id":firewall_port['id']})

        server_name = instance_name+server_instance_name                         
        server_imageid = image_id      
        server_flavor = flavor_id                             
        # server_nics = [{"net-id":cfg.CONF.fw_appliance.Net}]     
        # server_nics.append({"port-id":firewall_port['id']})
        # FIXME(anirudh): To differentiate a generic server/instance from a firewall and to 
        #                 disable user to delete the firewall instance by 'Terminate Instance',
        #                 However, server_type would require lot to changes to base code.
        #                 Need another solution to handle this issue.
        #server_type = "Firewall"
        server_output = nova_client.servers.create(server_name, server_imageid,
                                          server_flavor, min_count=1,  
                                          # *** removed the parameter stype, "stype = server_type"
                                          # as python-novaclient is incompatible with stype currently.
                                          nics=server_nics
                                          )

        server_net_id=[]
        server_net_id.append(server_output)
        server_net_id.append(source_net_id)
        return server_net_id,mgnt_net_id
