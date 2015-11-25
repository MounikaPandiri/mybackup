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
        self.port = 830
        super(GenericDriver, self).__init__()
     
    def push_configuration(self, instance, mgmt_ip, configuration_event):
        try:
            LOG.debug(_("***** CONFIGURATION EVENT *****:%s"),configuration_event)
            LOG.debug(_("***** LIFECYCLE EVENTS *****:%s"),self.lifecycle_events)
            config_xml = '<config>'+self.lifecycle_events[configuration_event]+'</config>'
            LOG.debug(_("DRIVER CODE RECEIVED IP**:%s"),mgmt_ip)
            self._check_connection(mgmt_ip)
            import pdb;pdb.set_trace()
            time.sleep(5) 
            mgr = manager.connect(host=mgmt_ip, port=self.port, username=self.username, password=self.password, hostkey_verify=False)
            LOG.debug(_("Driver nc client manager instantiated: %s"), mgr)
            mgr.lock()
            LOG.debug(_("Configuration XML is: %s"), config_xml)
            mgr.edit_config(target='candidate', config=config_xml)
            mgr.commit()
            mgr.unlock()
            mgr.close_session()
            status = "COMPLETE"
        except KeyError:
            LOG.debug(_("Configuration Event not in Lifecycle Events"))
            status = "ERROR"
        except Exception:
            status = "ERROR"
        finally:
            return status

    def _check_connection(self, mgmt_ip):
        ssh_connected = False
        # keep connecting till ssh is success
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while not ssh_connected:
            try:
                ssh.connect(mgmt_ip, username = self.username, password = self.password, allow_agent=False, timeout=10)
                ssh_connected = True
            except Exception:
                time.sleep(5)
                pass
