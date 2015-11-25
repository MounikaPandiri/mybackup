## vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2014 Tata Consultancy Services Limited
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
#
# @author: Anirudh Vedantam, anirudh.vedantam@tcs.com , Tata Consultancy Services Limited.

import re

from oslo.config import cfg

from neutron.agent.common import config
from neutron.agent.linux import ip_lib
from neutron.common import topics
from neutron import context
from neutron.extensions import firewall as fw_ext
from neutron.openstack.common import importutils
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants
from neutron.services.firewall.agents import firewall_agent_api as api
from neutron import nova

LOG = logging.getLogger(__name__)

VyattaOPTS = [
    cfg.StrOpt('username', default='vyatta',
               help=_("Vyatta username")),
    cfg.StrOpt('password', default='vyatta', secret=True,
               help=_("Vyatta password")), ]

cfg.CONF.register_opts(VyattaOPTS, "FW_appliance_creds")

OPTS = [
    cfg.StrOpt(
        'fw_app_driver',
        default='',
        help=_("Name of the FWaaS Driver")),
    cfg.BoolOpt(
        'fw_enabled',
        default=False,
        help=_("Enable FWaaS")),
]
cfg.CONF.register_opts(OPTS,'fw_app')

#GatewayOPTS = [
#         cfg.StrOpt('Gateway_Net',
#               help=_("Gateway Communication Network ID for the firewall VM")),
#]
#cfg.CONF.register_opts(GatewayOPTS, "fw_appliance")

class FWaaSNetconfPluginApi(api.FWaaSPluginApiMixin):
    """Agent side of the FWaaS agent to FWaaS Plugin RPC API."""

    def __init__(self, topic, host):
        super(FWaaSNetconfPluginApi, self).__init__(topic, host)

    def get_firewalls_for_tenant(self, context, **kwargs):
        """Get the Firewalls with rules from the Plugin to send to driver."""
        LOG.debug(_("Retrieve Firewall with rules from Plugin"))

        return self.call(context,
                         self.make_msg('get_firewalls_for_tenant',
                                       host=self.host),
                         topic=self.topic)

    def get_tenants_with_firewalls(self, context, **kwargs):
        """Get all Tenants that have Firewalls configured from plugin."""
        LOG.debug(_("Retrieve Tenants with Firewalls configured from Plugin"))

        return self.call(context,
                         self.make_msg('get_tenants_with_firewalls',
                                       host=self.host),
                         topic=self.topic)

class FWaaSNetconfAgentRpcCallback(api.FWaaSAgentRpcCallbackMixin):
    """FWaaS Agent support to be used by Neutron L3 agent."""

    def __init__(self, conf):
        LOG.debug(_("Initializing firewall agent"))
        fwaas_driver_class_path = cfg.CONF.fw_app.fw_app_driver
        self.fwaas_enabled = cfg.CONF.fw_app.fw_enabled
        self.fwaas_driver_class = fwaas_driver_class_path
        self.fwaas_driver = {}
        self.services_sync = False
        self.root_helper = config.get_root_helper(conf)
        self.max_no_of_retries = 10
        # setup RPC to msg fwaas plugin
        self.fwplugin_rpc = FWaaSNetconfPluginApi(topics.FIREWALL_PLUGIN,
                                             conf.host)
        super(FWaaSNetconfAgentRpcCallback, self).__init__(host = conf.host)

    def _invoke_driver_for_plugin_api(self, context, fw, func_name):
        """Invoke driver method for plugin API and provide status back."""

        LOG.debug(_("%(func_name)s from agent for fw: %(fwid)s"),
                  {'func_name': func_name, 'fwid': fw['id']})
        # inovke the driver & call into the driver
        try:
            nc = nova.Nova_API()

            if func_name == 'delete_firewall':
               #if self.status == constants.ACTIVE and servs.status == 'ACTIVE':
               #try:
                   #del self.fwaas_driver[fw['id']]
                   self.fwplugin_rpc.firewall_deleted(context, fw['id'])
                   try:
                       servs = nc.get_server(context, fw['id'])
                       nc.delete_server(context, fw['id'])
                   except Exception:
                       LOG.exception(_("Server Not found:%(fwid)s. Could not \
                                        delete the Firewall instance."),{"fwid":fw['id']})
               #except KeyError:
               #    LOG.info(_("The firewall not found"))
               #except Exception:
               #    LOG.info(_("Unable to delete the firewall"))
                   #self.fwplugin_rpc.firewall_deleted(context, fw['id'])
                   return

            if func_name == 'update_firewall':
               self.update_firewall_instance(fw)
               status = constants.ACTIVE
               self.fwplugin_rpc.set_firewall_status(context,
                                                     fw['id'],
                                                     status)

            if func_name == 'create_firewall':
                servs = nc.get_server(context, fw['id'])
                if servs.status == 'ACTIVE':
                    # To give VM time to boot and startup 
                    # netconf application after it goes ACTIVE
                    # FIXME(anirudh): better approach than thread sleep
                    #                 could be implemented.
                    import time
                    time.sleep(120)         
                    fw_vm_ips = servs.networks.values()
                    fw_ips=[]
                    test_dict={}
                    for i in range(0,len(fw_vm_ips)):
                        fw_ips.append(fw_vm_ips[i][0])
                        test_dict[fw_vm_ips[i][0][:-1]+'0/24']=fw_vm_ips[i][0]
                    
                    #fw_ips = [fw_vm_ips[0][:-1]+'0/24',fw_vm_ips[1][:-1]+'0/24',fw_vm_ips[2][:-1]+'0/24')
                    fw_rules_ips = []
                    fw_rules_ips.append(fw['firewall_rule_list'][0]['source_ip_address'])
                    fw_rules_ips.append(fw['firewall_rule_list'][0]['destination_ip_address'])
                    mgnt_cidr = list(set(test_dict.keys())-set(fw_rules_ips))
                    fw_vm_gateway = test_dict[mgnt_cidr[0]]
                    #fw_rule_ips= list(set(fw_ips)-set(fw_vm_gateway))
                    
                    
               	    #fw_vm_gateway = fw_vm_ips[0] if str(fw_vm_ips[0][0].split('.')[-1]) == str(1) else fw_vm_ips[1]           

                    # To find the external network for the VM if necessary
                    # fw_vm_external = fw_vm_ips[0] if str(fw_vm_ips[0][0].split('.')[-1]) != str(1) else fw_vm_ips[1]
                    
                    try: 
                        self.fwaas_driver[fw['id']] = importutils.import_object(
                    	                                              self.fwaas_driver_class,
                                                                      self.root_helper,
                            	                                      fw_vm_gateway,
                                 	                                  fw['mgnt_net_id'],
                                                                      cfg.CONF.FW_appliance_creds.username,
                                                                      cfg.CONF.FW_appliance_creds.password,
                                            		              "5000",
				                              	      )         
                	LOG.debug(_("FWaaS Driver Loaded: '%s' with ID: %s"), 
                                       self.fwaas_driver_class,self.fwaas_driver[fw['id']])
            	    except ImportError:
                	msg = _('Error importing FWaaS device driver: %s')
                	raise ImportError(msg % fwaas_driver_class_path)         
                	status = constants.ERROR
                
            	    try:
                	interfaces = self.get_interfaces_on_firewall(fw['id'])
                        self.apply_snat(fw, interfaces)
                	#self.apply_snat(fw, fw_vm_ips, interfaces)         
                	fw_name = self.apply_fw_policies(fw)
                	self.associate_fw_to_interface(fw['id'], fw_name, interfaces)
                	status = constants.ACTIVE

            	    except fw_ext.FirewallInternalDriverError:
                	LOG.error(_("Firewall Driver Error for %(func_name)s "
                        	    "for fw: %(fwid)s"),
                      		{'func_name': func_name, 'fwid': fw['id']})
                	status = constants.ERROR

                else:
                    status = self.wait_for_service_vm(context, fw, nc)
                self.fwplugin_rpc.set_firewall_status(context,
                                                      fw['id'],
                                                      status)

   
        except Exception:
            LOG.exception(
                _("FWaaS RPC failure in %(func_name)s for fw: %(fwid)s"),
                {'func_name': func_name, 'fwid': fw['id']})
            self.services_sync = True

        return

    def apply_snat(self, firewall,interfaces):
        """Source NATting in performed as soon as the firewall VM 
           is launched and NETCONF server starts on the VM.""" 
        nat = {}

        nat['outbound_interface'] = interfaces[0]
        #gateway = ips[0] if str(ips[0].split('.')[-1]) == str(1) else ips[1]
        nat['source_address'] = firewall['firewall_rule_list'][0]['source_ip_address']
        nat['destination_address'] = '!'+nat['source_address']
        nat['translation'] = 'masquerade'
        nat['id'] = '1'

        # Generic parameter- that supplies list of firewalls/instances 
        # to be applied
        apply_list = []

        self.fwaas_driver[firewall['id']].create_nat(apply_list,nat)

    def update_firewall_instance(self, fw):
        """Updating Firewalling policies or the 
           policies associated with the Firewall VM."""
         
        interfaces = self.get_interfaces_on_firewall(fw['id'])
        fw_name = self.apply_fw_policies(fw)
        self.associate_fw_to_interface(fw['id'], fw_name, interfaces)
        LOG.debug(_("Done Updating Firewall Policies"))
        return 
         
    def apply_fw_policies(self, firewall):
        """This method applies the rules to the firewall.

           Firewall policies are extracted from the firewall logical instance 
           and applied one by one on the firewall virtual instance."""

        policy = {}
        apply_list = []

        for firewall_rule in firewall['firewall_rule_list']:
            policy['action'] = "drop" if firewall_rule['action'] == 'deny' else "accept"
            policy['position'] = firewall_rule['position'] 
            policy['protocol'] = firewall_rule['protocol']
            policy['source_ip_address'] = firewall_rule['source_ip_address']
            policy['destination_ip_address'] = firewall_rule['destination_ip_address']
            policy['source_port_range_min'] = None
            policy['destination_port_range_min'] = None
 
            Sucess, Firewall_name = self.fwaas_driver[firewall['id']].create_firewall(apply_list,policy)
            return Firewall_name
  
    def associate_fw_to_interface(self, firewall_id, firewall_name, interfaces):
        if interfaces[0] == 'eth0':
           policy_list = [interfaces[0], 'out']        
        self.fwaas_driver[firewall_id].apply_fw_on_interface(firewall_name, policy_list)


    def get_interfaces_on_firewall(self, firewall_id):
        """ Reads the interfaces associated with firewall instance."""

        # TODO(anirudh): Have not thought of a better approach then to
        #                query the netconf server for the interfaces.
        output = self.fwaas_driver[firewall_id].executeCommands('sget vyatta-interfaces')
        fields = re.split(r'[\t\n\s,{}]\s*',output)
        indicies = [i for i,x in enumerate(fields) if x == "interface"]
        names = []
        for index in indicies:
             names.append(fields[index+1])
        return names

    def wait_for_service_vm(self, context, firewall, nova_client):
        """ This function waits till the instances goes ACTIVE for the 
            further process to take place. """

        # FIXME(anirudh): better approach than thread sleep
        #                 could be implemented.
        itr_num = 0
        import time
        time.sleep(40)
        server = nova_client.get_server(context, firewall['id'])
        if server.status == 'ACTIVE':
           #time.sleep(30)
           self._invoke_driver_for_plugin_api(context, firewall, 'create_firewall')
           status = constants.ACTIVE
           return status
        else:
           if itr_num < self.max_no_of_retries:
              itr_num = itr_num+1
              self.wait_for_service_vm(context, firewall, nova_client)
           else:
              status = constants.ERROR
              return status

    def create_firewall(self, context, firewall, host):
        """Handle Rpc from plugin to create a firewall."""
        return self._invoke_driver_for_plugin_api(
            context,
            firewall,
            'create_firewall')

    def update_firewall(self, context, firewall, host):
        """Handle Rpc from plugin to update a firewall."""
        return self._invoke_driver_for_plugin_api(
            context,
            firewall,
            'update_firewall')

    def delete_firewall(self, context, firewall, host):
        """Handle Rpc from plugin to delete a firewall."""
        return self._invoke_driver_for_plugin_api(
            context,
            firewall,
            'delete_firewall')
