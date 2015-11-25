import yaml
import time
from vnfmanager.agent.linux import utils
import paramiko
from ncclient import manager
from vnfmanager.drivers import templates
import re

from vnfmanager.openstack.common import log as logging
from vnfmanager.openstack.common.gettextutils import _
LOG = logging.getLogger(__name__)

class bono:

    def __init__(self, conf):
        LOG.debug(_("Bono __init__"))
        LOG.debug(_(conf))
        self.__ncport = "830"
        self.retries = 10
        self.homerip = "0.0.0.0"
        self.hsip = "0.0.0.0"
        self.sproutip = "0.0.0.0"

        self.parse(conf)
        try:
            self.__uname = "user="+self.username
            self.__pswd = "password="+self.password
        except KeyError:
            raise

    def parse(self,cfg):
        for i in range(0, len(cfg['Ims'])):
            regex = re.compile('^(vBono)\_\d*$')
            #if(cfg['Ims'][i]['name']=="vBono"):
            if re.search(regex, cfg['Ims'][i]['name']):
                LOG.debug(_("CONDITION*********************************SATISFIED"))
                self.username=cfg['Ims'][i]['vm_details']['image_details']['username']
                self.password=cfg['Ims'][i]['vm_details']['image_details']['password']
                #self.pkt_in_ips_key = cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'].keys()[0]
                self.localip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips']['ims-'+cfg['Ims'][i]['name']]
                self.publicip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips']['ims-'+cfg['Ims'][i]['name']]
                self.mgmtip=cfg['Ims'][i]['vm_details']['network_interfaces']['management-interface']['ips']['ims-'+cfg['Ims'][i]['name']]
         
                     
            if(cfg['Ims'][i]['name']=="vSprout"):
                self.pkt_in_ips_key = cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'].keys()[0]
                self.sproutip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'][self.pkt_in_ips_key]

            if(cfg['Ims'][i]['name']=="vHomer"):
                self.pkt_in_ips_key = cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'].keys()[0]
                self.homerip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'][self.pkt_in_ips_key]

            if(cfg['Ims'][i]['name']=="vHS"):
                self.pkt_in_ips_key = cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'].keys()[0]
                self.hsip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips'][self.pkt_in_ips_key]


    def configure_service(self, *args, **kwargs):
         LOG.debug(_("Bono configure service"))
         """configure the service """
         #self._check_connection()
         conf_dict = {"private_ip": self.localip , "public_ip": self.publicip , "chronos_ip": self.localip,"homer_ip": self.homerip, "homestead_ip": self.hsip , "sprout_ip": self.sproutip,"service_name": "bono"}
         confstr = templates.bono_settings.format(**conf_dict)
         conf_dict1 = {"restund_ip": self.localip,"service_name": "restund"}
         confstr1 = templates.restund_service.format(**conf_dict1)


         configuration_done = False
         while not configuration_done:
             try:
                 with manager.connect(host=self.mgmtip, username=self.username, password=self.password, port=830, hostkey_verify=False) as m:
                     print "VM is UP"
                     LOG.debug(_("VM is UP"))
                     configuration_done = True
                     c = m.get_config(source='running').data_xml
                     LOG.debug(_("config %s"), c)
                     #c1 = m.edit_config(target='candidate', config=confstr1)
                     #m.commit()
                     c2 = m.edit_config(target='candidate', config=confstr)
                     m.commit(confirmed=False, timeout=300)
                     c3 = m.edit_config(target='candidate', config=confstr1)
                     m.commit(confirmed=False, timeout=300)
             except Exception as e:
                 LOG.debug(_("VM is DOWN %s"), e)
                 LOG.debug(_("VM is DOWN"))
                 print e
                 print "VM is down"
                 time.sleep(5)

         """
         with manager.connect(host=self.mgmtip, username=self.username, password=self.password, port=830, hostkey_verify=False) as m:
             c = m.get_config(source='running').data_xml
             c1 = m.edit_config(target='candidate', config=confstr)
             m.commit()

         """

#             c2 = m.edit_config(target='candidate', config=confstr1)
#             m.commit()
         """
         command_list = []
         command_list.append("replace /ims/resolvedns/Ipaddress --value=%s" % self.Dnslocalip)
         command_list.append("replace /ims/privateip/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/publicip/Ipaddress --value=%s"% self.publicip)
         command_list.append("replace /ims/chronos/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/Service/name --value=bono")
         print(command_list)
         for command in command_list:
             #time.sleep(10)
             self.executeCommands(command)
         """
    
    def executeCommands(self, command):
        m = manager.connect_ssh(self.mgmtip, username=self.username, password=self.password, port=self.__ncport, hostkey_verify=False)
        c = m.get_config(source='running').data_xml
        conf_dict = {"dns_ip":self.Dnslocalip , "private_ip": self.localip , "public_ip": self.publicip, "chronos_ip": self.localip}
        confstr = template.allnode_settings.format(**conf_dict)
        c1 = m.edit_config(target='candidate', config=confstr)
        m.commit()
      
    def _check_connection(self):
        ssh_connected = False
        # keep connecting till ssh is success
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while not ssh_connected:
            try:
                ssh.connect(self.mgmtip, username = self.username, password = self.password, allow_agent=False, timeout=10)
                ssh_connected = True
                print "VM IS UP"
            except Exception:
                print "VM IS DOWN"
                pass

#def main():
#    f=open("xyz.yaml")
#    x=yaml.load(f)
#    bono(x)

#if __name__ == "__main__":
#    main()
