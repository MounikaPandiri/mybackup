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

#from vnfmanager.commom import exceptions
import yaml
import time
import paramiko

from vnfmanager.drivers.templates_haproxy import haproxy_templates as templates
from ncclient import manager
from vnfmanager.drivers import abstract_driver as abs_driver

class LoadBalancerDriver(abs_driver.AbstractDriver):
    def __init__(self, *args, **kwargs):
        self.username = kwargs['username']
        self.password = kwargs['password']

    def pre_configure(self):
        pass

    def configure(self, **kwargs):
        import pdb;pdb.set_trace()
        netconf_enabled = False
        """configure the service """
        self.mgmt_ip = kwargs['mgmt-ip']
        self.args_dict = kwargs['conf']
        ipaddresses = self.args_dict['config']['ips']
        port = self.args_dict['config']['port']
        #self._check_connection()
        time.sleep(5)
        while not netconf_enabled:
            try:
                m = manager.connect(host=self.mgmt_ip, username=self.username, password=self.password, port=830, hostkey_verify=False)
                netconf_enabled = True
                confstr = templates.action.format(**{'action':'change'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.frontend_name.format(**{'name':'input'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.frontend_name.format(**{'name':'input'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.bind.format(**{'ip_port':'*:'+port})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.default_backend.format(**{'backend_name':'output'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.backend_name.format(**{'backend_name':'output'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.balance.format(**{'balance_algorithm':'roundrobin'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                confstr = templates.mode.format(**{'mode':'http'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                for ipaddress in ipaddresses:
                    confstr = templates.IPAddress.format(**{'IPAddress':ipaddress+':'+port})
                    m.edit_config(target='candidate', config=confstr)
                    m.commit()
                confstr = templates.action.format(**{'action':'restart'})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
            except Exception:
                print "VM IS DOWN"
    
    def _check_connection(self):
        ssh_connected = False
        # keep connecting till ssh is success
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while not ssh_connected:
            try:
                ssh.connect(self.mgmt_ip, username = self.username, password = self.password, allow_agent=False)
                ssh_connected = True
            except Exception:
                time.sleep(5)
                pass

    def update(self, **kwargs):
        """
        Description   : Accepts config file updates.
        Input         : In the form of dictionary of dictionaries
        Params        :
           Type       : config(This should be specified as key)
           ips        : IP Addresses to be updated in the form of a list
           port       : port number in string format
           example    : {'config': {'ips': ['{webserver-vAS#pkt-in}'], 'port': '8080'}}
        """
        mgmt_ip = kwargs['mgmt-ip']
        for key in kwargs['conf']:
            if key == 'config':
               self._update_config(mgmt_ip, kwargs['conf'][key])

    def _update_config(self, mgmt_ip, args_dict):
        """updates the config file"""
        status = 'FAILED'
        ips = args_dict['ips']
        port_num = args_dict['port']
        with manager.connect(host=mgmt_ip, username=self.username, password=self.password, port=830, hostkey_verify=False) as m:
            for ipaddress in ips:
                confstr = templates.IPAddress.format(**{'IPAddress':ipaddress+':'+port_num})
                m.edit_config(target='candidate', config=confstr)
                m.commit()
                status = 'COMPLETE'
        return status

    def delete_service(self):
        """delete the service """
        pass

    def upgrade(self, **kwargs):
        import pdb;pdb.set_trace()
        mgmt_ip = kwargs['mgmt-ip']
        with manager.connect(host=mgmt_ip, username=self.username, password=self.password, port=830, hostkey_verify=False, timeout=1200) as m:
            if 'puppet' in m.get_config("running").data_xml:
                m.edit_config(target="candidate", config='<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"><puppet xmlns="http://netconfcentral.org/ns/puppet" xc:operation="delete"></puppet></config>')
                m.commit()
            confstr = '<config>'+kwargs['conf']+'</config>' 
            m.lock()
            m.edit_config(target='candidate', config=confstr)
            m.commit()
            m.unlock()
            m.close_session()
            status = 'COMPLETE'
        return status
