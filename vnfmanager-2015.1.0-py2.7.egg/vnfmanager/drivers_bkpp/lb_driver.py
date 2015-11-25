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
from vnfmanager.agent.linux import utils


class LoadBalancerDriver(object):
    def __init__(self , conf):
        import pdb;pdb.set_trace()
        self.conf = conf
        self.__ncport = "ncport=830"
        self.retries = 10
        self.webserver = self.conf['webserver']
        self.loadbalancer = self.conf['loadbalancer']
        try:
            for vdu in self.loadbalancer:
                if vdu['name'] == 'vLB':
                    self.lb_vdu = vdu
                    self.uname = vdu['vm_details']['image_details']['username']
                    self.password = vdu['vm_details']['image_details']['password']
                    self.__uname = "user="+vdu['vm_details']['image_details']['username']
                    self.__password = "password="+vdu['vm_details']['image_details']['password']
                    break
            #self.configure_service()
        except KeyError:
            raise
    
    def get_type(self):
        """Return one of predefined type of the hosting device drivers."""
        pass

    def get_name(self):
        """Return a symbolic name for the service VM plugin."""
        pass

    def get_description(self):
        """Returns the description of driver"""
        pass
    
    def configure_service(self, dev):
        """configure the service """
        self.__ip = "server="+self.lb_vdu['mgmt-ip'][0]
        self.mgmt_ip = self.lb_vdu['mgmt-ip'][0]
        self._check_connection()
        ipaddresses = []
        for vdu in self.webserver:
            if vdu['name'] == 'vAS':
                ips = vdu['vm_details']['network_interfaces']['pkt-in']['ips']
                for instance_name, ip in ips.iteritems():
                    ipaddresses.append(ip)
                    self.dev_name = instance_name
                break

        #for devname, ip in self.conf['webserver']['_mgmt_ips'].iteritems():
        #    ipaddresses.append(ip)
        command_list = []
        #command_list.append("replace /haproxy/backend/action --value=change")
        #command_list.append("replace /haproxy/frontend/name --value=input")
        #command_list.append("replace /haproxy/frontend/bind --value=*:8000")
        #command_list.append("replace /haproxy/frontend/default_backend --value=output")
        #command_list.append("replace /haproxy/backend/name --value=output")
        #command_list.append("replace /haproxy/backend/balance --value=roundrobin")
        #command_list.append("replace /haproxy/backend/mode --value=http")
        for ipaddress in ipaddresses:
            command_list.append("replace /haproxy/backend/IPAddress --value=%s:80" % ipaddress)
        command_list.append("replace /haproxy/backend/action --value=restart")
        for command in command_list:
            self.executeCommands(command)
        return self.dev_name, 'ACTIVE'

    def _check_connection(self):
        ssh_connected = False
        # keep connecting till ssh is success
        executionList =[]
        executionList.extend(['sshpass','-p'+self.password,'ssh', '-T', self.uname+'@'+self.mgmt_ip])
        while not ssh_connected:
            try:
                retVal = utils.execute(executionList)
                ssh_connected = True
            except Exception:
                pass


    def delete_service(self):
        """delete the service """
        pass

    def update_service(self):
        """update the service """
        pass

    def executeCommands(self, command):
        executionList = ['yangcli']
        executionList.extend([self.__ip, self.__uname, self.__password, self.__ncport])
        executionList.append(command)
        for i in xrange(0,self.retries):
            retVal = utils.execute(executionList)
            if  retVal.find("The replace command is not allowed in this mode") == -1:
                break
            elif i == self.retries-1:
                #raise exceptions.DriverException("Unable to connect to server")
                pass
            
        return retVal

"""if __name__ == '__main__':
    lb = LoadBalancerDriver('sudo /usr/local/bin/neutron-rootwrap /etc/neutron/rootwrap.conf', '10.0.0.6','9cd6977f-a92a-4ba2-87d7-f47115fbf754', 'tcs','tcs123', '830')
    lb.configure_service(['10.0.0.4:80','10.0.0.5:80'])"""
