
from vnfmanager.agent.linux import utils
import yaml
import os
import re
import ipaddr
import time
import paramiko

class NetConf(object):
    def __init__(self, ns_dict):
        self.masklen = "24"
        self.ns_config = ns_dict
        #self.ns_config = yaml.load(open('/tmp/vnfm_conf.yaml', 'r'))['service']
        self.src_ip = ""
        self.dst_ip = ""
        self.classpath = "/home/openstack/netconf-driver/Netconf.jar:/home/openstack/netconf-driver/NetconfClient.jar"
        self.addl_env = {}
        self.addl_env['CLASSPATH'] = self.classpath
        self.endpoint = {}
        self.parse()
        #self.configure_service()

    def parse(self):
        self.ifaces={}
        for vnfd in self.ns_config.keys():
            if vnfd == "firewall":
                self.vnfd = vnfd
                self.vnf = str(self.ns_config[vnfd][0]['instance_list'][0])
                #self.service = self.ns_config['id']
                self.mgmt_ip = self.ns_config[vnfd][0]['mgmt-ip'][self.vnf]
                self.uname = self.ns_config[vnfd][0]['vm_details']['image_details']['username']
                self.password = self.ns_config[vnfd][0]['vm_details']['image_details']['password']
 
                for iface in self.ns_config[vnfd][0]['vm_details']['network_interfaces'].keys():
                    if iface != "mgmt-if":
                        self.ifaces[iface] = self.ns_config[vnfd][0]['vm_details']['network_interfaces'][iface]['ips'][self.vnf]
 
        self.vdu_name = self.vnf.split("-")[0] + ":" + self.vnf.split("-")[1]
 
        for cp in self.ns_config['fg']['WebAccess']['network-forwarding-path']:
 
            if cp['type'] == "endpoint":
                self.endpoint = cp
  
            if cp['name'].lower() == self.vdu_name:
                for iface in self.ns_config[self.vnfd][0]['vm_details']['network_interfaces'].keys():
                    if cp['connection-point'] == iface:
                        if self.src_ip == "":
                            self.src_ip = self.ifaces[iface]
                        elif self.dst_ip == "":
                             self.dst_ip = self.ifaces[iface]


    def _check_connection(self):
        ssh_connected = False
        # keep connecting till ssh is success
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while not ssh_connected:
            try:
                ssh.connect(self.mgmt_ip, username = self.uname, password = self.password, allow_agent=False, timeout=10)
                ssh_connected = True
                print "VM IS UP"
            except Exception:
                print "VM IS DOWN"
                pass


    # Get the destination endpoint ip to configure DNAT rules
    def _get_endpoint_ip(self):
        ep_vnfd = self.endpoint['name'].split(":")[0]
        for vnfd in self.ns_config.keys():
            if ep_vnfd == vnfd:
                ep_vnf = self.ns_config[vnfd][0]['instance_list'][0]
                for iface in self.ns_config[vnfd][0]['vm_details']['network_interfaces'].keys():
                    if self.endpoint['connection-point'] == iface:
                        self.endpoint['ip'] = self.ns_config[vnfd][0]['vm_details']['network_interfaces'][iface]['ips'][ep_vnf]


    def configure_service(self, *args):
        self._check_connection()
        self._configure_firewall()
        self._configure_nat()

    def _get_subnet(self, ip_addr):
        ip=ip_addr.split(".")
        ip.pop()
        ip.append('0')
        return '.'.join(ip)+"/"+ self.masklen


    def _configure_nat(self):
        # Get dst endpoint from forwarding graph ,
        #   to configure DNAT and SNAT on the packets traversing through firewall and destined to webservers

        nat_commands_list = []
        match_addr = self.src_ip

        self._get_endpoint_ip()
        if self.endpoint['ip'] is not None:
            nat_commands_list.append("set security nat destination pool dst-nat-pool-1 address " + self.endpoint['ip'])
 
        if match_addr is not None:
            match_subnet = self._get_subnet(match_addr)
            match_addr_mask = ipaddr.IPv4Network(match_subnet)
            match_network = str(match_addr_mask.network)
 
            match_interface = self._get_vsrx_interface_name(match_network)
            match_zone = self._get_vsrx_interface_zone(match_interface)
           
            if match_zone is not None:
                nat_commands_list.append("set security nat destination rule-set rs1 from zone " + match_zone)
                nat_commands_list.append("set security nat destination rule-set rs1 rule r1 match destination-address " + match_addr)
                nat_commands_list.append("set security nat destination rule-set rs1 rule r1 then destination-nat pool dst-nat-pool-1")
 
        self.executeCommands(nat_commands_list) 


    def _configure_firewall(self):
        policy_commands_list = []
        firewall_action = "permit"
        src_network=""
        dst_network=""
        dst_zone_exists = False
        src_zone_exists = False
 
        # Get forwarding policies to be configured from forwarding graph
        # Get corresponding interfaces and ips from vdu_details in vnfm yaml file
        # Get the subnet configuration (masklen also)
 
 
        dst_subnet = self._get_subnet(self.dst_ip)
        src_subnet = self._get_subnet(self.src_ip)
 
        if dst_subnet is not None:
            dst_addr_mask = ipaddr.IPv4Network(dst_subnet)
            dst_network = str(dst_addr_mask.network)
            dst_addr = dst_network + "/" + str(dst_addr_mask.netmask)
 
        if src_subnet is not None:
            src_addr_mask = ipaddr.IPv4Network(src_subnet)
            src_network = str(src_addr_mask.network)
            src_addr = src_network + "/" + str(src_addr_mask.netmask)
 
        dst_interface = self._get_vsrx_interface_name(dst_network)
        src_interface = self._get_vsrx_interface_name(src_network)
 
        dst_zone_name = self._get_vsrx_interface_zone(dst_interface)
        src_zone_name = self._get_vsrx_interface_zone(src_interface)
 
        if dst_zone_name is not None:
            policy_commands_list.append("set security address-book dst-book attach zone " + dst_zone_name)
            dst_zone_exists = True
 
        if src_zone_name is not None:
            policy_commands_list.append("set security address-book src-book attach zone " + src_zone_name)
            src_zone_exists = True
 
        if dst_zone_exists and src_zone_exists:
 
            fr_name = src_zone_name + "_" + dst_zone_name
            fr_rev_name = dst_zone_name + "_" + src_zone_name
 
            policy_commands_list.append("set security policies from-zone " + src_zone_name + " to-zone " + dst_zone_name + " policy " + fr_name + " then " + firewall_action)
 
            policy_commands_list.append("set security policies from-zone " + dst_zone_name + " to-zone " + src_zone_name + " policy " + fr_rev_name + " then " + firewall_action)
 
            if src_addr is not None:
                src_addr_str = "src_addr"
                src_addr_cmd = "set security address-book src-book address " + src_addr_str + " wildcard-address " + src_addr
                policy_commands_list.append(src_addr_cmd)
 
            if dst_addr is not None:
                dst_addr_str = "dst_addr"
                dst_addr_cmd = "set security address-book dst-book address " + dst_addr_str + " wildcard-address " + dst_addr
                policy_commands_list.append(dst_addr_cmd)
 
            # build the firewall policy commands
            policy_commands_list.append("set security policies from-zone "+ src_zone_name + " to-zone " + dst_zone_name + " policy " + fr_name + " match source-address any destination-address " + dst_addr_str + " application any")
 
            policy_commands_list.append("set security policies from-zone " + dst_zone_name + " to-zone " + src_zone_name + " policy " + fr_rev_name + " match source-address " + dst_addr_str + " destination-address any application any")
 
            self.executeCommands(policy_commands_list)
        return ""

    def executeCommands(self, commands_list):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.uname, self.password])
 
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

    def _get_vsrx_interface_name(self, network):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunCliCommand']
        executionList.extend([self.mgmt_ip, self.uname, self.password])
        executionList.extend(["show route terse"])
        command_exec_success = False
 
        while not command_exec_success:
            try:
                op_list=[]
                retVal=""
                retVal = utils.execute(executionList, addl_env=self.addl_env)
                for line in retVal.splitlines(retVal.count('\n')):
                    if re.search(network, line):
                         line = line.rstrip()
                         op_list=re.split(" ", line)
                         iface=op_list[len(op_list)-1].replace(">", "")
                         return iface
                command_exec_success = True
            except Exception:
                pass
        return ""

    def _get_vsrx_zone_list(self):
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.uname, self.password])
        command_exec_success = False
 
        zone_list=[]
 
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
                command_exec_success = True
                return zone_list
            except Exception:
                pass
        return ""

    def _get_vsrx_interface_zone(self, interface):
        zone_list=[]
        os.putenv("CLASSPATH", self.classpath);
        executionList=['java', 'RunConfigurationCommand']
        executionList.extend([self.mgmt_ip, self.uname, self.password])
        command_exec_success = False
 
        zone_list = self._get_vsrx_zone_list()
 
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
