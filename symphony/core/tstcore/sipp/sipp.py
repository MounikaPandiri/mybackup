import sys,os

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-3):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
import time
from ftplib import FTP
from common import utils
from core.tstcore.sipp import utils as sipputils
from core import executionCore
from core.tstcore.testcore import TestCore
import logging.config
import errno
import csv
import requests
import random
import ast
import logWriter as logwriter
class sipp(TestCore):

    def __init__(self, exeCore):
        """onboard the test framework"""
        import pdb;pdb.set_trace()
        sipp_config = {}
        self.execore = exeCore
        '''self.sipp_cfg = sipputils._get_sipp_config()
        self._base = self.sipp_cfg['base_number']

        args = {'network': 'sip-network', 'subnet_name': 'sip_subnet', 'cidr': self.sipp_cfg['sipp_network']}
        sip_nw_id = self.execore.createNetwork(**args)
        args = {'network': 'sip-mgmt', 'subnet_name': 'sip_mgmt_subnet', 'cidr': self.sipp_cfg['mgmt_network']}
        mgmt_nw_id = self.execore.createNetwork(**args)
        #TODO: Router ID should be from config file instead of hardcoding
        args = {'router_name': self.sipp_cfg['sipp_router'], 'external_network_name': 'public'}
        router_id = self.execore.createRouter(**args)

        self.NSD = os.path.join(self.execore.productDir,'core/tstcore/sipp/descriptor','sippApi.zip')
        self.templateID = self.execore.onBoard('sipp', self.NSD)

        csObj = self.execore.createServiceRequestObject(router=self.sipp_cfg['sipp_router'], networks= {'sip-network': sip_nw_id, 'mgmt-if': mgmt_nw_id})
        csObj['name'] = 'Sipp'
        csObj['qos'] = 'Voip'
        sipp_svc = self.execore.createService(self.templateID, **csObj)
	print sipp_svc
        import pdb;pdb.set_trace()
        #Need to obtain below configuration from service object
	self.local_path = self.execore.sessionDir
        self.sip1_ip = utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][0], 'mgmt-ip')
        self.sip1_username = utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][0], 'username')
        self.sip1_password = utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][0], 'password')
        self.sip2_ip = utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][1], 'mgmt-ip')
        self.sip2_username = utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][1], 'username')
        self.sip2_password= utils.getVduParameter(sipp_svc['vdus']['Sipp']['vSipp'][1], 'password')
        self._udp_ports = []
        for i in range(16376, 32767):
            self._udp_ports.append(i)
        import pdb;pdb.set_trace()
        self.sip1_client = utils.get_ssh_conn(self.sip1_ip, self.sip1_username, self.sip1_password) 
        self.sip2_client = utils.get_ssh_conn(self.sip2_ip, self.sip2_username, self.sip2_password)
        #self.report = sipputils._init_report()'''
        self.testCaseMap = { 'TEST_SIP_WITH_RTP' : '__exec_sip_rtp__', 
                             'TEST_SIP_WITHOUT_RTP' : '__exec_sip_no_rtp__'}
        super(sipp, self).__init__()


    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
#_______________________________________________________________________________
    def __exec_sip_rtp__(self, **kwargs):
        import pdb;pdb.set_trace()
        sip_port = random.choice(self._udp_ports)
        self._init_args(**kwargs)
	reg1Result_list=list()
	reg2Result_list=list()
	inviteResult_list=list()
	errorStmnt="The server encountered an internal error and was unable to complete your request"
	connectionErrorStmnt="ERR_CONNECT_FAIL"
	for i in range(0,self.test_runs):
		import pdb
		pdb.set_trace()
	        regResult = self._register_users(self.sip1_ip,sip_port,rtp=True, caller=True)
		if errorStmnt in regResult.text:
			print 'error occoured during registration..\n Exiting'
			time.sleep(5)
			sys.exit()
		if connectionErrorStmnt in regResult.text:
	                print 'Could not connect to sipp VM\n Check proxy connections ..\n Exiting'
			time.sleep(5)
	                sys.exit()
		csvFileName=logwriter.csvWrite('registration',regResult.text,self.local_path)
	        outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		#result=self._reportAnalyse(outputDict,'With RTP')
		#reg1Result_list.append(result)
		#_____________________________________________________________
	        sip2_registration_file = self._register_users(self.sip2_ip,sip_port, rtp=True, caller=False)
	        if errorStmnt in sip2_registration_file.text:
	                print 'error occoured during registration..\n Exiting'
	                time.sleep(5)
	                sys.exit()
	        if connectionErrorStmnt in sip2_registration_file.text:
	                print 'Could not connect to sipp VM\n Check proxy connections ..\n Exiting'
	                time.sleep(5)
	                sys.exit()
	
		csvFileName=logwriter.csvWrite('registration',sip2_registration_file.text,self.local_path)
	        outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		#result=self._reportAnalyse(outputDict,'With RTP')
		#reg2Result_list.append(result)
		#_____________________________________________________________
	        import pdb;pdb.set_trace()
	        send_result =self._send(self.sip2_ip,str(sip_port),rtp=True)
	        time.sleep(5)
		invite_result =self._invite(self.sip1_ip,str(sip_port),rtp=True)
		if errorStmnt in invite_result:
	                print 'error occoured during registration..\n Exiting'
	                time.sleep(5)
	                sys.exit()
        	csvFileName=logwriter.csvWrite('invite',invite_result,self.local_path)
        	outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		inviteResult_list.append(outputDict)
		#_____________________________________________________________
		self.users=int(self.users)*2
		self.load=int(self.load)*2
	result=self._reportAnalyse(inviteResult_list,'With RTP')
       	return result
#_______________________________________________________________________________
    def __exec_sip_no_rtp__(self, **kwargs):
        import pdb;pdb.set_trace()
        sip_port = random.choice(self._udp_ports)
        self._init_args(**kwargs)
	reg1Result_list=list()
	reg2Result_list=list()
	inviteResult_list=list()
	errorStmnt="The server encountered an internal error and was unable to complete your request"
	connectionErrorStmnt="ERR_CONNECT_FAIL"
	for i in range(0,self.test_runs):
		import pdb
		pdb.set_trace()
	        regResult = self._register_users(self.sip1_ip,sip_port,rtp=False, caller=True)
		if errorStmnt in regResult.text:
			print 'error occoured during registration..\n Exiting'
			time.sleep(5)
			sys.exit()
		if connectionErrorStmnt in regResult.text:
	                print 'Could not connect to sipp VM\n Check proxy connections ..\n Exiting'
			time.sleep(5)
	                sys.exit()
		csvFileName=logwriter.csvWrite('registration',regResult.text,self.local_path)
	        outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		#result=self._reportAnalyse(outputDict,'Without RTP')
		#reg1Result_list.append(result)
		#_____________________________________________________________
	        sip2_registration_file = self._register_users(self.sip2_ip,sip_port, rtp=False, caller=False)
	        if errorStmnt in sip2_registration_file.text:
	                print 'error occoured during registration..\n Exiting'
	                time.sleep(5)
	                sys.exit()
	        if connectionErrorStmnt in sip2_registration_file.text:
	                print 'Could not connect to sipp VM\n Check proxy connections ..\n Exiting'
	                time.sleep(5)
	                sys.exit()
	
		csvFileName=logwriter.csvWrite('registration',sip2_registration_file.text,self.local_path)
	        outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		#result=self._reportAnalyse(outputDict,'Without RTP')
		#reg2Result_list.append(result)
		#_____________________________________________________________
	        import pdb;pdb.set_trace()
	        send_result =self._send(self.sip2_ip,str(sip_port),rtp=False)
		time.sleep(5)
	        invite_result =self._invite(self.sip1_ip,str(sip_port),rtp=False)
		if errorStmnt in invite_result:
	                print 'error occoured during registration..\n Exiting'
	                time.sleep(5)
	                sys.exit()
	        csvFileName=logwriter.csvWrite('invite',invite_result,self.local_path)
	        outputDict=logwriter.csvAnalyzer(self.load,csvFileName)
		inviteResult_list.append(outputDict)
		#_____________________________________________________________
		self.users=int(self.users)*2
		self.load=int(self.load)*2
		#_____________________________________________________________
        result=self._reportAnalyse(inviteResult_list,'Without RTP')
       	return result
#_______________________________________________________________________________
    def _register_users(self, sip_ip,sip_port,rtp, caller):
       import pdb
       pdb.set_trace()
       #if caller==False:
       #     self._base = int(self._base) + int(self.users)
       cmd='http://'+sip_ip+':9878/register_user/'+str(rtp)+'/'+str(caller)+'/'+str(sip_ip)+'/'+str(self.users)+'/'+str(self._base)+'/'+str(self.bono)+'/'+str(sip_port)+'/'+str(self.load)+'/'+str(self.concurrency)+'/'+str(self.time)+'/'+str(self.ellis)
       self._base = int(self._base) + int(self.users)
       result=requests.get(cmd)
       #outPut=result.text
       return result
#______________________________________________________________________________________
    def _invite(self,sipIp,sipPort,rtp):
	if rtp==True:
		csv='invite_rtp_'+str(self.users)+'.csv'
	else:
		csv='invite_no_rtp_'+str(self.users)+'.csv'
	cmd='http://'+sipIp+':9878/invite/'+str(rtp)+'/'+sipIp+'/'+str(sipPort)+'/'+str(self.load)+'/'+str(self.concurrency)+'/'+str(self.call_count)+'/'+csv+'/'+str(self.bono)+'/'+str(self.time)+'/'+str(self.users)+'/'+str(self.test_type)
	result=requests.get(cmd)
	outPut=result.text
	return outPut
#______________________________________________________________________________________
    def _send(self,sipIp,sipPort,rtp):
	cmd='http://'+sipIp+':9878/generate_send_command/'+str(rtp)+'/'+sipIp+'/'+sipPort+'/'+str(self.load)+'/'+str(self.concurrency)+'/'+str(self.call_count)+'/'+str(self.bono)+'/'+str(self.time)
	result=requests.get(cmd)
	outPut=result.text
	return outPut
#______________________________________________________________________________________
    def _reportAnalyse(self,returnDict,rtpStatus):
	import pdb
	pdb.set_trace()
	#res_dict ={'load':list(),'CSR':list()}	
	tmp_load = list()
	tmp_csr = list()
	lastLoad= int(self.load)/float(2)
	result_dict={}
	test_status=''
	csr=0
	if len(returnDict)>1:
		for result in returnDict:
			tmp_load.append(str(result['load']))
			tmp_csr.append(result['CSR'])
		result_dict = {'report': {'graph': {}}}
		print_string = str(lastLoad)+" SIP Calls Execution "+rtpStatus
		result_dict['report']['graph'] = {"graph_data" : {}}
		result_dict['report']['graph']['graph_data']['label'] = [tuple(tmp_load)]
		result_dict['report']['graph']['graph_data']['data'] = [tuple(tmp_csr)]
		result_dict['report']['graph']['graph_data']['legend'] = [tuple(["Call Success Rate"])]
		result_dict['report']['ptext'] = {'ptext_data': print_string}
	else:
		for result in returnDict:
			csr=result['CSR']
			if csr == 1.0:
				test_status = 'PASS'
			else:
				test_status = 'COMPLETE'
			break
		result_dict = {'report': {'table_append': {}}}
		result_dict['report']['table_append'] = {'table_data': {}}
		result_dict['report']['table_append']['table_data']['header'] = ["Test Scenario", "Test Status", "Call Sucess Rate", "Load"]
		result_dict['report']['table_append']['table_data']['data'] = [["Sipp "+rtpStatus,test_status ,str(csr),str(lastLoad)]]
	return result_dict
