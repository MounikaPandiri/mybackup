from vnfmanager.agent.linux import utils
import yaml
import os
import re
import ipaddr
import time
import paramiko
from vnfmanager.drivers import abstract_driver as abs_driver
from vnfmanager.openstack.common import log as logging
from vnfmanager.openstack.common.gettextutils import _

LOG = logging.getLogger(__name__)

class NetConf(abs_driver.AbstractDriver):
    def __init__(self, *args, **kwargs):
        self.masklen = "24"
        self.classpath = "/home/openstack/netconf-driver/Netconf.jar:/home/openstack/netconf-driver/NetconfClient.jar"
        self.addl_env = {}
        self.addl_env['CLASSPATH'] = self.classpath
        self.username = kwargs['username']
        self.password = kwargs['password']

    def pre_configure(self):
        self.zone_list = self._get_vsrx_zone_list()
        self.iface_net_map = self._get_interface_mapping()
        for iface in self.iface_net_map:
            zone = self._get_vsrx_interface_zone(iface, self.zone_list)
            self.iface_net_map[iface]['zone'] = zone
 
    def configure(self, **kwargs):
        self.mgmt_ip = kwargs['mgmt-ip']
        self.args_dict = kwargs['conf']
        self.pre_configure()
        for entity in self.args_dict:
            if entity == "policy":
               self._configure_firewall(self.mgmt_ip, self.args_dict['policy'])
            elif entity == "nat":
               self._configure_nat(self.mgmt_ip, self.args_dict['nat'])
 
    def update(self, **kwargs):
        """
        Description   : Accepts policy and nat configuration updates.
        Input         : In the form of dictionary of dictionaries
        Params        :
           Type       : policy(This should be specified as key of dict)
           name       : policy name in form of string
           src-ip     : Source IP Address in string format
           dst-ip     : Destination IP Address in string format
           action     : "allow" or "deny"
           application: Protocol name in string format

           Type       : nat(This should be specified as key of dict)
           source-nat : "true" or "false"
           dest-nat   : "true" or "false"
           src-ip     : Source IP Address
           dst-ip     : Destination IP Address

         Example      : {'policy': {'name' : 'fw_rule', 'src_ip': '192.168.3.2', 
                                    'dst_ip': '192.168.2.2', 'action': 'deny', 
                                    'application': 'tcp'}
                          'nat'  : {'source_nat': 'True', 'dest-nat': 'False' 
                                    'src_ip': '192.168.3.2', 
                                    'dst_ip':'192.168.2.2'}
                        }
         """
        mgmt_ip = kwargs['mgmt-ip']
        for entity in kwargs['conf']:
            if entity == "policy":
               self._update_policy(mgmt_ip, kwargs['conf']['policy'])
            elif entity == "nat":
               self._update_nat(mgmt_ip, kwargs['conf']['nat'])

    def _configure_nat(self, mgmt_ip, args_dict):
        nat_commands_list = []
        self.mgmt_ip = mgmt_ip
        nat_type = args_dict['type']
        
        if nat_type == 'destination-nat':

            nat_commands_list.append("set security nat destination pool dst-nat-pool-1 address " + args_dict['ipaddr'])
            match_addr = args_dict['match']['src']
            if match_addr is not None:
                match_subnet = self._get_subnet(match_addr)
                match_addr_mask = ipaddr.IPv4Network(match_subnet)
                match_network = str(match_addr_mask.network)
  
                match_interface = self._get_vsrx_interface_name(match_network)
                match_zone = self._get_vsrx_interface_zone(match_interface, self.zone_list)
           
                if match_zone is not None:
                    nat_commands_list.append("set security nat destination rule-set rs1 from zone " + match_zone)
                    nat_commands_list.append("set security nat destination rule-set rs1 rule r1 match destination-address " + match_addr)
                    nat_commands_list.append("set security nat destination rule-set rs1 rule r1 then destination-nat pool dst-nat-pool-1")

        if nat_type == 'source-nat':

            nat_commands_list.append("set security nat source pool dst-nat-pool-1 address " + args_dict['ipaddr'])
            match_addr = args_dict['match']['dst']
            if match_addr is not None:
                match_subnet = self._get_subnet(match_addr)
                match_addr_mask = ipaddr.IPv4Network(match_subnet)
                match_network = str(match_addr_mask.network)
  
                match_interface = self._get_vsrx_interface_name(match_network)
                match_zone = self._get_vsrx_interface_zone(match_interface, self.zone_list)
           
                if match_zone is not None:
                    nat_commands_list.append("set security nat destination rule-set rs1 from zone " + match_zone)
                    nat_commands_list.append("set security nat destination rule-set rs1 rule r1 match destination-address " + match_addr)
                    nat_commands_list.append("set security nat destination rule-set rs1 rule r1 then destination-nat pool dst-nat-pool-1")

 
        self.executeCommands(nat_commands_list) 


    def _configure_firewall(self, mgmt_ip, args_dict):
        policy_commands_list = []
        self.mgmt_ip = mgmt_ip
        dst_zone_exists = False
        src_zone_exists = False
        src_network,dst_network,src_addr,dst_addr = self._get_addr_from_ip(args_dict['src_ip'],args_dict['dst_ip'])
   
        dst_interface = self._get_vsrx_interface_name(dst_network)
        src_interface = self._get_vsrx_interface_name(src_network)
 
        dst_zone_name = self._get_vsrx_interface_zone(dst_interface, self.zone_list)
        src_zone_name = self._get_vsrx_interface_zone(src_interface, self.zone_list)

        if dst_zone_name is not None:
            policy_commands_list.append("set security address-book dst-book attach zone " + dst_zone_name)
            dst_zone_exists = True
 
        if src_zone_name is not None:
            policy_commands_list.append("set security address-book src-book attach zone " + src_zone_name)
            src_zone_exists = True
 
        if dst_zone_exists and src_zone_exists:

            policy_commands_list = self._frame_command_list(src_zone_name, dst_zone_name, src_addr, 
                                                            dst_addr, args_dict, policy_commands_list)
            self.executeCommands(policy_commands_list)
        return ""

### ADDED By Mounika for update ###

    def _frame_command_list(self, src_zone_name, dst_zone_name, 
                            src_addr, dst_addr, args_dict, 
                            policy_commands_list):

        src_ip = args_dict['src_ip']
        dst_ip = args_dict['dst_ip']
        application = args_dict['application']
        application = self.get_vsrx_application(application)
        firewall_action = args_dict['action']
        if firewall_action == 'allow':
            firewall_action = 'permit'
        policy_name = args_dict['name']
        self.policy_dict = dict()
        self.policy_dict[policy_name] = dict()

        policy_commands_list.append("set security policies from-zone " + \
                                    src_zone_name + " to-zone " + dst_zone_name + \
                                    " policy " + policy_name + " then " + firewall_action)

        policy_commands_list.append("set security policies from-zone " + \
                                    dst_zone_name + " to-zone " + src_zone_name + \
                                    " policy " + policy_name + " then " + firewall_action)

        if src_addr is not None:
            src_addr_str = "src_addr"
            src_addr_cmd = "set security address-book src-book address " + src_addr_str + " wildcard-address " + src_addr
            policy_commands_list.append(src_addr_cmd)

        if dst_addr is not None:
            dst_addr_str = "dst_addr"
            dst_addr_cmd = "set security address-book dst-book address " + dst_addr_str + " wildcard-address " + dst_addr
            policy_commands_list.append(dst_addr_cmd)

            # build the firewall policy commands
        policy_commands_list.append("set security policies from-zone "+ src_zone_name + \
                                    " to-zone " + dst_zone_name + " policy " + policy_name + \
                                    " match source-address any destination-address " + \
                                    dst_addr_str + " application " + application)

        policy_commands_list.append("set security policies from-zone " + dst_zone_name + \
                                    " to-zone " + src_zone_name + " policy " + policy_name + \
                                    " match source-address any"+ \
                                    " destination-address " + src_addr_str+" application " + application)

        self.policy_dict[policy_name]['src_zone'] = src_zone_name
        self.policy_dict[policy_name]['dst_zone'] = dst_zone_name
        self.policy_dict[policy_name]['src_addr'] = src_ip
        self.policy_dict[policy_name]['dst_addr'] = dst_ip
        self.policy_dict[policy_name]['application'] = application
        self.policy_dict[policy_name]['action'] = firewall_action

        return policy_commands_list

 
    def _update_policy(self, mgmt_ip, args_dict):
        src_ip = args_dict['src_ip']
        dst_ip = args_dict['dst_ip']
        self.mgmt_ip = mgmt_ip
        application = args_dict['application']
        application_new = self.get_vsrx_application(application)
        action = args_dict['action']
        if action == 'allow':
            action = 'permit'
        policy_commands_list = []

        for policy in self.policy_dict:
            if self.policy_dict[policy]['src_addr'] == src_ip and self.policy_dict[policy]['dst_addr'] == dst_ip:
               policy_name_old = policy

               if self.policy_dict[policy]['application'] == application_new and self.policy_dict[policy]['action'] == action:
                  LOG.debug(_("policy already present"))

               else:
                  src_zone_name = self._get_zone_for_ip(src_ip)
                  dst_zone_name = self._get_zone_for_ip(dst_ip)
                  src_network,dst_network,src_addr,dst_addr = self._get_addr_from_ip(src_ip, dst_ip)

                  policy_commands_list.append("delete security policies from-zone " +\
                                               src_zone_name+ " to-zone " + \
                                               dst_zone_name + " policy " + policy_name_old)

                  policy_commands_list.append("delete security policies from-zone " + \
                                               dst_zone_name + " to-zone " + \
                                               src_zone_name + " policy " + policy_name_old)

                  if dst_zone_name is not None:
                      dst_zone_exists = True

                  if src_zone_name is not None:
                      src_zone_exists = True

                  if dst_zone_exists and src_zone_exists:
                      policy_commands_list = self._frame_command_list(src_zone_name, dst_zone_name, src_addr, 
                                                                      dst_addr, args_dict, policy_commands_list)
                  self.executeCommands(policy_commands_list)

            else:
               self._configure_firewall(args_dict)

    def update_rule(self, **kwargs):
        """Update the Firewall Rule."""
        pass

    def update_zone(self, **kwargs):
        """Update the Firewall Zone."""
        pass

    def _update_nat(self, mgmt_ip, args_dict):
        """Update the Nat."""
        pass

## ends here ###

### added by Mounika to get mapping for inerfaces and network,ips ###

    def _get_interface_mapping(self):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunCliCommand']
        executionList.extend([self.mgmt_ip, self.username, self.password])
        executionList.extend(["show route terse"])
        command_exec_success = False
        while not command_exec_success:
            interfaces_dict = dict()
            try:
                op_list=[]
                retVal=""
                retVal = utils.execute(executionList, addl_env=self.addl_env)
                for line in retVal.splitlines(retVal.count('\n')):
                    op_list.append(line)
                for i in range(len(op_list)):
                    iface_dict = dict()
                    if op_list[i] != '\n':
                       op_split = op_list[i].split(" ")
                       if op_split[-4].find('ge') >=0:
                          iface_dict['network'] = op_split[1]
                          new_op = op_list[i+1]
                          new_op_split = new_op.split(" ")
                          iface_dict['ip'] = new_op_split[1]
                          interfaces_dict[op_split[-4][1:]] = iface_dict
                command_exec_success = True 
            except Exception as e:
                pass  
        return interfaces_dict

### Ends Here ##############

    def _get_vsrx_zone_list(self):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.username, self.password])
        command_exec_success = False
 
        zone_list=[]
        try:
          while not command_exec_success:
            try:
                op_list=[]
                executionList.extend(["show security zones"])
                retVal=""
                retVal = utils.execute(executionList, addl_env=self.addl_env)
                for line in retVal.splitlines(retVal.count('\n')):
                     if re.search("security-zone", line):
                         line = line.rstrip()
                         op_list=re.split(" ", line)
                         zone=op_list[len(op_list)-2]
                         zone_list.extend([zone])

                if "exception" in retVal:
                    command_exec_success = False
                else:
                    command_exec_success = True
            except Exception:
                pass
        finally:
            return zone_list

    def _get_vsrx_interface_zone(self, interface, zone_list):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.username, self.password])
        command_exec_success = False
        ### Modified by Mounika ### 
        for zone in zone_list:
            command_exec_success = False
            cmd = "show security zones security-zone " + zone
            executionList.extend([cmd])
            while not command_exec_success:
                try:
                    op_list=[]
                    retVal=""
                    retVal = utils.execute(executionList, addl_env=self.addl_env)
                    for line in retVal.splitlines(retVal.count('\n')):
                        if re.search(interface, line):
                            return zone
                    command_exec_success = True
                except Exception:
                    pass
            del executionList[len(executionList)-1]
        return ""

####added By Mounika##
    def _get_zone_for_ip(self,addr):
        for iface in self.iface_net_map:
            if self.iface_net_map[iface]['ip'].split('/')[0] == addr:
               zone = self.iface_net_map[iface]['zone']
        return zone
               
    def _get_vsrx_interface_name(self,network):
       for iface in self.iface_net_map:
           if self.iface_net_map[iface]['network'].split('/')[0] == network:
              return iface

    def get_vsrx_application(self, protocol):

        if protocol=="icmp":
            return "junos-icmp-all"
        elif protocol == "tcp":
            return "junos-tcp-any"
        elif protocol == "any":
            return "any"

    def _get_addr_from_ip(self, src_ip, dst_ip):
        dst_subnet = self._get_subnet(dst_ip)
        src_subnet = self._get_subnet(src_ip)

        if dst_subnet is not None:
            dst_addr_mask = ipaddr.IPv4Network(dst_subnet)
            dst_network = str(dst_addr_mask.network)
            dst_addr = dst_network + "/" + str(dst_addr_mask.netmask)

        if src_subnet is not None:
            src_addr_mask = ipaddr.IPv4Network(src_subnet)
            src_network = str(src_addr_mask.network)
            src_addr = src_network + "/" + str(src_addr_mask.netmask)

        return src_network,dst_network,src_addr,dst_addr

## ends here ##

    def executeCommands(self, commands_list):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.username, self.password])

        for command in commands_list:
            executionList.append(command);

        execute=False
        while not execute:
            try:
                retVal = utils.execute(executionList, addl_env=self.addl_env)
                execute=True
            except Exception:
                pass
        return retVal

    def _check_connection(self):
        ssh_connected = False
        # keep connecting till ssh is success
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while not ssh_connected:
            try:
                ssh.connect(self.mgmt_ip, username = self.username, password = self.password, allow_agent=False, timeout=10)
                ssh_connected = True
                print "VM IS UP"
            except Exception:
                print "VM IS DOWN"
                pass

    def _get_subnet(self, ip_addr):
        ip=ip_addr.split(".")
        ip.pop()
        ip.append('0')
        return '.'.join(ip)+"/"+ self.masklen
