# vim: tabstop=4 shiftwidth=4 softtabstop=4
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
# @author: Hemanth N, hemanth.n@tcs.com, Tata Consultancy Services Limited
# @author: anirudh vedantam, anirudh.vedantam@tcs.com, Tata Consultancy Services Limited

from neutron.agent.linux import ip_lib

from neutron.openstack.common import log as logging
from neutron.services.firewall.drivers import fwaas_base
####
import subprocess
from subprocess import call, Popen, PIPE
#####


LOG = logging.getLogger(__name__)

class NetconfFwaasDriver(fwaas_base.FwaasDriverBase):

    def __init__(self , root_helper, ip,  network_id, uname, password, ncport):
        LOG.debug(_("Initializing fwaas Netconf driver"))
        self.__ip = "server="+ip
        self.__uname = "user="+uname
        self.__password = "password="+password
        self.__ncport = "ncport="+ncport
	self.root_helper = root_helper
	self.__network_id = network_id

    def create_firewall(self, apply_list, firewall):
	    LOG.debug(_('Creating firewall and associating rule: %(rule_id)s)'),
                  {'rule_id': firewall['position']})
        
            return self.update_firewall(apply_list, firewall)

    def update_firewall(self, apply_list, firewall):
        return self._update_firewall(apply_list, firewall)
        #else:
        #    return self.apply_default_policy(apply_list, firewall)

    def delete_firewall(self, apply_list, firewall):
	LOG.debug(_('Deleting firewall %(fw_id)s for tenant %(tid)s)'),
                  {'fw_id': firewall['id'], 'tid': firewall['tenant_id']})
        
        command = "delete /vyatta-firewall"
        self.executeCommands(command)
        
        return True

    def apply_default_policy(self, apply_list, firewall):
        """ Default Policy to be applied to the firewall in 
            case no rules are specified or admin state is inactive.""" 

        # TODO(anirudh) : Still this function is ready to be used. 
	LOG.debug(_('Applying firewall %(fw_id)s for tenant %(tid)s)'),
                  {'fw_id': firewall['id'], 'tid': firewall['tenant_id']})

	firewall_policy = firewall['firewall_policy_id']
		
	# Delete firewall policy or rule? Apply default policy hardcoded?
	# delete /vyatta-firewall/firewall-name[name='%s']/rule
 	# replace /vyatta-firewall/firewall-name[name='%s']/default-action --value='drop'
		
	command_list = []
	command_list.append("delete /vyatta-firewall/firewall-name[name='%s']/rule" % firewall_policy)
	command_list.append("replace /vyatta-firewall/firewall-name[name='%s']/default-action --value='drop'" % firewall_policy)
		
	for command in command_list:
	    self.executeCommands(command)
	    
        return True
    
    def create_nat(self, apply_list, nat):
	LOG.debug(_('Applying Source NATTing: %(nat_id)s on the Firewall instance'),
                  {'nat_id': nat['id']})
        LOG.warn(_('APPLYING NAT RULES'))
        
        command_list = []
	    
 	vyatta_rules = {
		   "source_address": "replace /vyatta-nat/source/rule[name='%s']/source/address --value='%s'",
		   "outbound_interface": "replace /vyatta-nat/source/rule[name='%s']/outbound-interface --value='%s'",
		   "destination_address": "replace /vyatta-nat/source/rule[name='%s']/destination/address --value='%s'",
	 	   "translation": "replace /vyatta-nat/source/rule[name='%s']/translation/address --value='%s'"	
        }
	    
	command_list.append("replace /vyatta-nat/source/rule[name='%s']" % nat['id'])

        for k in vyatta_rules.keys():
           if nat[k]:
              command_list.append(vyatta_rules[k] % (nat['id'], nat[k]))
		
	LOG.debug(_("NAT Policy Command list (%s)"), command_list)
#        execute=False
#        for command in command_list:
#            while not execute:
#                val = self.executeCommands(command)
#                if val == '\n':
#                    execute = True
#                    break
         
	for command in command_list:
	    self.executeCommands(command)

        return True
	
    def delete_nat(self, apply_list, nat):
	LOG.debug(_('Deleting NAT %(nat_id)s for tenant %(tid)s)'),
                  {'nat_id': nat['id'], 'tid': nat['tenant_id']})
        
        command = "delete /vyatta-nat"
        self.executeCommands(command)
        
        return True
    
    def _update_firewall(self, apply_list, firewall):
        LOG.debug(_("Applying firewall rule: %(rule)s on firewall"), {'rule':firewall['position']})
        
        # TODO(anirudh) : command_keys are to keep track of which cmds are executed and 
        #                 which to be executed first so that firewall 
        #                 doesn't go to an inconsistent state. If possible to implement
        #				  a better method.
        
        command_keys = {} 
        command_list = []
        
        vyatta_rules = {
	    "action": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/action --value='%s'",
	    "protocol": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/protocol --value='%s'",
	    "source_ip_address": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/source/address --value='%s'",
	    "destination_ip_address": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/destination/address --value='%s'",
	    "source_port_range_min": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/source/port --value='%s'",
	    "destination_port_range_min": "replace /vyatta-firewall/firewall-name[name='%s']/rule[name='%s']/destination/port --value='%s'"
        }
        
        firewall_policy_name = "fw1"        # Hardcoding it for now later to make it dyanamically available from agent.
        command_keys['firewall-name'] = "replace /vyatta-firewall/firewall-name[name='%s']" % firewall_policy_name
        command_keys['default-action'] = "replace /vyatta-firewall/firewall-name[name='%s']/default-action --value='drop'" % firewall_policy_name
        
        for k in vyatta_rules.keys():
             if firewall[k]:
                 command_keys[k] = vyatta_rules[k] % (firewall_policy_name, firewall['position'], firewall[k])
	     else:
                 LOG.warn(_("Unsupported IP version rule."))
		
        LOG.debug(_("Firewall Policy Command list (%s)"), command_list)
 
        for command in command_keys:
            if command == 'action' or command == 'firewall-name' or command == 'firewall-name':
	       self.executeCommands(command_keys[command])
            else:
               command_list.append(command_keys[command])

        for command in command_list:
            self.executeCommands(command)

#        execute=False
#        for command in command_list:
#            while not execute:
#                val = self.executeCommands(command)
#                if val == '\n':
#                    execute = True
#                    break
		
	    
        return (True, firewall_policy_name)

    def apply_fw_on_interface(self, firewall_name, interfaces):
	LOG.debug(_('Associating Firewall %(firewall_name)s with interfaces %(interface)s)'),
                  {'firewall_name': 'fw1', 'interface': 'eth0'})
        
        command = "replace /vyatta-interfaces/interface[name='%s']/firewall/%s/name --value='%s'"%\
                        (interfaces[0], interfaces[1], firewall_name)
        self.executeCommands(command)
        
        return True


    def executeCommands(self, command):
	#executionList = ['/opt/stack/neutron/bin/workspace1/OpenYuma-master/netconf/target/bin/yangcli']
        executionList = ['/opt/stack/yangcli']
	executionList.extend([self.__ip, self.__uname, self.__password, self.__ncport])
	executionList.append(command);
		
	# TODO: How to get Namespace.. something fishy
	# TODO: Is apply_list is list of Firewalls???
        addl_env = {}
	namespace = "qdhcp-" + self.__network_id
	ns = ip_lib.IPWrapper(self.root_helper, namespace)

	# TODO(anirudh): To handle 'mgr_io_failed' error in efficient way
        #	         to reapply the commands by the deleting the leaf
        #                from the point of error.
        
        execute=False
        while not execute:
            try:
                retVal = ns.netns.execute(executionList,addl_env)
                execute=True
            except Exception:
                pass
#	while(True):
#	    retVal = ns.netns.execute(executionList,addl_env)
#	    if  retVal.find("mgr_io failed") == -1:
#		break;
		
	return retVal
