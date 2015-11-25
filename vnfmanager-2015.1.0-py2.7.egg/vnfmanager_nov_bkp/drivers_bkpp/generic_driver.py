# Copyright 2015 Tata Consultancy Services Limited(TCSL)
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

import time
import paramiko

from ncclient import manager
from vnfmanager.openstack.common import log as logging
from vnfmanager.openstack.common.gettextutils import _

LOG = logging.getLogger(__name__)

class GenericDriver(object):
    def __init__(self, *args, **kwargs):
        conf = args[0]
        self.username = kwargs['username'] 
        self.password = kwargs['password']
        self.lifecycle_events = kwargs['lifecycle_events']
        self.config_xml = '<config>'+self.lifecycle_events['init']+'</config>'
        self.port = 830
        super(GenericDriver, self).__init__()
     
    def push_configuration(self, instance, mgmt_ip):
        netconf_enable = False
        LOG.debug(_("DRIVER CODE RECEIVED IP**:%s"),mgmt_ip)
        
        while not netconf_enable:
            try:
                mgr = manager.connect(host=mgmt_ip, port=self.port, username=self.username, password=self.password, timeout=70, hostkey_verify=False)
                LOG.debug(_("Device Connected!!Configuration to remote device instantiated: %s"), mgr)
                mgr.lock()
                netconf_enable = True
                LOG.debug(_("Configuration XML is: %s"), self.config_xml)
                mgr.edit_config(target='candidate', config=self.config_xml)
                mgr.commit()
                mgr.unlock()
                mgr.close_session()
                status = "COMPLETE"
            except Exception:
                if not netconf_enable:
                    LOG.debug(_("VNF is DOWN"))
                    time.sleep(5)
                else:
                    status = "ERROR"
        return status
