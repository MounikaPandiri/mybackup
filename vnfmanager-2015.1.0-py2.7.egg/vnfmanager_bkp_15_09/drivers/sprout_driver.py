import yaml
import time
from vnfmanager.agent.linux import utils
import paramiko
from vnfmanager.drivers import templates
from ncclient import manager

from vnfmanager.openstack.common import log as logging
from vnfmanager.openstack.common.gettextutils import _
LOG = logging.getLogger(__name__)

class sprout:

    def __init__(self, conf):
        LOG.debug(_(conf))
        self.__ncport = "830"
        self.retries = 10
        self.hsip = "0.0.0.0"
        self.homerip = "0.0.0.0"

        self.parse(conf)
        try:
            self.__uname = "user="+self.username
            self.__pswd = "password="+self.password
        except KeyError:
            raise

    def parse(self,cfg):
        for i in range(0,len(cfg['Ims'])):
            if(cfg['Ims'][i]['name']=="vSprout"):
                self.username=cfg['Ims'][i]['vm_details']['image_details']['username']
                self.password=cfg['Ims'][i]['vm_details']['image_details']['password']
                self.localip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips']['ims-vsprout']
                self.mgmtip=cfg['Ims'][i]['vm_details']['network_interfaces']['management-interface']['ips']['ims-vsprout']
         
                     
            if(cfg['Ims'][i]['name']=="vHS"):
                self.hsip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips']['ims-vhs']

            if(cfg['Ims'][i]['name']=="vHomer"):
                self.homerip=cfg['Ims'][i]['vm_details']['network_interfaces']['pkt-in']['ips']['ims-vhomer']

    def configure_service(self, *args, **kwargs):
         """configure the service """
         #self._check_connection()

         LOG.debug(_("Sprout .. In Configure service"))
         LOG.debug(_(self.hsip))
         LOG.debug(_(self.homerip))
         LOG.debug(_(self))

         conf_dict = {"private_ip": self.localip , "public_ip": self.localip , "chronos_ip": self.localip,"homer_ip": self.homerip, "homestead_ip": self.hsip,"cluster_ip": "127.0.0.1","service_name": "sprout"}
         confstr = templates.sprout_settings.format(**conf_dict)

         configuration_done = False
         while not configuration_done:
             try:
                 with manager.connect(host=self.mgmtip, username=self.username, password=self.password, port=830, hostkey_verify=False) as m:
                     print "VM is UP"
                     LOG.debug(_("VM is UP"))
                     configuration_done = True
                     c = m.get_config(source='running').data_xml
                     #c1 = m.edit_config(target='candidate', config=confstr1)
                     #m.commit()
                     LOG.debug(_("configuration %s"), e)
                     c1 = m.edit_config(target='candidate', config=confstr)
                     m.commit(confirmed=False, timeout=300)
                     configuration_done = True
             except Exception as e:
                 print e
                 print "VM is down"
                 LOG.debug(_("VM is down"))
                 time.sleep(5)

         """
         with manager.connect(host=self.mgmtip, username=self.username, password=self.password, port=830, hostkey_verify=False) as m:
             c = m.get_config(source='running').data_xml
             c1 = m.edit_config(target='candidate', config=confstr)
             m.commit()
         """

         """
         command_list = []
         command_list.append("replace /ims/resolvedns/Ipaddress --value=%s" % self.Dnslocalip)
         command_list.append("replace /ims/privateip/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/publicip/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/chronos/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/ClusterSettings/Ipaddress --value=%s"% self.localip)
         command_list.append("replace /ims/Service/name --value=sprout")
         print(command_list)
         for command in command_list:
             self.executeCommands(command)
         """

    def executeCommands(self, command):
        executionList = ['yangcli']
        self.__ip = "server="+self.mgmtip
        executionList.extend([self.__ip, self.__uname, self.__pswd, self.__ncport])
        executionList.append(command)
        addl_env = {}
        print(executionList)
        for i in xrange(0,self.retries):
            retVal = utils.execute(executionList)
            if  retVal.find("The replace command is not allowed in this mode") == -1:
                break
            elif i == self.retries-1:
                #raise exceptions.DriverException("Unable to connect to server")
                pass

        return retVal

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
#    sprout(x)

#if __name__ == "__main__":
#    main()
