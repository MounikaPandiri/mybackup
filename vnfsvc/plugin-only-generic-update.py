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

import datetime
import json
import os
import uuid
import shutil
import six
import eventlet
import pexpect
import tarfile
import time
import sys 
import re
import yaml
import ast
import subprocess
import traceback
import pyaml

from collections import OrderedDict
from distutils import dir_util
from netaddr import IPAddress, IPNetwork
from oslo.config import cfg

from vnfsvc import constants
from vnfsvc import manager
from vnfsvc import constants as vm_constants
from vnfsvc import config
from vnfsvc import context
from vnfsvc import nsdmanager

from vnfsvc.api.v2 import attributes
from vnfsvc.api.v2 import vnf
from vnfsvc.db.vnf import vnf_db
from vnfsvc.db import monitoring

from vnfsvc.openstack.common.gettextutils import _
from vnfsvc.openstack.common import excutils
from vnfsvc.openstack.common import log as logging
from vnfsvc.openstack.common import importutils

from vnfsvc.client import client
from vnfsvc.client import utils as ovs_utils

from vnfsvc.common import driver_manager
from vnfsvc.common import exceptions
from vnfsvc.common import rpc as v_rpc
from vnfsvc.common import topics
from vnfsvc.agent.linux import utils
from vnfsvc.common.yaml.nsdparser import NetworkParser
from vnfsvc.common.yaml.vnfdparser import VNFParser
from vnfsvc.vnfmonitor import service as monitor_service
## ADDED BY ANIRUDH
from vnfsvc.db import monitoring
#

LOG = logging.getLogger(__name__)
DEFAULT_OVS_VSCTL_TIMEOUT = 10

class VNFPlugin(vnf_db.NetworkServicePluginDb):
    """VNFPlugin which provide support to OpenVNF framework"""

    #register vnf driver 
    OPTS = [
        cfg.MultiStrOpt(
            'vnf_driver', default=[],
            help=_('Hosting  drivers for vnf will use')),
        cfg.StrOpt(
            'templates', default='',
            help=_('Path to service templates')),
        cfg.StrOpt(
            'vnfmanager', default='',
            help=_('Path to VNF Manager')),
        cfg.StrOpt(
            'compute_hostname', default='',
            help=_('Compute Hostname')),
        cfg.StrOpt(
            'compute_user', default='',
            help=_('User name')),
        cfg.StrOpt(
            'vnfm_home_dir', default='',
            help=_('vnf_home_dir')),
        cfg.StrOpt(
            'compute_home_user', default='',
            help=_('compute_home_user')),
        #cfg.StrOpt(
        #    'puppet_master_image_id', default='',
        #    help=_('puppet_master_image_id')),
        cfg.StrOpt(
            'ssh_pwd', default='',
            help=_('ssh_pwd')),
        cfg.StrOpt(
            'ovs_bridge', default='br-int',
            help=_('ovs_bridge')),
        cfg.StrOpt(
            'neutron_rootwrap', default='',
            help=_('path to neutron rootwrap')),
        cfg.StrOpt(
            'neutron_rootwrapconf', default='',
            help=_('path to neutron rootwrap conf')),
        cfg.StrOpt(
            'vnfmconf', default='local',
            help=_('Vnf Manager Configuaration')),
    ]
    cfg.CONF.register_opts(OPTS, 'vnf')
    conf = cfg.CONF

    def __init__(self):
        super(VNFPlugin, self).__init__()
        self.novaclient = self._get_nova_client()
        self.glanceclient = self._get_glance_client()
        self.neutronclient = self._get_neutron_client()
        self._pool = eventlet.GreenPool()
        self.conf = cfg.CONF
        self.ns_dict = dict()

        config.register_root_helper(self.conf)
        self.root_helper = config.get_root_helper(self.conf)
        self.agent_mapping = dict()
        self.vsctl_timeout = DEFAULT_OVS_VSCTL_TIMEOUT

        self.endpoints = [VNFManagerCallbacks(self), VNFMonitorRPCHandler(self)]
        self.conn = v_rpc.create_connection(new=True)
        self.conn.create_consumer(
            topics.PLUGIN, self.endpoints, fanout=False)

        self.conn.consume_in_threads()
        self.monitoring_db = monitoring.get_connection("mongodb://10.138.97.204:27017/vnfsvc")


    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    def _get_neutron_client(self):
        return client.NeutronClient()

    def _get_nova_client(self):
        return client.NovaClient()

    def _get_glance_client(self):
        return client.GlanceClient()

    def _get_networks(self, ns_info):
        return ns_info['attributes']['networks']

    def _get_router(self, ns_info):
        return ns_info['attributes']['router']

    def _get_subnets(self, ns_info):
        return ns_info['attributes']['subnets']

    def _get_qos(self, ns_info):
        return ns_info['quality_of_service']

    #def _get_monitor_param(self, ns_info):
    #    return ns_info[]


    def _get_name(self, ns_info):
        return ns_info['name']

    def _ns_dict_init(self, service, nsd_id):
        ns_info = {}
        ns_info[nsd_id] = service['service']
        self.ns_dict[nsd_id]= {}
        self.ns_dict[nsd_id]['vnfds'] = {}
        self.ns_dict[nsd_id]['instances'] = {}
        self.ns_dict[nsd_id]['configured'] = []
        self.ns_dict[nsd_id]['image_list'] = []
        self.ns_dict[nsd_id]['flavor_list'] = []
        self.ns_dict[nsd_id]['puppet'] = ''
        self.ns_dict[nsd_id]['conf_generated'] = []
        self.ns_dict[nsd_id]['errored'] = []
        self.ns_dict[nsd_id]['is_manager_invoked'] = False
        self.ns_dict[nsd_id]['vnfmanager_uuid'] = str(uuid.uuid4())
        self.ns_dict[nsd_id]['acknowledge_list'] = dict()
        self.ns_dict[nsd_id]['deployed_vdus'] = list()
        self.ns_dict[nsd_id]['vnfm_dir'] =  self.conf.state_path+'/'+ \
                                    self.ns_dict[nsd_id]['vnfmanager_uuid']

        if not os.path.exists(self.ns_dict[nsd_id]['vnfm_dir']):
            os.makedirs(self.ns_dict[nsd_id]['vnfm_dir'])
        self.ns_dict[nsd_id]['service_name'] = self._get_name(ns_info[nsd_id])
        self.ns_dict[nsd_id]['networks'] = self._get_networks(ns_info[nsd_id])
        self.ns_dict[nsd_id]['router'] = self._get_router(ns_info[nsd_id])
        self.ns_dict[nsd_id]['subnets'] = self._get_subnets(ns_info[nsd_id])
        self.ns_dict[nsd_id]['qos'] = self._get_qos(ns_info[nsd_id])
        self.ns_dict[nsd_id]['templates_json'] = json.load(
                                       open(self.conf.vnf.templates, 'r'))

        self.ns_dict[nsd_id]['nsd_template'] = yaml.load(open(
                          self.ns_dict[nsd_id]['templates_json']['nsd']\
                          [self.ns_dict[nsd_id]['service_name']], 'r'))['nsd']



    def create_service(self, context, service):
        nsd_id = str(uuid.uuid4())
        nsd_dict = {}
        nsd_dict['id'] = nsd_id
        nsd_dict['check'] = ''
       
        try:
            self._ns_dict_init(service, nsd_id)

            self.ns_dict[nsd_id]['nsd_template'] = NetworkParser(
                                self.ns_dict[nsd_id]['nsd_template']).parse(
                                             self.ns_dict[nsd_id]['qos'],
                                             self.ns_dict[nsd_id]['networks'] ,
                                             self.ns_dict[nsd_id]['router'],
                                             self.ns_dict[nsd_id]['subnets'])

            self.ns_dict[nsd_id]['nsd_template']['router'] = {}
            self.ns_dict[nsd_id]['nsd_template'] = nsdmanager.Configuration(
                               self.ns_dict[nsd_id]['nsd_template']).preconfigure()

            for vnfd in self.ns_dict[nsd_id]['nsd_template']['vnfds']:
                vnfd_template = yaml.load(open(
                               self.ns_dict[nsd_id]['templates_json']['vnfd'][vnfd],
                               'r'))
                self.ns_dict[nsd_id]['vnfds'][vnfd] = dict()
                self.ns_dict[nsd_id]['vnfds'][vnfd]['template'] = vnfd_template
                self.ns_dict[nsd_id]['vnfds'][vnfd] = VNFParser(
                               self.ns_dict[nsd_id]['vnfds'][vnfd],
                               self.ns_dict[nsd_id]['qos'],
                               self.ns_dict[nsd_id]['nsd_template']['vnfds'][vnfd],
                               vnfd,
                               self.ns_dict[nsd_id]['nsd_template']).parse()
                self.ns_dict[nsd_id]['vnfds'][vnfd]['vnf_id'] = str(uuid.uuid4())

            db_dict = {
                'id': nsd_id,
                'nsd': self.ns_dict[nsd_id]['nsd_template'],
                'vnfds': self.ns_dict[nsd_id]['vnfds'],
                'networks': self.ns_dict[nsd_id]['networks'],
                'subnets': self.ns_dict[nsd_id]['subnets'],
                'vnfm_id': self.ns_dict[nsd_id]['vnfmanager_uuid'],
                'service': service['service'],
                'puppet_id': self.ns_dict[nsd_id]['nsd_template']['puppet-master']['instance_id'],
                'status': 'PENDING'
            }
            #Create DB Entry for the new service
            nsdb_dict = self.create_service_model(context, **db_dict)

            #Launch VNFDs
            self._create_vnfds(context,nsd_id)
            self.get_ns_config_details(nsd_id)
            self._modify_iptables(nsd_id)
            self.update_nsd_status(context, nsd_id, 'ACTIVE')
        except Exception as e:
            LOG.debug(_('An exception occured while configuring NetworkService')) 
            traceback.print_exc(file=sys.stdout)
            nsd_dict['check'] = e
            return nsd_dict
        return nsdb_dict

    def update_service(self, context, nsd_id, service):
        new_configuration = service['service']['attributes']['lifecycle_events']
        vdu_name = service['service']['attributes']['vdu_name']
        LOG.debug(_("Service: %s updation taking place with the configuration %s"), nsd_id, new_configuration)
        service_details_for_nsd = self.get_service_by_nsd_id(context, nsd_id)
        vnf_manager = service_details_for_nsd['vnfm_id']
        vdus_in_nsd = service_details_for_nsd['vdus']
        if vdu_name not in [m.split(':')[1] for m in eval(vdus_in_nsd).keys()]:
            raise exceptions.NoVduforNsd()
        status = self.agent_mapping[vnf_manager].update_vdu_configuration(context, vdu_name, new_configuration)
        updated_service = dict()
        updated_service['nsd_id'] = nsd_id
        updated_service['status'] = status
        return updated_service 

    def delete_service(self, context, service):
        self.novaclient = self._get_nova_client()
        self.glanceclient = self._get_glance_client()
        self.neutronclient = self._get_neutron_client()
        nsd_id = service
        service_db_dict = self.delete_service_model(context,service)
        try:
            self.delete_puppet_instance(service_db_dict)
        except Exception as e:
            pass
        if service_db_dict is not None:
            self.delete_vtap_and_vnfm(service_db_dict)
            try:
                self.delete_vdus(service_db_dict, service)
                time.sleep(15)
                self.delete_router_interfaces(service_db_dict)
                self.delete_router(service_db_dict)
                self.delete_ports(service_db_dict)
                self.delete_networks(service_db_dict)
                self.delete_ns_policy(context, service)
                self.delete_db_dict(context, service)
            except Exception:
                raise
        else:
            return

    def _populate_details(self, vdu_details, port, subnets, ports):
        vdu_details['subnet_id'] = port['fixed_ips'][0]['subnet_id']
        vdu_details['mac_address'] = port['mac_address']
        vdu_details['network_id'] = port['network_id']
        vdu_details['ovs_port'] = self.get_port_ofport(vdu_details['vm_interface'])
        for subnet in subnets:
            if subnet['id'] == vdu_details['subnet_id']:
                vdu_details['gateway_ip'] = subnet['gateway_ip']
        for port in ports:
            if vdu_details['gateway_ip'] == port['fixed_ips'][0]['ip_address']:
                vdu_details['is_gateway'] = True

        return vdu_details

    def get_port_ofport(self, port_name):
        ofport = self.db_get_val("Interface", port_name, "ofport")
        # This can return a non-integer string, like '[]' so ensure a
        # common failure case
        try:
            int(ofport)
            return ofport
        except (ValueError, TypeError):
            return

    def db_get_val(self, table, record, column, check_error=False):
        output = self.run_vsctl(["get", table, record, column], check_error)
        if output: 
            return output.rstrip("\n\r")

    def run_vsctl(self, args, check_error=False):
        full_args = ["sudo", "ovs-vsctl", "--timeout=%d" % self.vsctl_timeout] + args
        try:
            return ovs_utils.execute(full_args, root_helper=None)
        except Exception as e:
            with excutils.save_and_reraise_exception() as ctxt:
                if not check_error:
                    ctxt.reraise = False
    
    def get_ns_config_details(self, nsd_id):
        subnets = self.neutronclient.get_subnets()
        ports = self.neutronclient.get_ports()
        self.ns_dict[nsd_id]['instance_details'] = dict()

        for vnfd in self.ns_dict[nsd_id]['nsd_template']['vnfds']:
            self.ns_dict[nsd_id]['instance_details'][vnfd] = dict()
            for vdu in self.ns_dict[nsd_id]['nsd_template']['vnfds'][vnfd]:
                vdu_name = vnfd + ":" + vdu
                for instance in self.ns_dict[nsd_id]['vnfds'][vnfd]['vdus'][vdu]['instances']:
                    instance_networks = instance.networks
                    for k,v in instance_networks.iteritems():
                        vdu_details = dict()
                        vdu_details['name'] = instance.name
                        vdu_details['hostname'] = instance.__dict__['OS-EXT-SRV-ATTR:host']
                        vdu_details['is_gateway'] = False
                        for port in ports:
                            if v[0] == port['fixed_ips'][0]['ip_address']:
                                vdu_details['port-id'] = port['id'] 
                                vdu_details['vm_interface'] = "qvo"+port['id'][:11]
                                vdu_details = self._populate_details(vdu_details, port, subnets, ports)
                                break
                        for key1,value1 in self.ns_dict[nsd_id]['nsd_template']['vdus'][vdu_name]['networks'].iteritems():
                            if vdu_details['subnet_id'] == value1['subnet-id']:
                                if not key1 in self.ns_dict[nsd_id]['instance_details'][vnfd].keys():
                                    self.ns_dict[nsd_id]['instance_details'][vnfd][key1] = []
                                self.ns_dict[nsd_id]['instance_details'][vnfd][key1].append(vdu_details)

    def _modify_iptables(self, nsd_id):
        ipt_cmd_list = []
        port = ""
        for vdu in self.ns_dict[nsd_id]['instance_details'].keys():
            for iface in self.ns_dict[nsd_id]['instance_details'][vdu].keys():
                if iface != "" :
                    for vm in self.ns_dict[nsd_id]['instance_details'][vdu][iface]:
                        port = str(vm['port-id'])
                        self.neutronclient.update_port(port, \
                               body={"port": {"allowed_address_pairs": [{"ip_address": "0.0.0.0/0"}]}})
 
    def delete_vtap_and_vnfm(self,service_db_dict):
        try:
            vnfm_id = service_db_dict['service_db'][0].vnfm_id
            homedir = cfg.CONF.state_path
            with open(homedir+'/'+vnfm_id+"/ovs.sh","r") as f:
                data = f.readlines()
            subprocess.call(["sudo","ovs-vsctl","del-port",data[2].split(" ")[2]])
            subprocess.call(["sudo","pkill","-9","vnf-manager"])
        except Exception as e:
            pass

    def delete_puppet_instance(self, service_db_dict):
        ns_list = service_db_dict['service_db']
        try:
            for nw_service in ns_list:
               puppet = nw_service['puppet_id']
               if puppet:
                    self.novaclient.delete(puppet)
        except Exception:
            LOG.debug(_("An Exception occured while deleting puppet instance"))
            pass

    def delete_vdus(self, service_db_dict, nsd_id):
        instance_list = []
        for vdu in range(len(service_db_dict['instances'])):
            for instance in range(len(service_db_dict['instances'][vdu])): 
                instance_list = service_db_dict['instances'][vdu][instance].__dict__['instances'].split(',')
                flavor = service_db_dict['instances'][vdu][instance].__dict__['flavor']
                image = service_db_dict['instances'][vdu][instance].__dict__['image']
                try:
                    for inst in instance_list:
                        self.novaclient.delete(inst)
                    self.novaclient.delete_flavor(flavor)
                    if image in self.ns_dict[nsd_id]['image_list']:
                        self.glanceclient.delete_image(image)
                except Exception:
                    LOG.debug(_("Exception occured while deleting VDU configurarion in Netwrok Service"))
                    pass
        

    def delete_router_interfaces(self, service_db_dict):
        fixed_ips = []
        subnet_ids = []
        body = {}
        router_id = ast.literal_eval(service_db_dict['service_db'][0].router)['id']
        router_ports = self.neutronclient.list_router_ports(router_id)

        for r_port in range(len(router_ports['ports'])):
            fixed_ips.append(router_ports['ports'][r_port]['fixed_ips'])

        for ip in range(len(fixed_ips)):
            subnet_ids.append(fixed_ips[ip][0]['subnet_id'])

        for s_id in range(len(subnet_ids)):
            body['subnet_id']=subnet_ids[s_id]
            try:
                self.neutronclient.remove_interface_router(router_id, body)
            except Exception as e:
                pass

    def delete_router(self,service_db_dict):
        
        router_id = ast.literal_eval(service_db_dict['service_db'][0].router)['id']
        try:
            self.neutronclient.delete_router(router_id)
        except Exception as e:
             pass
    
    def delete_ports(self,service_db_dict):
        net_ids = ast.literal_eval(service_db_dict['service_db'][0].networks).values()
        port_list=self.neutronclient.list_ports()

        for port in range(len(port_list['ports'])):
            if port_list['ports'][port]['network_id'] in net_ids:
               port_id = port_list['ports'][port]['id']
               try:
                   self.neutronclient.delete_port(port_id)
               except Exception as e:
                   pass
    
    def delete_networks(self,service_db_dict):
        net_ids = ast.literal_eval(service_db_dict['service_db'][0].networks).values()
        for net in range(len(net_ids)):
            try:
                self.neutronclient.delete_network(net_ids[net])
            except Exception as e:
                pass


    def remove_keys(self, temp_vdus, key_list):
        for vdu in key_list:
            del temp_vdus[vdu]
        return temp_vdus

    def create_dependency_dict(self, nsd_id):
        temp_vdus = self.ns_dict[nsd_id]['nsd_template']['vdus'].copy()
        self.ns_dict[nsd_id]['dependency_dict'] = dict()
        for vdu in temp_vdus.keys():
            self.ns_dict[nsd_id]['dependency_dict'][vdu] = {
                'updatesFrom': list(),
                'updatesTo': list(),
            }
        for vdu in temp_vdus.keys():
            if 'dependency' in temp_vdus[vdu].keys():
                temp_dependencies = temp_vdus[vdu]['dependency']
                for dependent_vdu  in temp_dependencies:
                    self.ns_dict[nsd_id]['dependency_dict'][vdu]['updatesFrom'].append(dependent_vdu)
                    if dependent_vdu in self.ns_dict[nsd_id]['dependency_dict'].keys():
                        self.ns_dict[nsd_id]['dependency_dict'][dependent_vdu]['updatesTo'].append(vdu)


    def _get_vnfds_no_dependency(self ,nsd_id):
        """ Returns all the vnfds which don't have dependency """
        temp_vnfds = list()
        for vnfd in self.ns_dict[nsd_id]['nsd_template']['vnfds']:
            for vdu in self.ns_dict[nsd_id]['nsd_template']['vnfds'][vnfd]:
                if 'dependency' not in self.ns_dict[nsd_id]['nsd_template']\
                                       ['vdus'][vnfd+':'+vdu].keys():
                    temp_vnfds.append(vnfd+':'+vdu)
        return temp_vnfds

    
    def _create_flavor(self, vnfd, vdu, nsd_id):
        """ Create a openstack flavor based on vnfd flavor """
        flavor_dict = VNFParser().get_flavor_dict(
                             self.ns_dict[nsd_id]['vnfds'][vnfd]['vdus'][vdu])
        flavor_dict['name'] = vnfd+'_'+vdu+flavor_dict['name']
        return self.novaclient.create_flavor(**flavor_dict)


    def _create_vnfds(self, context, nsd_id):
        self.create_dependency_dict(nsd_id)

        """ Deploy independent VNF/VNF'S """
        self.independent_vdus = list()
        for vdu in self.ns_dict[nsd_id]['dependency_dict'].keys():
            if len(self.ns_dict[nsd_id]['dependency_dict'][vdu]['updatesFrom']) == 0:
                self.independent_vdus.append(vdu)
        
        for vnfd in self.independent_vdus:
            self._launch_vnfds(vnfd, context, nsd_id)
        self._invoke_vnf_manager(context, nsd_id)

    def wait_for_acknowledgment(self, vdus, nsd_id):
        acknowledged = False
        while not acknowledged:
            vdu_count = 0
            for vdu in vdus:
                LOG.debug(_('Wait for acknowledgement for vdu : %s'), vdu)
                if vdu in self.ns_dict[nsd_id]['errored']:
                   raise exceptions.ConfigurationError
                elif vdu in self.ns_dict[nsd_id]['configured']:
                    vdu_count = vdu_count + 1
            if vdu_count == len(vdus):
                acknowledged = True
            else:
                time.sleep(5)

    def _resolve_dependency(self, context, nsd_id):
       self.wait_for_acknowledgment(self.independent_vdus, nsd_id)
       while len(self.ns_dict[nsd_id]['nsd_template']['vdus']) != len(self.ns_dict[nsd_id]['configured']):
           vdus = list()
           for vdu in self.ns_dict[nsd_id]['dependency_dict'].keys():
               if vdu in self.ns_dict[nsd_id]['configured']:
                   continue
               else:
                   launched_dependencies = 0
                   actual_dependencies = len(self.ns_dict[nsd_id]['dependency_dict'][vdu]['updatesFrom'])
                   for dependent_vdu in self.ns_dict[nsd_id]['dependency_dict'][vdu]['updatesFrom']:
                       if dependent_vdu  in self.ns_dict[nsd_id]['configured']:
                           launched_dependencies += 1
                   if launched_dependencies == actual_dependencies:
                       vdus.append(vdu)

           for vdu in vdus:
               self._launch_vnfds(vdu, context, nsd_id)
           conf =  self._generate_vnfm_conf(nsd_id)
           for vdu in vdus:
               self.ns_dict[nsd_id]['conf_generated'].append(vdu)
           self.agent_mapping[self.ns_dict[nsd_id]['vnfmanager_uuid']].\
                  configure_vdus(context, conf=conf)
           self.wait_for_acknowledgment(vdus, nsd_id)

    def _get_vm_details(self, vnfd_name, vdu_name, nsd_id):
        flavor = self._create_flavor(vnfd_name, vdu_name, nsd_id)
        self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                    ['new_flavor'] = flavor.id
        self.ns_dict[nsd_id]['flavor_list'].append(flavor.id)
        name = vnfd_name.lower()+'-'+vdu_name.lower()
        vm_details = VNFParser().get_boot_details(
                                 self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                                 ['vdus'][vdu_name])
        vm_details['name'] = name
        vm_details['flavor'] = flavor
        return vm_details         

    def _get_vm_image_details(self, vnfd_name, vdu_name, nsd_id):
        image_details = self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus']\
                                    [vdu_name]['vm_details']['image_details']
        if 'image-id' in image_details.keys():
            image = self.glanceclient.get_image(image_details['image-id'])
        else:
            image_details['data'] = open(image_details['image'], 'rb')
            image = self.glanceclient.create_image(**image_details)
            del image_details['data']
            while image.status!='active':
                time.sleep(5)
                image = self.glanceclient.get_image(image.id)
            self.ns_dict[nsd_id]['image_list'].append(image.id)
        self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                    ['new_img'] = image.id
        
        return image    

    def _get_vm_network_details(self, vnfd_name, vdu_name, nsd_id):
        nics = []
        nw_ifaces = self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus']\
                                [vdu_name]['vm_details']['network_interfaces']
        for iface in nw_ifaces:
            if 'port_id' in nw_ifaces[iface].keys():
               nics.append({"subnet-id":nw_ifaces[iface]['subnet-id'],
                    "net-id": nw_ifaces[iface]['net-id'],
                    "port-id": nw_ifaces[iface]['port_id']})
            else:
                nics.append({"subnet-id": nw_ifaces[iface]['subnet-id'],
                             "net-id": nw_ifaces[iface]['net-id']})

        mgmt_id =  self.ns_dict[nsd_id]['networks']['mgmt-if']
        for iface in range(len(nics)):
            if nics[iface]['net-id'] == mgmt_id:
               iface_net = nics[iface]
               del nics[iface]
               nics.insert(0, iface_net)
               break
        return nics

    def _launch_vnfds(self, vnfd, context, nsd_id, method='create'):
        '''
        1)create conf dict
        2)send conf dict to VNF Manager using RPC if VNF Manager was already invoked
        '''
        vnfd_name, vdu_name = vnfd.split(':')[0],vnfd.split(':')[1]
        vm_details = self._get_vm_details(vnfd_name, vdu_name, nsd_id)
        vm_details['image_created'] = self._get_vm_image_details(vnfd_name,
                                                                 vdu_name,
                                                                 nsd_id)
        vm_details['nics'] = self._get_vm_network_details(vnfd_name,
                                                          vdu_name,
                                                          nsd_id)

        vm_details['userdata'] = self.set_default_userdata(vm_details,
                                                           nsd_id)
        self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                    ['vm_details']['userdata'] = vm_details['userdata']

        self.set_default_route(vm_details, nsd_id)
        if method == 'scale':
            vm_details['num_instances'] = 1
        with open(vm_details['userdata'], 'r') as ud_file:
            data = ud_file.readlines()
        data.insert(0, '#cloud-config\n')
        with open(vm_details['userdata'], 'w') as ud_file:
            ud_file.writelines(data)

        # Update flavor and image details for the vdu
        if method == 'create':
            self.update_vdu_details(context,
                                self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                                            ['vdus'][vdu_name]['new_flavor'],
                                self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                                            ['vdus'][vdu_name]['new_img'],
                                self.ns_dict[nsd_id]['nsd_template']['vdus']\
                                            [vnfd_name+':'+vdu_name]['id'])

        deployed_vdus = self._boot_vdu(context, vnfd, nsd_id, **vm_details)
        if method == 'create':
            if type(deployed_vdus) == type([]):
                self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                        ['instances'] = deployed_vdus
            else:
                self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                        ['instances'] = [deployed_vdus]

        elif method == 'scale':
            self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                        ['instances'].append(deployed_vdus)

        self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                        ['instance_list'] = []
        # Create dictionary with vdu and it's corresponding nova instance ID details
        self._populate_instances_id(vnfd_name, vdu_name, nsd_id)

        for instance in self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                             ['vdus'][vdu_name]['instances']:
            name = instance.name
            self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]\
                        ['instance_list'].append(name)

        self.ns_dict[nsd_id]['deployed_vdus'].append(vnfd)
        self._set_mgmt_ip(vnfd_name, vdu_name, nsd_id)
        self._set_instance_ip(vnfd_name, vdu_name, nsd_id)


    def set_default_userdata(self, vm_details, nsd_id):
        temp_dict = {'runcmd':[], 'manage_etc_hosts': 'localhost'}
        temp_dict['runcmd'].append('dhclient eth1')
        if 'cfg_engine' in self.ns_dict[nsd_id]['nsd_template']\
                                       ['preconfigure'].keys() and \
                           self.ns_dict[nsd_id]['nsd_template']\
                                       ['preconfigure']['cfg_engine'] != "":
            puppet_master_ip = self.ns_dict[nsd_id]['nsd_template']\
                                           ['puppet-master']['master-ip']
            puppet_master_hostname = self.ns_dict[nsd_id]['nsd_template']\
                                          ['puppet-master']['master-hostname']
            puppet_master_instance_id = self.ns_dict[nsd_id]['nsd_template']\
                                          ['puppet-master']['instance_id']
            self.ns_dict[nsd_id]['puppet'] = puppet_master_instance_id
            temp_dict['runcmd'].append('sudo echo '+ puppet_master_ip + \
                                       ' ' + puppet_master_hostname + \
                                       ' >> /etc/hosts')

        if 'userdata' in vm_details.keys() and vm_details['userdata'] != "":
            with open(vm_details['userdata'], 'r') as f:
                data = yaml.safe_load(f)
            if 'runcmd' in data.keys():
                temp_dict['runcmd'].extend(data['runcmd'])
                data['runcmd'] = temp_dict['runcmd']
            else:
                data['runcmd'] = temp_dict['runcmd']
            data['manage_etc_hosts'] = temp_dict['manage_etc_hosts']
            with open(self.ns_dict[nsd_id]['vnfm_dir']+'/userdata',
                      'w') as ud_file:
                yaml.safe_dump(data, ud_file)
        else:
          with open(self.ns_dict[nsd_id]['vnfm_dir']+ '/userdata',
                    'w') as ud_file:
              yaml.safe_dump(temp_dict, ud_file)
        return self.ns_dict[nsd_id]['vnfm_dir']+'/userdata'


    def set_default_route(self, vm_details, nsd_id):
        nics = vm_details['nics']
        cidr = ''
        for network in nics:
            if network['net-id'] != self.ns_dict[nsd_id]['networks']['mgmt-if']:
                 subnet_id = network['subnet-id']
                 cidr = self.neutronclient.show_subnet(subnet_id)\
                                           ['subnet']['cidr']
                 break
        if  cidr != ''  and 'userdata' in vm_details.keys():
            with open(vm_details['userdata'], 'r') as f:
                data = yaml.safe_load(f)
            ip  = cidr.split('/')[0]
            ip = ip[0:-1]+'1'
            data['runcmd'].insert(1,"sudo ip route del default")
            data['runcmd'].insert(2,"sudo ip route add default via "+ ip + \
                                    " dev eth1")
            with open(vm_details['userdata'], 'w') as userdata_file:
                yaml.safe_dump(data, userdata_file)


    def _populate_instances_id(self, vnfd_name, vdu_name, nsd_id):
        if not vnfd_name+':'+vdu_name in self.ns_dict[nsd_id]['instances'].keys():
            self.ns_dict[nsd_id]['instances'][vnfd_name+':'+vdu_name] = []
        for instance in self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                                    ['vdus'][vdu_name]['instances']:
            self.ns_dict[nsd_id]['instances'][vnfd_name+':'+vdu_name].\
                     append(instance.id)
    
    def get_configurables(self, string_to_search):
        empty = ""
        configurables = list()
        if string_to_search is empty:
           return None
        keyword_start = [m.start()+1 for m in re.finditer('{',string_to_search)] 
        keyword_end = [m.start() for m in re.finditer('}',string_to_search)]
        
        if len(keyword_start) == len(keyword_end):
           for idx in xrange(0, len(keyword_start)):
               configurable = string_to_search[keyword_start[idx]:keyword_end[idx]]
               if configurable not in configurables:
                  configurables.append(configurable)
               else:
                  continue
        return configurables

    def get_network_interfaces(self, vdu_details_dict):
        return vdu_details_dict['vm_details']['network_interfaces']

    def format_lfevents(self, lf_events, nsd_id):
        event = 'init'
        string_to_search = lf_events[event]
        format_data = dict()
        configurables =  self.get_configurables(string_to_search)
        if configurables is None:
            return
        for configurable in configurables:
            Delimiter = '#'
            vm_name, parameter = configurable.split(Delimiter)
            vnfd_name = re.sub(r'\d+', '', vm_name).split('-')[0]
            vdu_name = vm_name[len(re.sub(r'\d+', '', vm_name).split('-')[0])+1:]
            #vnfd_name, vdu_name = re.sub(r'\d+', '', vm_name).split('-')
            vdu_dict = self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]
            network_ifaces = self.get_network_interfaces(vdu_dict)
            if parameter in network_ifaces.keys():
               format_data[configurable] = network_ifaces[parameter]['ips'][vm_name.lower()]
        lf_events[event] = string_to_search.format(**format_data)
        return lf_events

    def _generate_vnfm_conf(self, nsd_id):
        vnfm_dict = {}
        vnfm_dict['service'] = {}
        vnfm_dict['service']['nsd_id'] = nsd_id
        current_vnfs = [vdu for vdu in self.ns_dict[nsd_id]['deployed_vdus'] \
                        if vdu not in self.ns_dict[nsd_id]['conf_generated']]
        for vnf in current_vnfs:
            if not self.ns_dict[nsd_id]['is_manager_invoked']:
                vnfm_dict['service']['id'] = self.ns_dict[nsd_id]\
                                                  ['service_name']
                vnfm_dict['service']['fg'] = self.ns_dict[nsd_id]\
                                             ['nsd_template']\
                                             ['postconfigure']\
                                             ['forwarding_graphs']
                vnfm_dict['service']['monitor'] = self.ns_dict[nsd_id]\
                                             ['nsd_template']\
                                             ['postconfigure']\
                                             ['monitoring']
            vnfd_name, vdu_name = vnf.split(':')[0],vnf.split(':')[1]
            if vnfd_name  not in vnfm_dict['service'].keys(): 
                vnfm_dict['service'][vnfd_name] = list()
            vdu_dict = {}
            vdu_dict['name'] = vdu_name
            vdu = self.ns_dict[nsd_id]['vnfds'][vnfd_name]['vdus'][vdu_name]
            for property in vdu:
                if property not in ['preconfigure', 'instances']:
                    if property == 'postconfigure':
                        if 'lifecycle_events' in vdu['postconfigure'].keys():
                            formatted_lfevents = self.format_lfevents(vdu['postconfigure']['lifecycle_events'], nsd_id)
                            vdu['postconfigure']['lifecycle_events'] = formatted_lfevents
                        vdu_dict.update(vdu['postconfigure'])
                    else:
                        vdu_dict[property] = vdu[property]
            vnfm_dict['service'][vnfd_name].append(vdu_dict)
            self.ns_dict[nsd_id]['conf_generated'].append(vnf)

        return vnfm_dict


    def _boot_vdu(self, context, vnfd, nsd_id, **vm_details):
        vdu_id = self.ns_dict[nsd_id]['nsd_template']['vdus'][vnfd]['id']
        launched_instances = self.get_instance_ids(context, vdu_id) 
        if launched_instances == '':
            instance = self.novaclient.server_create(vm_details)
        else:
            index = len(launched_instances.split(","))
            instance = self.novaclient.server_create(vm_details, index=index)
        if vm_details['num_instances'] == 1:
            instance = self.novaclient.get_server(instance.id)
            self.update_vdu_instance_details(context,
                                             instance.id,
                                             self.ns_dict[nsd_id]\
                                             ['nsd_template']['vdus']\
                                             [vnfd]['id'])
            while instance.status != 'ACTIVE' or \
                   all(not instance.networks[iface] \
                   for iface in instance.networks.keys()):
                time.sleep(3)
                instance = self.novaclient.get_server(instance.id)
                if instance.status == 'ERROR':
                    self.update_nsd_status(context, nsd_id, 'ERROR')
                    raise exceptions.InstanceException()
        else:
            instances_list = instance
            instance = list()
            instances_active = 0
            temp_instance = None
            for temp_instance in instances_list:
                self.update_vdu_instance_details(context, temp_instance.id,
                                self.ns_dict[nsd_id]['nsd_template']\
                                ['vdus'][vnfd]['id'])

            while instances_active != vm_details['num_instances'] or \
                  len(instances_list) > 0:
                for inst in instances_list:
                    temp_instance = self.novaclient.get_server(inst.id)
                    if temp_instance.status == 'ACTIVE':
                        instances_active += 1
                        instances_list.remove(inst)
                        instance.append(inst)
                    elif temp_instance.status == 'ERROR':
                        self.update_nsd_status(context, nsd_id, 'ERROR')
                        raise exceptions.InstanceException()
                    else:
                        time.sleep(3)

        return instance
 

    def _set_instance_ip(self, vnfd_name, vdu_name, nsd_id):
        instances = self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                      ['vdus'][vdu_name]['instances']
        ninterfaces = self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                        ['vdus'][vdu_name]['vm_details']['network_interfaces']
        for interface in ninterfaces:
            subnet =self.neutronclient.show_subnet(
                           ninterfaces[interface]['subnet-id'])
            cidr = subnet['subnet']['cidr']
            ninterfaces[interface]['ips'] = self._get_ips(instances, cidr)

        
    def _get_ips(self, instances, cidr):
        ip_list = {}
        for instance in instances:
            instance_name = instance.name
            networks = instance.addresses
            for network in networks.keys():
                for i in range(len(networks[network])):
                    ip = networks[network][i]['addr']
                    if IPAddress(ip) in IPNetwork(cidr):
                       ip_list[instance_name]= ip
        return ip_list 


    def _set_mgmt_ip(self,vnfd_name, vdu_name, nsd_id):
        instances = self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                         ['vdus'][vdu_name]['instances']
        self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                    ['vdus'][vdu_name]['mgmt-ip'] = {}
        mgmt_cidr = self.ns_dict[nsd_id]['nsd_template']['mgmt-cidr']
        for instance in instances:
            networks = instance.addresses
            for network in networks.keys():
                for subnet in networks[network]:
                    ip = subnet['addr']
                    if IPAddress(ip) in IPNetwork(mgmt_cidr):
                        self.ns_dict[nsd_id]['vnfds'][vnfd_name]\
                             ['vdus'][vdu_name]['mgmt-ip'][instance.name] = ip


    def _copy_vnfmanager(self):
        src = self.conf.vnf.vnfmanager
        dest = '/tmp/vnfmanager'
        try:
            dir_util.copy_tree(src, dest)
            return dest
        except OSError as exc:
            raise


    def get_service(self, context, service, **kwargs):
        service = self.get_service_model(context, service, fields=None)
        return service

    def get_services(self,context, **kwargs):
        service=self.get_all_services(context, **kwargs)
        return service

    def _get_manager_info(self, context):
        return self.get_manager_info(context)


    def _make_tar(self, vnfmanager_path):
        tar = tarfile.open(vnfmanager_path+'.tar.gz', 'w:gz')
        tar.add(vnfmanager_path)
        tar.close() 
        return vnfmanager_path+'.tar.gz'


    def _invoke_vnf_manager(self, context, nsd_id):
        """Invokes VNF manager using ansible(if multihost)"""
        vnfm_conf_dict = self._generate_vnfm_conf(nsd_id)
        with open(self.ns_dict[nsd_id]['vnfm_dir'] + '/' + \
                  self.ns_dict[nsd_id]['vnfmanager_uuid']+'.yaml', 'w') as f:
            yaml.safe_dump(vnfm_conf_dict, f)
        vnfm_conf = self.ns_dict[nsd_id]['vnfm_dir'] + '/' + \
                    self.ns_dict[nsd_id]['vnfmanager_uuid']+'.yaml'
        vnfsvc_conf = cfg.CONF.config_file[0]
        

        ovs_path,p_id = self._create_ovs_script(self.ns_dict[nsd_id]\
                                           ['nsd_template']\
                                           ['networks']['mgmt-if']['id'],
                                           nsd_id)
        vnfm_host =  self.novaclient.check_host(cfg.CONF.vnf.compute_hostname)
        if cfg.CONF.vnf.vnfmconf == "local":
            confcmd  = 'vnf-manager ' + \
                       '--config-file /etc/vnfsvc/vnfsvc.conf'\
                       ' --vnfm-conf-dir ' + \
                       self.ns_dict[nsd_id]['vnfm_dir'] + \
                       '/ --log-file ' + self.ns_dict[nsd_id]['vnfm_dir'] + \
                       '/vnfm.log --uuid ' + \
                       self.ns_dict[nsd_id]['vnfmanager_uuid']

            ovscmd =  'sudo sh '+ self.ns_dict[nsd_id]['vnfm_dir'] + '/ovs.sh'
            proc = subprocess.Popen(ovscmd, shell=True)
            proc2 = subprocess.Popen(confcmd.split(),
                                     stderr=open('/dev/null', 'w'),
                                     stdout=open('/dev/null', 'w'))

        elif cfg.CONF.vnf.vnfmconf == "ansible":
            with open(self.ns_dict[nsd_id]['vnfm_dir']+'/hosts', 'w') as hosts_file:
                 hosts_file.write("[server]\n%s\n"%(vnfm_host.host_ip))
            vnfm_home_dir =  '{{ ansible_env["HOME"] }}/.vnfm/' +self.ns_dict[nsd_id]\
                                                         ['vnfmanager_uuid']

            ansible_dict=[{'tasks': [
                            {'ignore_errors': True, 'shell': 'mkdir -p '+\
                          vnfm_home_dir},
                            {'copy': 'src='+ vnfsvc_conf +' dest='+\
                          vnfm_home_dir+'/vnfsvc.conf'},
                            {'copy': 'src='+ vnfm_conf + ' dest=' + \
                          vnfm_home_dir + '/' + \
                          self.ns_dict[nsd_id]['vnfmanager_uuid'] + \
                          '.yaml'},
                            {'async': 1000000, 'poll': 0,
                          'command': 'vnf-manager --config-file '+ \
                          vnfm_home_dir + '/vnfsvc.conf --vnfm-conf-dir '+ \
                          vnfm_home_dir + '/ --log-file ' + vnfm_home_dir + \
                          '/vnfm.log --uuid %s'
                          % self.ns_dict[nsd_id]['vnfmanager_uuid'],
                          'name': 'run manager'},
                            {'copy': 'src='+ ovs_path + ' dest=' + \
                          vnfm_home_dir + '/ovs.sh'},
                            {'ignore_errors': True, 'shell': 'sh '+ \
                          vnfm_home_dir + '/ovs.sh', 'register': 'result1'},
                            {'debug': 'var=result1.stdout_lines'},
                        ], 'hosts': 'server', 'remote_user': \
                          cfg.CONF.vnf.compute_user}]

         
            with open(self.ns_dict[nsd_id]['vnfm_dir'] +\
                      '/vnfmanager-playbook.yaml', 'w') as yaml_file:
                yaml_file.write( yaml.dump(ansible_dict, 
                                           default_flow_style=False))
            LOG.debug(_('----- Launching VNF Manager -----'))

            child = pexpect.spawn('ansible-playbook ' +\
                                  self.ns_dict[nsd_id]['vnfm_dir'] +\
                                  '/vnfmanager-playbook.yaml -i ' +\
                                  self.ns_dict[nsd_id]['vnfm_dir'] +\
                                  '/hosts --ask-pass', timeout=None)
            child.expect('SSH password:')
            child.sendline(cfg.CONF.vnf.ssh_pwd)
            result =  child.readlines()
        self.agent_mapping[self.ns_dict[nsd_id]['vnfmanager_uuid']] =\
                      VNFManagerAgentApi(topics.get_topic_for_mgr(
                                     self.ns_dict[nsd_id]['vnfmanager_uuid']),
                                         cfg.CONF.host, self)
        nc = self.neutronclient
        body = {'port': {'binding:host_id': cfg.CONF.vnf.compute_hostname}}
        v_port_updated = nc.update_port(p_id,body)
        self.ns_dict[nsd_id]['is_manager_invoked'] = True
        self._resolve_dependency(context, nsd_id)


    def _create_ovs_script(self, mgmt_id, nsd_id):
        nc = self.neutronclient
        v_port = nc.create_port({'port':{'network_id': mgmt_id}})
        p_id = v_port['port']['id']
        mac_address = v_port['port']['mac_address']
        lines_dict = []
        lines_dict.append('#!/bin/sh\n')
        lines_dict.append('sudo ovs-vsctl add-port br-int vtap-%s \
                -- set interface vtap-%s type=internal \
                -- set interface vtap-%s external-ids:iface-id=%s \
                -- set interface vtap-%s external-ids:iface-status=active \
                -- set interface vtap-%s external-ids:attached-mac=%s\n'
                %(str(p_id)[:8],str(p_id)[:8],str(p_id)[:8],str(p_id),
                  str(p_id)[:8],str(p_id)[:8],str(mac_address)))

        lines_dict.append('sudo ifconfig vtap-%s %s up\n'
                %(str(p_id)[:8],str(v_port['port']['fixed_ips'][0]\
                  ['ip_address'])))

        with open(self.ns_dict[nsd_id]['vnfm_dir']+'/ovs.sh', 'w') as f:
            f.writelines(lines_dict)
        return self.ns_dict[nsd_id]['vnfm_dir']+'/ovs.sh',str(p_id)
  
    def push_monitoringKPI(self, kpi_value, nsd_id, timestamp):
        self.monitoring_db.record_kpi_data(kpi_value, nsd_id, timestamp) 
  
    def get_metric(self, context, metric, **kwargs):
        query_dict = {'resource': metric}
        sample_filter = monitoring.SampleFilter(**query_dict)
        sample = self.monitoring_db.get_kpi_data(sample_filter)
        metric = {}
        for key in sample[0].keys():
            if key == 'nsd_id':
               metric['id'] = sample[0][key]
            else:
               metric[key] = str(sample[0][key])
        return metric

    def get_metrics(self, context, **kwargs):
        query_dict = {'resource': kwargs['filters']['id'][0] if 'id' in kwargs['filters'].keys() else kwargs['filters']['name'][0]}
        sample_filter = monitoring.SampleFilter(**query_dict)
        sample = self.monitoring_db.get_kpi_data(sample_filter)
        metric = []
        for idx in range(0,len(sample)):
            tmp = {} 
            for key in sample[idx].keys():
               if key == 'nsd_id':
                  tmp['id'] = sample[idx][key]
               else:
                  tmp[key] = sample[idx][key]
            metric.append(tmp)
        return metric

    def build_acknowledge_list(self, context, vnfd_name, vdu_name, instance, status, nsd_id):
        vdu = vnfd_name+':'+vdu_name
        if status == 'ERROR':
            self.ns_dict[nsd_id]['errored'].append(vdu)
            self.update_nsd_status(context, nsd_id, 'ERROR')
        else:
            #check whether the key exists or not
            if self.ns_dict[nsd_id]['acknowledge_list'].get(vdu, None):
                self.ns_dict[nsd_id]['acknowledge_list'][vdu].append(instance)
            else:
                self.ns_dict[nsd_id]['acknowledge_list'][vdu] = [instance]

            # Check whether all the instances of a specific VDU 
            # are acknowledged
            vdu_instances = len(self.ns_dict[nsd_id]['vnfds'] \
                                [vnfd_name]['vdus'][vdu_name]['instances'])
            current_instances = len(self.ns_dict[nsd_id] \
                                    ['acknowledge_list'][vdu])
            if vdu_instances <= current_instances:
                self.ns_dict[nsd_id]['configured'].append(vdu)


    def create_template(self, context, template):
        json_dict = {}
        template_json = json.load(open(self.conf.vnf.templates, 'r'))
        newpath = self.conf.state_path+"/templates/"+template['template']['name']
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        for files in template['template']['files']:
            pyaml.dump(json.JSONDecoder(object_pairs_hook=OrderedDict).decode(template['template']['files'][files]),open(newpath+"/"+files,'w+'))
            for key in template_json.keys():
                if files.find(key) == 0:
                    template_json[key][files[len(key)+1:files.find('.')]] = newpath+"/"+files
                json_dict[key] = template_json[key].keys()
            with open(self.conf.vnf.templates, 'w') as outfile:
                json.dump(template_json, outfile, indent=2, sort_keys=True)
        return json_dict


    def get_templates(self, context, filters, fields=None):
        json_dict = {}
        json_list = []
        template_json = json.load(open(self.conf.vnf.templates, 'r'))
        for key in template_json.keys():
            json_dict[key] = ', '.join(template_json[key].keys())
        json_list.append(json_dict)
        return json_list


    def create_scale(self, context, scale):
        try:
            scale = scale['scale']
            nsd_id = scale['nsd_id']
            policy_name = scale['policy_name']
            policy_details = self.get_policy_details(context, nsd_id, policy_name)
            status = self.get_network_service_status(context, nsd_id)
            if status != 'ACTIVE' or status == None:
                raise Exception()
            vdus = policy_details.VDUs.split(",")
            if len(vdus) == 0:
                raise Exception()
            elif len(vdus) == 1 and vdus[0] == '':
                raise Exception()
            else:
                action = policy_details.action.replace('-', '_')
                result = getattr(self, action)(context, nsd_id, vdus)
                if result['status'] ==  'COMPLETE':
                    self.update_nsd_status(context, nsd_id, 'ACTIVE')
                    curr_time = str(datetime.datetime.utcnow()).split("-")
                    curr_time[2] = curr_time[2].split(".")[0]
                    curr_time[2] = curr_time[2].split()
                    curr_time[2] = "".join(curr_time[2])
                    curr_time[2] = "".join(curr_time[2].split(":"))
                    self.update_timestamp(context, nsd_id, policy_name, "".join(curr_time))
                    return result
        except Exception:
            self.update_nsd_status(context, nsd_id, 'ACTIVE')
            LOG.debug(_("An exception occured while scaling %s policy for network service %s"), policy_name, nsd_id)
    
    def scale_out(self, context, nsd_id, vdus):
        self.update_nsd_status(context, nsd_id, 'IN PROGRESS')
        for vdu in vdus:
            self.ns_dict[nsd_id]['configured'].remove(vdu) 
            while vdu in self.ns_dict[nsd_id]['conf_generated']:
                self.ns_dict[nsd_id]['conf_generated'].remove(vdu)
            self.ns_dict[nsd_id]['deployed_vdus'].remove(vdu) 
            self._launch_vnfds(vdu, context, nsd_id, method='scale')
            conf =  self._generate_vnfm_conf(nsd_id)
            self.agent_mapping[self.ns_dict[nsd_id]['vnfmanager_uuid']].\
                  scale_vdu(context, conf=conf)
            self.wait_for_acknowledgment([vdu], nsd_id) 
            dependents = self.ns_dict[nsd_id]['dependency_dict'][vdu]['updatesTo']
            for i in range(0, len(dependents)):
                self.ns_dict[nsd_id]['configured'].remove(dependents[i]) 
                self.agent_mapping[self.ns_dict[nsd_id]['vnfmanager_uuid']].\
                      update_vdu(context, scaled_vdu=vdu.split(':')[-1], config_vdu=dependents[0].split(':')[-1])
                self.wait_for_acknowledgment([dependents[i]], nsd_id)

        return {
            'nsd_id': nsd_id,
            'status': 'COMPLETE'
        }


    def push_monitoringKPI(self, kpi_value, nsd_id, timestamp):
        self.monitoring_db.record_kpi_data(kpi_value, nsd_id, timestamp)


    def get_metric(self, context, metric, **kwargs):
        query_dict = {'resource': metric}
        sample_filter = monitoring.MetricFilter(**query_dict)
        sample = self.monitoring_db.get_kpi_data(sample_filter)
        metric = {}
        for key in sample[0].keys():
            if key == 'nsd_id':
               metric['id'] = sample[0][key]
            else:
               metric[key] = str(sample[0][key])
        return metric


    def get_metrics(self, context, **kwargs):
        metric = []
        service = kwargs['filters']['id'][0] if 'id' in kwargs['filters'].keys() else kwargs['filters']['name'][0]
        if self.get_service_model(context, service, fields=None):
            query_dict = {'resource': service}
            #query_dict = {'resource': kwargs['filters']['id'][0] if 'id' in kwargs['filters'].keys() else kwargs['filters']['name'][0]}
            sample_filter = monitoring.MetricFilter(**query_dict)
            sample = self.monitoring_db.get_kpi_data(sample_filter)
            for idx in range(0,len(sample)):
                tmp = {}
                for key in sample[idx].keys():
                   if key == 'nsd_id':
                      tmp['id'] = sample[idx][key]
                   else:
                      tmp[key] = sample[idx][key]
                metric.append(tmp)
        else:
            LOG.debug(_("Requested network service doesn't exists !!"))
        return metric


class VNFManagerAgentApi(v_rpc.RpcProxy):
    """Plugin side of plugin to agent RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, host, plugin):
        super(VNFManagerAgentApi, self).__init__(topic, self.API_VERSION)
        self.host = host
        self.plugin = plugin


    def configure_vdus(self, context, conf):
        return self.cast(
            context,
            self.make_msg('configure_vdus', conf=conf),
        )

    def scale_vdu(self, context, conf):
        return self.cast(
            context,
            self.make_msg('scale_vdu', conf=conf),
        )

## ADDED BY ANIRUDH
    def update_vdu_configuration(self, context, vdu_name, conf):
        return self.call(
            context,
            self.make_msg('update_vdu_configuration', vdu_name=vdu_name, configuration=conf),
        )
## ENDS HERE

    def update_vdu(self, context, scaled_vdu, config_vdu):
        return self.cast(
            context,
            self.make_msg('update_vdu', scaled_vdu=scaled_vdu, config_vdu=config_vdu),
        )

    def send_statistics(self,context,statistics):
        return self.cast(
            context,
            self.make_msg('send_statistics', statistics=statistics)
        )


class VNFManagerCallbacks(v_rpc.RpcCallback):
    RPC_API_VERSION = '1.0'

    def __init__(self, plugin):
        super(VNFManagerCallbacks, self).__init__()
        self.plugin = plugin

    def send_ack(self, context, vnfd, vdu, instance, status, nsd_id):
        if status == 'COMPLETE':
            self.plugin.build_acknowledge_list(context, vnfd, vdu, instance,
                                               status, nsd_id)
            LOG.debug(_('ACK received from VNF Manager: '
                        'Configuration complete for VNF %s'), instance)
        else:
            self.plugin.build_acknowledge_list(context, vnfd, vdu, instance,
                                               status, nsd_id)
            LOG.debug(_('ACK received from VNF Manager: '
                        'Confguration failed for VNF %s'), instance)

    def push_monitoringKPI(self, context, statistics, nsd_id, timestamp):
        LOG.debug(_('Key Performance Indication Received %s'), statistics)
        self.plugin.push_monitoringKPI(statistics, nsd_id, timestamp)



class VNFMonitorRPCHandler(v_rpc.RpcCallback, vnf_db.NetworkServicePluginDb):
    RPC_API_VERSION = '1.0'

    def __init__(self, plugin):
        super(VNFMonitorRPCHandler, self).__init__()
        self.plugin = plugin
        self.agent_mapping = dict()

    def monitoring(self, context, statistics):
        try:
            service_dict = self.plugin._get_manager_info(context)
            if service_dict:
                for vnfm in service_dict.keys():
                    stats_details = {vdu:statistics[vdu] for vdu in service_dict[vnfm]}
                    LOG.debug(_("Statistics Details: %s"),stats_details)
                    LOG.debug(_("****** Stats to be sent to: %s"), vnfm)
                    vnf_api = VNFManagerAgentApi(
                                  topics.get_topic_for_mgr(vnfm),
                                  cfg.CONF.host, self.plugin)
                    self.agent_mapping[vnfm] = vnf_api
                    self.agent_mapping[vnfm].send_statistics(context, statistics=stats_details)
        except Exception:
            pass
        return"rutoiruy"
