import time
from ftplib import FTP
from common import utils
from core.tstcore.sipp import utils as sipputils
from core import executionCore
from core.tstcore.testcore import testCore
import os
import logging.config

logger = logging.getLogger(__name__)


class sipp(testCore):

    def __init__(self, exeCore):
        """onboard the test framework"""
        import pdb;pdb.set_trace()
        sipp_config = {}
        self.execore = exeCore
        self.sipp_cfg = sipputils._get_sipp_config()
        self._base = self.sipp_cfg['base_number']

        args = {'network': 'sip-network', 'subnet_name': 'sip_subnet', 'cidr': self.sipp_cfg['sipp_network']}
        sip_nw_id = self.execore.createNetwork(**args)
        args = {'network': 'sip-mgmt', 'subnet_name': 'sip_mgmt_subnet', 'cidr': self.sipp_cfg['mgmt_network']}
        mgmt_nw_id = self.execore.createNetwork(**args)
        #TODO: Router ID should be from config file instead of hardcoding
        args = {'router_name': self.sipp_cfg['sipp_router'], 'external_network_name': 'public'}
        router_id = self.execore.createRouter(**args)

        self.NSD = os.path.join(self.execore.productDir,'core/tstcore/sipp/descriptor','sipp.zip')
        self.templateID = self.execore.onBoard('teravm', self.NSD)

        csObj = self.execore.createServiceRequestObject(router=self.sipp_cfg['sipp_router'], networks= {'sip-network': sip_nw_id, 'mgmt-if': mgmt_nw_id})
        csObj['name'] = 'Sipp'
        csObj['qos'] = 'Voip'
        sipp_svc = self.execore.createService(self.templateID, **csObj)

        import pdb;pdb.set_trace()
        #Need to obtain below configuration from service object
        self.sip1_ip='192.168.21.3'
        self.sip1_username='tcs'
        self.sip1_password='tyui'
        self.sip2_ip='192.168.21.4'
        self.sip2_username='tcs'
        self.sip2_password='tyui'

        self.sip1_client = utils.get_ssh_conn(self.sip1_ip, self.sip1_username, self.sip1_password) 
        self.sip2_client = utils.get_ssh_conn(self.sip2_ip, self.sip2_username, self.sip2_password)

        self.testCaseMap = { 'TEST_SIP_WITH_RTP' : '__exec_sip_rtp__', 
                             'TEST_SIP_WITHOUT_RTP' : '__exec_sip_no_rtp'}
        super(testCore, self).__init__()


    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __exec_sip_rtp__(self, **kwargs):
        import pdb;pdb.set_trace()
        self._init_args(**kwargs)
        sip1_reg_file = self._register_users(self.sip1_ip, client=self.sip1_client, rtp=True)
        sip2_reg_file, sip2_invite_file = self._register_users(self.sip2_ip, client=self.sip2_client, rtp=True, caller=True)


    def __exec_sip_no_rtp(self, **kwargs):
        self._init_args(**kwargs)


    def _register_users(self, sip_ip, client, rtp=False, caller=False):
        user_file = self._generate_users(client, rtp, caller)
        reg_cmd = self._generate_register_cmd(user_file, sip_ip)
        result, error = utils.exec_command(reg_cmd, client)
        time.sleep(30)
        self._base = self._base + self.call_count


    def _generate_register_cmd(self, csv, ip):
        #need to fix variable ip
        return "/home/tcs/sipp-3.4.1/sipp " + self.ellis + \
               " -sf /home/tcs/scripts/register3_3.xml  -inf " + csv + \
               " -rsa " + self.bono + ":5060 -p " + str(self.sip_port) + " -i " + \
               ip + " -trace_screen -trace_stat -m " + str(self.call_count) + " -l " + \
               str(self.load) + " -r " + str(self.concurrency) + " -rp " + self.time + " -bg"


    def _generate_users(self, client, rtp=False, caller=False):
        import pdb;pdb.set_trace()
        """ Generated SIP users with IMS """
        if rtp:
            file_name = "register_rtp_"+self.call_count
        else:
            file_name = "register_no_rtp_"+self.call_count

        cmd = "python /home/tcs/scripts/EllisClient.py --ellis_ip " + self.ellis + " --call_count " + \
               str(self.call_count) + " --base_number " + str(self._base) + " --file_name " + file_name

        if caller:
             cmd += " --caller"
        try: 
            result, error = utils.exec_command(cmd, client)
        except:
            logger.debug("Unable to generate sip users.")

        #Get remote path from the config file.
        if caller:
            return self.sipp_cfg['remote_files_path']+'/'+file_name+'.csv', self.sipp_cfg['remote_files_path'] + \
                   "/invite_without_rtp_" + str(self._runner) + ".csv"
        else:
            return self.sipp_cfg['remote_files_path']+'/'+file_name+'.csv'
