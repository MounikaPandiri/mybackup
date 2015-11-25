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
import os
import sys
import time
from oslo_config import cfg
from vnfsvc.client import client 
from vnfsvc import messaging
from vnfsvc.openstack.common import gettextutils
from vnfsvc.openstack.common.gettextutils import _
from vnfsvc.openstack.common import service as os_service
from vnfsvc import config
from vnfsvc import context
from vnfsvc.common import constants
from vnfsvc.openstack.common import loopingcall
from vnfsvc.openstack.common import service
from vnfsvc.openstack.common import log
from vnfsvc.openstack.common import gettextutils as gettextutils

from vnfsvc.agent import rpc as agent_rpc
from vnfsvc.common import config as common_config
from vnfsvc.common import rpc as v_rpc
from vnfsvc.common import topics
from vnfsvc import service as vnfsvc_service
from vnfsvc.openstack.common import uuidutils
from vnfsvc.openstack.common import importutils
from collections import defaultdict
import itertools
import datetime
# NOTE: Have to import raw rpc file as v_rpc
#cfg.CONF.register_opts(OPTS, 'vnf')

OPTS = [
    cfg.IntOpt("monitoring_interval",
                default=20,
                help='Period of evaluation cycle, should'
                     ' be >= than configured pipeline interval for'
                     ' collection of underlying metrics.'),
    cfg.ListOpt("meter_list",
                default=None,
                help=' List of meters for which metrics'
                     ' has to be collected from ceilometer'),

]

cfg.CONF.register_opts(OPTS, 'monitor')
CONF = cfg.CONF


LOG = log.getLogger(__name__)

class UtilizationMonitorService(os_service.Service):

    MONITOR_NAMESPACE = 'vnfsvc.monitor'

    def __init__(self):
        super(UtilizationMonitorService, self).__init__()
        self.rpc_server = VNFMonitorRpcApi(
                              topics.PLUGIN,
                              cfg.CONF.host)
        #self.nova_cli = client.NovaClient()
        self.start()
   
    def start(self):
        super(UtilizationMonitorService, self).start()
        wait_interval = cfg.CONF.monitor.monitoring_interval
        self.tg.add_timer(wait_interval, self.check_vnf_util_and_notify, 0)
        self.tg.add_timer(604800, lambda: None)

    def _get_statistics(self):
        statistics = {}
        for meter in cfg.CONF.monitor.meter_list:
            timestamp_now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            timestamp_before = (datetime.datetime.utcnow() - datetime.timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S')
            statistics[meter] = self.ceiloclient.query_samples(meter_name=meter,timestamp1=timestamp_before,                                                                     timestamp2=timestamp_now)
        return statistics


    def check_vnf_util_and_notify(self):
        self.ceiloclient = client.CeilometerClient()
        LOG.info("Checking for the vnf Utilization")
        utility_statistics = {}
        util_dict = {}
        cpu_avg = {}
        nw_avg = {}
        cpu_util = defaultdict(list)
        nw_util = {}
        statistics_dict={}
        resource_list_new = []
        networking_dict = {}
        utility_statistics = self._get_statistics()
        print  utility_statistics
        for util in utility_statistics:
            if util == 'cpu_util':
                for util_stats in utility_statistics[util]:
                    cpu_util[util_stats.resource_id].append(util_stats.counter_volume)
                for vnf in cpu_util.keys():
                    cpu_stats = 0
                    for val in iter(cpu_util[vnf]):
                        cpu_stats = cpu_stats+val
                    avg = cpu_stats/len(cpu_util[vnf])
                    cpu_avg[vnf]= {'cpu_util': avg}
                util_dict.update(cpu_avg)

            else:
                for util_stats in utility_statistics[util]:
                    nw_util_lst = []
                    if util_stats.resource_id not in nw_util.keys():
                        nw_util[util_stats.resource_id] = {}
                    nw_util_lst.append(util_stats.counter_volume)
                    nw_util[util_stats.resource_id].update({ util: nw_util_lst})
                for vnf in nw_util.keys():
                    nw_avg[vnf] = {}
                    sum1 = 0
                    for stats in nw_util[vnf].keys():
                        sum_avg = sum(nw_util[vnf][stats])
                        avg = sum_avg/len(nw_util[vnf][stats])
                        nw_avg[vnf][stats] = avg
                util_dict.update(nw_avg)


        for key in util_dict.keys():
            if key.find('instance')<0:
               resource_list_new.append(key)
        for key in resource_list_new:
           statistics_dict[key] = {}
           networking_dict['network.outgoing.bytes'] = {}
           networking_dict['network.incoming.bytes'] = {}
           for resource_id in util_dict:
               if resource_id.find(key)>=0 and resource_id.find('tap')>=0:
                   if 'network.incoming.bytes' in util_dict[resource_id]:
                       networking_dict['network.incoming.bytes'][resource_id[resource_id.find('tap'):]] = util_dict[resource_id]                                                                                                                  ['network.incoming.bytes']
                       statistics_dict[key].update(networking_dict)
                   if 'network.outgoing.bytes' in util_dict[resource_id]:
                       networking_dict['network.outgoing.bytes'][resource_id[resource_id.find('tap'):]] = util_dict[resource_id]                                                                                                                  ['network.outgoing.bytes']
                       statistics_dict[key].update(networking_dict)
           statistics_dict[key]['cpu_util'] = util_dict[key]['cpu_util']
      
        self.rpc_server.monitoring(context.get_admin_context(), statistics_dict)

    def stop(self):
        super(UtilizationMonitorService, self).stop()


class VNFMonitorRpcApi(v_rpc.RpcProxy):
    """Plugin side of plugin to manager RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, host):
        super(VNFMonitorRpcApi, self).__init__(topic, self.API_VERSION)
        self.host = host
    
    def monitoring(self, context, stats_dict):
        return self.cast(
            context,
            self.make_msg('monitoring', statistics=stats_dict)
        )


def main(monitor='vnfsvc.vnfmonitor.service.UtilizationMonitorService'):

    config.register_root_helper(cfg.CONF)
    common_config.init(sys.argv[1:])

    vnfsvc_service.prepare_service()
    launcher = os_service.ProcessLauncher()
    launcher.launch_service(
        UtilizationMonitorService())
    launcher.wait()

