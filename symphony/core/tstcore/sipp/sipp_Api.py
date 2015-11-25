import time
from ftplib import FTP
from common import utils
from core.tstcore.sipp import utils as sipputils
from core import executionCore
from core.tstcore.testcore import TestCore
import os
import logging.config
import errno
import csv
import requests
import random

class sipp(TestCore):

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
        self.templateID = self.execore.onBoard('sipp', self.NSD)

        csObj = self.execore.createServiceRequestObject(router=self.sipp_cfg['sipp_router'], networks= {'sip-network': sip_nw_id, 'mgmt-if': mgmt_nw_id})
        csObj['name'] = 'Sipp'
        csObj['qos'] = 'Voip'
        sipp_svc = self.execore.createService(self.templateID, **csObj)

        import pdb;pdb.set_trace()
        #Need to obtain below configuration from service object
        self.sip1_ip = utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][0], 'mgmt-if')
        self.sip1_username = utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][0], 'username')
        self.sip1_password = utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][0], 'password')
        self.sip2_ip = utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][1], 'mgmt-if')
        self.sip2_username = utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][1], 'username')
        self.sip2_password= utils.getVduParameter(tvm_srv['vdus']['Sipp']['vSipp'][1], 'password')
        self._udp_ports = []
        for i in range(16376, 32767):
            self._udp_ports.append(i)

        self.sip1_client = utils.get_ssh_conn(self.sip1_ip, self.sip1_username, self.sip1_password) 
        self.sip2_client = utils.get_ssh_conn(self.sip2_ip, self.sip2_username, self.sip2_password)
        self.report = sipputils._init_report()
        self.testCaseMap = { 'TEST_SIP_WITH_RTP' : '__exec_sip_rtp__', 
                             'TEST_SIP_WITHOUT_RTP' : '__exec_sip_no_rtp'}
        super(TestCore, self).__init__()


    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
#_______________________________________________________________________________
    def __exec_sip_rtp__(self, **kwargs):
        import pdb;pdb.set_trace()
        sip_port = random.choice(self._udp_ports)
        self._init_args(**kwargs)
        registration_file,sip1_invite_file = self._register_users(self.sip1_ip, rtp=True, caller=True,sip_port)
        sip2_invite_file = self._register_users(self.sip2_ip, rtp=True, caller=False,sip_port)
        import pdb;pdb.set_trace()
        invite_testscript = self.sipp_cfg['remote_files_path'] + "/invite_final_rtp.xml" 
        send_testscript = self.sipp_cfg['remote_files_path'] + "/send_final_rtp.xml"
        invite_result =self._invite(rtp=True,self.sip1_ip,sipPort,sip1_invite_file)
	send_result =self._send(rtp=True,self.sip2_ip,sipPort)
        return sipputils._report(invite_result, self.report)
#_______________________________________________________________________________
    def __exec_sip_no_rtp(self, **requests.post("http://httpbin.org/post")kwargs):
        self._init_args(**kwargs)
#_______________________________________________________________________________
    def _register_users(self, sip_ip, rtp=False, caller=False,sip_port):
       cmd='http://'+sip_ip+':9879/register_user/'+rtp+'/'+caller+'/'+str(sip_ip)+'/'+str(self.users)+'/'+str(self._base)+'/'+str(self.bono)+'/'+str(sip_port)+'/'+str(self.load)+'/'+str(self.concurrency)+'/'+str(self.time)+'/'+str(self.ellis))
       result=requests.get(cmd)
       outPut=result.text
#______________________________________________________________________________________
    def _invite(self,rtp,sipIp,sipPort,csv):
	cmd='http://'+sipIp+':9879/invite/'+rtp+'/'+sipIp+'/'+str(sipPort)+'/'str(self.load)+'/'+str(self.concurrency)+'/'+str(self.call_count)+'/"'+csv+'"/'+str(self.bono)+'/'+str(self.time)+'/'+str(self.users)+'/'str(self.test_type'
	result=requests.get(cmd)
	outPut=result.text
#______________________________________________________________________________________
   def _send(self,rtp,sipIp,sipPort):
	cmd='http://'+sipIp+':9879/generate_send_command/'+rtp+'/'+sipIp+'/'+sipPort+'/'+str(self.load)+'/'+str(self.concurrency)+'/'+str(self.call_count)+'/'+str(self.bono)+'/'+str(self.time)'
	result=requests.get(cmd)
	outPut=result.text
