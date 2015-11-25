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
# @author: anirudh vedantam, anirudh.vedantam@tcs.com, Tata Consultancy Services Limited

import eventlet
import netaddr
from oslo.config import cfg

from neutron.agent.common import config
from neutron.agent.linux import external_process
from neutron.agent.linux import interface
from neutron.agent.linux import ip_lib
from neutron.common import constants as l3_constants
#from neutron.common import legacy
from neutron.common import topics
from neutron.openstack.common import log as logging
from neutron.openstack.common import service
from neutron import service as neutron_service
from neutron.services.firewall.agents.fw_netconf import firewall_netconf_agent

from neutron import manager
from neutron import context
from neutron.openstack.common import importutils
from neutron.openstack.common import loopingcall
from neutron.openstack.common import periodic_task
from neutron.agent import rpc as agent_rpc

LOG = logging.getLogger(__name__)

class NetconfFirewallAgent(firewall_netconf_agent.FWaaSNetconfAgentRpcCallback, manager.Manager):
    def __init__(self, host, conf=None):
        LOG.debug(_('NETCONF L3NATAgent: __init__'))
        if conf:
            self.conf = conf
        else:
            self.conf = cfg.CONF
        self.root_helper = config.get_root_helper(self.conf)

        self._check_config_params()

        try:
            self.driver = importutils.import_object(
                self.conf.interface_driver,
                self.conf
            )
        except Exception:
            msg = _("Error importing interface driver "
                    "'%s'") % self.conf.interface_driver
            LOG.error(msg)
            raise SystemExit(msg)

        self.context = context.get_admin_context_without_session()
        super(NetconfFirewallAgent, self).__init__(conf=self.conf)
 
    def _check_config_params(self):
        """Check items in configuration files.

        Check for required and invalid configuration items.
        The actual values are not verified for correctness.
        """
        if not self.conf.interface_driver:
            msg = _('An interface driver must be specified')
            LOG.error(msg)
            raise SystemExit(msg)

        if not self.conf.use_namespaces and not self.conf.router_id:
            msg = _('Router id is required if not using namespaces.')
            LOG.error(msg)
            raise SystemExit(msg)


class NetconfFirewallAgentWithStateReport(NetconfFirewallAgent):
     
     # TODO(anirudh): To check whether agent scheduler would be necessary for
     #                one firewall to one driver/agent.
     def __init__(self, host, conf=None):
        super(NetconfFirewallAgentWithStateReport, self).__init__(host=host, conf=conf)
        self.conf = cfg.CONF
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.PLUGIN)
        self.agent_state = {
            'binary': 'neutron-FW-appliance-aS',
            'host': host,
            'topic': topics.L3_AGENT,
            'configurations': {
                'use_namespaces': self.conf.use_namespaces,
                'interface_driver': self.conf.interface_driver},
            'start_flag': True,
            'agent_type': l3_constants.AGENT_TYPE_L3}
        report_interval = cfg.CONF.AGENT.report_interval
        self.use_call = True
        if report_interval:
            self.heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            self.heartbeat.start(interval=report_interval)

     def _report_state(self):
        try:
            self.state_rpc.report_state(self.context,
                                        self.agent_state,
                                        self.use_call)
            self.agent_state.pop('start_flag', None)
            self.use_call = False
            LOG.debug(_("Report state task successfully completed"))
        except Exception:
            LOG.exception("Failed reporting state!")


def main():
    eventlet.monkey_patch()
    conf = cfg.CONF
    conf.register_opts(firewall_netconf_agent.OPTS)
    config.register_interface_driver_opts_helper(conf)
    config.register_use_namespaces_opts_helper(conf)
    config.register_agent_state_opts_helper(conf)
    config.register_root_helper(conf)
    conf.register_opts(interface.OPTS)
    conf.register_opts(external_process.OPTS)
    conf(project='neutron')
    config.setup_logging(conf)
    #legacy.modernize_quantum_config(conf)
    server = neutron_service.Service.create(
        binary='neutron-FW-appliance-aS',
        topic=topics.L3_AGENT,
        report_interval=cfg.CONF.AGENT.report_interval,
        manager='neutron.services.firewall.agents.fw_netconf.netconf_fw_agent.'
                'NetconfFirewallAgentWithStateReport')
    service.launch(server).wait()
