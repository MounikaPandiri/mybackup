# Copyright (c) 2014 Tata Consultancy Services Limited(TCSL). 
# Copyright 2012 OpenStack Foundation
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

import os
import sys
import threading
import time

import yaml
import itertools
import eventlet
eventlet.monkey_patch()

from oslo.config import cfg
from oslo import messaging
from oslo.utils import timeutils

from vnfmanager import config
from vnfmanager import context
from vnfmanager import manager
from vnfmanager.openstack.common import loopingcall
from vnfmanager.openstack.common import service
from vnfmanager.openstack.common import log as logging
from vnfmanager.openstack.common.gettextutils import _

from vnfmanager.agent import rpc as agent_rpc
from vnfmanager.common import config as common_config
from vnfmanager.common import rpc as v_rpc
from vnfmanager.common import topics
from vnfmanager import service as vnfsvc_service
from vnfmanager.openstack.common import uuidutils as uuid
from vnfmanager.openstack.common import importutils
from vnfmanager.common import exceptions

LOG = logging.getLogger(__name__)

command_opts = [cfg.StrOpt('uuid', default=None, 
                help='VNF manager identifier'),
                cfg.StrOpt('vnfm-conf-dir', default=None,  
                help='VNF manager identifier')]
cfg.CONF.register_cli_opts(command_opts)

AGENT_VNF_MANAGER = 'VNF manager agent'
_monitor_drv = 'vnfmanager.monitoring.driver.'
launchd_threads_info = dict()

class ImplThread(threading.Thread):
    def __init__(self, target, condition, *args, **kwargs):
        global launchd_threads_info
        self._id = kwargs['_id']
        self._condition = condition
        self._target = target
        self._args = args
        self._thr_info = launchd_threads_info
        threading.Thread.__init__(self)

    def run(self):
        try:
           self.return_vals = self._target(*self._args)
        except Exception:
           self.return_vals = 'Error'
        self._condition.acquire()
        self._thr_info[self._id]['result'] = self.return_vals
        self._condition.notify()
        self._condition.release()

class VNFManager(manager.Manager):

    def __init__(self, host=None):
        super(VNFManager, self).__init__(host=host)
        self.vplugin_rpc = VNFPluginCallbacks(topics.PLUGIN,
                                               cfg.CONF.host)
        self.needs_resync_reasons = []
        self.drv_conf = dict()
        self.conf = cfg.CONF
        self.ctx = context.get_admin_context_without_session()
        self.ns_config = dict()
        self.nsd_id = self.conf.vnfm_conf_d['service']['nsd_id']
        #self.ns_config['fg'] = self.conf.vnfm_conf_d['service']['fg']
        self.monitor = self.conf.vnfm_conf_d['service']['monitor']
        self._extract_monitor_drv()
        self._condition = threading.Condition()
        monitor_daemon = threading.Thread(target=self.monitor_thread_pool)
        monitor_daemon.setDaemon(True)
        LOG.warn(_("Waiter Daemon Starting"))
        self.configure_vdus(self.ctx, self.conf.vnfm_conf_d)
        monitor_daemon.start()


    def monitor_thread_pool(self, thread_info=None, condition=None):
        global launchd_threads_info
        if thread_info is None:
            thread_info = launchd_threads_info
        if condition is None:
            condition = self._condition
        while True:
            condition.acquire()
            for each_thread in iter(thread_info.keys()):
                if 'result' in thread_info[each_thread].keys():
                    LOG.debug(_("Worker Thread # for VNF configuration Ending"), thread_info[each_thread])
                    LOG.debug(_("%s"), thread_info)
                    status = 'ERROR' if 'ERROR' in str(thread_info[each_thread]['result']) else 'COMPLETE' 
                    self.vplugin_rpc.send_ack(self.ctx,
                                               thread_info[each_thread]['vnfd'],
                                               thread_info[each_thread]['vdu'],
                                               thread_info[each_thread]['vm_name'],
                                               status,
                                               self.nsd_id)
                    if status == "COMPLETE":
                        self.drv_conf[thread_info[each_thread]['vdu']]['COMPLETE'].append(thread_info[each_thread]['vm_name'])
                    if thread_info[each_thread]['thread_obj'].isAlive():
                        thread_info[each_thread]['thread_obj'].kill()
                    del(thread_info[each_thread])
            condition.wait()
            condition.release()


    def _extract_monitor_drv(self):
        global _monitor_drv
        if self.monitor:
            LOG.debug(_("Loading Monitoring driver for the network service"))
            self._monitor_drv_path = _monitor_drv + self.monitor['driver']
            self._monitor_driver = importutils.import_object(self._monitor_drv_path)


    def send_statistics(self, context, statistics):
        LOG.warn(_("statistics is %s"),statistics)
        self.vplugin_rpc.push_monitoringKPI(context, self._monitor_driver.compute(statistics),
                                            self.nsd_id, timeutils.utcnow())


    def _extract_drivers(self, vnfm_conf):
        vnfds = list(set(vnfm_conf.keys()) - set(['id','nsd_id','fg', 'monitor']))
        vnfd_details = dict()
        for vnfd in vnfds:
            for vdu in range(0,len(vnfm_conf[vnfd])):
                vdu_name = vnfm_conf[vnfd][vdu]['name']
                if vdu_name not in self.drv_conf.keys():
                    vnfd_details[vdu_name] = dict()
                    vnfd_details[vdu_name]['_instances'] = vnfm_conf[vnfd][vdu]['instance_list']
                    vnfd_details[vdu_name]['_driver'] = vnfm_conf[vnfd][vdu]['mgmt-driver'] if vnfm_conf[vnfd][vdu]['mgmt-driver'] is not '' else None
                    vnfd_details[vdu_name]['_lc_events'] = vnfm_conf[vnfd][vdu]['lifecycle_events']
                    vnfd_details[vdu_name]['_vnfd'] = vnfd
                    vnfd_details[vdu_name]['idx'] = vdu
                    vnfd_details[vdu_name]['COMPLETE'] = list()
                    vnfd_details[vdu_name]['_username'] = vnfm_conf[vnfd][vdu]['vm_details']['image_details']['username']
                    vnfd_details[vdu_name]['_password'] = vnfm_conf[vnfd][vdu]['vm_details']['image_details']['password']
                    vnfd_details[vdu_name]['_mgmt_ips'] = vnfm_conf[vnfd][vdu]['mgmt-ip']
        return vnfd_details


    def _populate_vnfd_drivers(self, drv_conf):
        vnfd_drv_cls_path = drv_conf['_driver']
        username = drv_conf['_username']
        password = drv_conf['_password']
        lf_events = drv_conf['_lc_events']
        try:
            drv_conf['_drv_obj'] = importutils.import_object(vnfd_drv_cls_path,
                                                             self.ns_config,
                                                             username = username, 
                                                             password = password,
                                                             lifecycle_events = lf_events)
        except Exception:
            LOG.warn(_("%s driver not Loaded"), vnfd_drv_cls_path)
            raise


    def _configure_service(self, vdu, instance, mgmt_ip):
        status = "ERROR"
        try:
            #vdu['_drv_obj'].configure_service(instance)
            LOG.debug(_("Configuration of VNF being carried out on VDU:%s with IP:%s"), vdu, mgmt_ip)
            status = vdu['_drv_obj'].push_configuration(instance, mgmt_ip)
        except exceptions.DriverException or Exception:
            LOG.exception(_("Configuration of VNF Failed!!"))
        finally:
            return status

    def _get_vdu_from_conf(self, conf):
        return conf[conf.keys()[0]][0]['name']


    def configure_vdus(self, context, conf):
        curr_drv_conf = dict()
        vnfds = list(set(conf['service'].keys()) - set(['nsd_id' , 'id', 'fg']))
        for vnfd in vnfds:
            if vnfd not in self.ns_config.keys():
                self.ns_config[vnfd]= list()
            self.ns_config[vnfd].extend(conf['service'][vnfd])

        curr_drv_conf = self._extract_drivers(conf['service'])

        if curr_drv_conf:
            for vdu in curr_drv_conf:
                if not curr_drv_conf[vdu]['_driver']:
                   self.drv_conf.update(curr_drv_conf)
                   continue
                self._populate_vnfd_drivers(curr_drv_conf[vdu])
                self.drv_conf.update(curr_drv_conf)

        LOG.info(self.ns_config)
        for vdu_name in curr_drv_conf:
            if not curr_drv_conf[vdu_name]['_driver']:
                status = 'COMPLETE' 
                for instance in curr_drv_conf[vdu_name]['_instances']:
                    self.vplugin_rpc.send_ack(context, curr_drv_conf[vdu_name]['_vnfd'],
                                              vdu_name,
                                              instance,
                                              status,
                                              self.nsd_id)
                    self.drv_conf[vdu_name][status].append(instance)
                continue
            else:
                self._configure_vdu(vdu_name)


    def scale_vdu(self, context, conf):
        if conf is not None:
           conf = conf['service']
           vnfds = list(set(conf.keys()) - set(['nsd_id']))
           for vnfd in vnfds:
                if vnfd in self.ns_config.keys():
                    for new_vdu in range(0, len(conf[vnfd])):
                        new_vdu_name =  conf[vnfd][new_vdu]['name']
                        for exist_vdu in range(0, len(self.ns_config[vnfd])):
                            if new_vdu_name == self.ns_config[vnfd][exist_vdu]['name']:
                                self.ns_config[vnfd][exist_vdu] = conf[vnfd][new_vdu]
                              
                                if new_vdu_name in self.drv_conf.keys():
                                    if vnfd == self.drv_conf[new_vdu_name]['_vnfd']:
                                        self.drv_conf[new_vdu_name]['_instances'] = conf[vnfd][new_vdu]['instance_list']
                                        self.drv_conf[new_vdu_name]['_mgmt_ips'] = conf[vnfd][new_vdu]['vm_details']['network_interfaces']['management-interface']['ips']
                                self._configure_vdu(new_vdu_name, scale=True)
                                break 

    def update_vdu(self, context, scaled_vdu, config_vdu):

        if scaled_vdu:
            if self.drv_conf[scaled_vdu]:
                for instance in self.drv_conf[scaled_vdu]['_instances']:
                    if instance not in self.drv_conf[scaled_vdu]['COMPLETE']:
                        LOG.warn(_("Configuration not completed for instance %s , belongs to %s "),
                                  instance_name, scaled_vdu)
                        raise Exception
        else:
            raise Exception
            LOG.warn(_("Scaled VDU information is empty!!"))

        if config_vdu:
            if self.drv_conf[config_vdu]:
                del self.drv_conf[config_vdu]['COMPLETE'][:]
                self._configure_vdu(config_vdu)

        else:
            raise Exception
            LOG.warn(_("To Update VDU information is empty!!"))

                

    def _configure_vdu(self, vdu_name, scale=False):
        status = ""
        for instance in range(0,len(self.drv_conf[vdu_name]['_instances'])):
            instance_name = self.drv_conf[vdu_name]['_instances'][instance]
            if instance_name not in self.drv_conf[vdu_name]['COMPLETE']:
                try:
                    if not self.drv_conf[vdu_name]['_driver']:
                        status = 'COMPLETE'
                        self.vplugin_rpc.send_ack(self.ctx, self.drv_conf[vdu_name]['_vnfd'],
                                              vdu_name,
                                              instance_name,
                                              self.drv_conf[vdu_name]['_mgmt_ips'][instance_name],
                                              status,
                                              self.nsd_id)
                        self.drv_conf[vdu_name][status].append(instance_name)
                    else:
                        self._invoke_driver_thread(self.drv_conf[vdu_name],
                                               instance_name,
                                               vdu_name,
                                               self.drv_conf[vdu_name]['_mgmt_ips'][instance_name],
                                               scale)
                        status = 'COMPLETE'
                except Exception:
                    status = 'ERROR'
                    LOG.warn(_("Configuration Failed for VNF %s"), instance_name)
                    self.vplugin_rpc.send_ack(self.ctx,
                                              self.drv_conf[vdu_name]['_vnfd'],
                                              vdu_name,
                                          instance_name,
                                          status,
                                          self.nsd_id)
        return status


    def _invoke_driver_thread(self, vdu, instance, vdu_name, mgmt_ip, scale=False):
        global launchd_threads_info
        LOG.debug(_("Configuration of the remote VNF %s being intiated"), instance)
        _thr_id = str(uuid.generate_uuid()).split('-')[1]   
        try:
            if scale:
                driver_thread = ImplThread(self._configure_service, self._condition, vdu, instance, mgmt_ip, _id = _thr_id)
            else:
                driver_thread = ImplThread(self._configure_service, self._condition, vdu, instance, mgmt_ip, _id = _thr_id)
            self._condition.acquire()
            launchd_threads_info[_thr_id] = {'vm_name': instance, 'thread_obj': driver_thread, 'vnfd': vdu['_vnfd'], 'vdu':vdu_name}
            self._condition.release()
            driver_thread.start()
        except RuntimeError:
            LOG.warning(_("Configuration by the Driver Failed!"))


    def validate_scaling(self):
       return "VALID"


class VNFPluginCallbacks(v_rpc.RpcProxy):
    """Manager side of the vnf manager to vnf Plugin RPC API."""

    def __init__(self, topic, host):
        RPC_API_VERSION = '1.0'
        super(VNFPluginCallbacks, self).__init__(topic, RPC_API_VERSION)

    def send_ack(self, context, vnfd, vdu, instance, status, nsd_id):
        return self.call(context,
                         self.make_msg('send_ack', vnfd=vnfd, vdu=vdu,
                                        instance=instance, status=status, nsd_id=nsd_id))

    def push_monitoringKPI(self, context, statistics, nsd_id, timestamp):
        return self.cast(context,
                         self.make_msg('push_monitoringKPI', statistics=statistics,
                                        nsd_id=nsd_id, timestamp=timestamp))


class VNFMgrWithStateReport(VNFManager):
    def __init__(self, host=None):
        super(VNFMgrWithStateReport, self).__init__(host=cfg.CONF.host)
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.PLUGIN)
        self.agent_state = {
            'binary': 'vnf-manager',
            'host': host,
            'topic': topics.set_topic_name(self.conf.uuid, prefix=topics.VNF_MANAGER),
            'configurations': {
                'agent_status': 'COMPLETE',
                'agent_id': cfg.CONF.uuid
                },
            'start_flag': True,
            'agent_type': AGENT_VNF_MANAGER}
        report_interval = 60
        self.use_call = True
        if report_interval:
            self.heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            self.heartbeat.start(interval=report_interval)


    def _report_state(self):
        try:
            self.agent_state.get('configurations').update(
                self.cache.get_state())
            ctx = context.get_admin_context_without_session()
            self.state_rpc.report_state(ctx, self.agent_state, self.use_call)
        except AttributeError:
            # This means the server does not support report_state
            LOG.warn(_("VNF server does not support state report."
                       " State report for this agent will be disabled."))
            self.heartbeat.stop()
            return
        except Exception:
            LOG.exception(_("Failed reporting state!"))
            return


def load_vnfm_conf(conf_path):
    conf_doc = open(conf_path, 'r')
    conf_dict = yaml.load(conf_doc)
    OPTS = [cfg.DictOpt('vnfm_conf_d', default=conf_dict)]
    cfg.CONF.register_opts(OPTS)


def _register_opts(conf):
    config.register_agent_state_opts_helper(conf)
    config.register_root_helper(conf)


def read_sys_args(arg_list):
    """ Reads a command-line arguments and returns a dict 
        for easier processing of cmd args and useful when 
        a number of args need to specified for the service
        without ordering them in a specific order. """
    arg_l = [arg if uuid.is_uuid_like(arg) else \
                             arg.lstrip('-').replace('-','_') for arg in arg_list[1:]]
    return dict(itertools.izip_longest(*[iter(arg_l)] * 2, fillvalue=""))


def main(manager='vnfmanager.vnf_manager.VNFMgrWithStateReport'):

    # placebo func to replace the server/__init__ with project startup. 
    # pool of threads needed to spawn worker threads for RPC.
    # Default action for project's startup, explictly maintainly a pool
    # for manager as it cannot inherit the vnfsvc's thread pool.
    pool = eventlet.GreenPool()
    pool.waitall()

    conf_params = read_sys_args(sys.argv)
    _register_opts(cfg.CONF)
    common_config.init(sys.argv[1:])
    uuid = conf_params['uuid']
    config.setup_logging(cfg.CONF)
    LOG.warn(_("UUID: %s"), uuid)
    vnfm_conf_dir = conf_params['vnfm_conf_dir'].split("/")
    vnfm_conf_dir[-2] = uuid
    vnfm_conf_dir = "/".join(vnfm_conf_dir)
    vnfm_conf_path = vnfm_conf_dir+uuid+'.yaml'
    load_vnfm_conf(vnfm_conf_path)
    server = vnfsvc_service.Service.create(
                binary='vnf-manager',
                topic=topics.set_topic_name(uuid, prefix=topics.VNF_MANAGER),
                report_interval=60, manager=manager)
    service.launch(server).wait()

