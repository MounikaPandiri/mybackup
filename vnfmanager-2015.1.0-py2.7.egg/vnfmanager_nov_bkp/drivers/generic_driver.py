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

try:
    from ncclient import manager
    from vnfmanager.openstack.common import log as logging
    from vnfmanager.openstack.common.gettextutils import _
    LOG = logging.getLogger(__name__)
except Exception:
    LOG = None
    pass


class GenericDriver(object):
    def __init__(self, *args, **kwargs):
        conf = args[0]
        self.username = kwargs['username'] 
        self.password = kwargs['password']
        self.port = 830
        super(GenericDriver, self).__init__()
     
    def configure(self, **kwargs):
        """
        Description   : Configuration/Updation wrapper that pushes configuration to the device.
        Input         : In the form of xml-string
        Params        : None 

        ** Example    : {'configure': '<ims>
                                          <Homer>
                                              <Ipaddress>{Ims-vHomer-HS#pkt-in}</Ipaddress>
                                          </Homer>
                                          <privateip>
                                              <Ipaddress>{Ims-vBono-Ellis#pkt-in}</Ipaddress>
                                          </privateip>
                                          <publicip>
                                              <Ipaddress>{Ims-vBono-Ellis#pkt-in}</Ipaddress>
                                          </publicip>
                                          <chronos>
                                              <Ipaddress>{Ims-vBono-Ellis#pkt-in}</Ipaddress>
                                          </chronos>
                                          <Homestead>
                                              <Ipaddress>{Ims-vHomer-HS#pkt-in}</Ipaddress>
                                          </Homestead>
                                          <Sprout>
                                              <Ipaddress>{Ims-vSprout#pkt-in}</Ipaddress>
                                          </Sprout>
                                          <restund>
                                              <Ipaddress>{Ims-vBono-Ellis#pkt-in}</Ipaddress>
                                          </restund> 
                                          <Service>
                                              <name>bono</name>
                                          </Service>
                                          <Service>
                                              <name>restund</name>
                                          </Service>
                                       </ims>'   }
        NOTE: The alignment and indentation are only for display, the input can be a continous xml string. 
              ** Also, the xml-string should of the yang model corresponding to the device.
        """  
        try:
            mgmt_ip = kwargs['mgmt-ip']
            netconf_enable = False
            if kwargs['conf'] == '':
               status = "COMPLETE"
               return
            config_xml = '<config>'+kwargs['conf']+'</config>'
            LOG.debug(_("DRIVER CODE RECEIVED IP**:%s"), mgmt_ip)

            while not netconf_enable:
                try:
                    mgr = manager.connect(host=mgmt_ip, port=self.port, username=self.username, password=self.password, hostkey_verify=False, timeout=50)
                    if 'puppet' in mgr.get_config("running").data_xml:
                        mgr.edit_config(target="candidate", config='<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"><puppet xmlns="http://netconfcentral.org/ns/puppet" xc:operation="delete"></puppet></config>')
                        mgr.commit()
                    LOG.debug(_("Driver nc client manager instantiated: %s"), mgr)
                    mgr.lock()
                    LOG.debug(_("Configuration XML is: %s"), config_xml)
                    mgr.edit_config(target='candidate', config=config_xml)
                    mgr.commit()
                    mgr.unlock()
                    mgr.close_session()
                    status = "COMPLETE"
                    netconf_enable = True
                except Exception:
                    if not netconf_enable:
                        LOG.debug(_("VNF is DOWN"))
                        time.sleep(10)
                    else:
                        raise 

        except KeyError:
            LOG.debug(_("Configuration Event not in Lifecycle Events"))
            status = "ERROR"
        except Exception:
            status = "ERROR"
        finally:
            return status

    def upgrade(self, **kwargs):
        self.configure(kwargs)
