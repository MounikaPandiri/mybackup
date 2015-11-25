import time
import zipfile
import csv

from report import report
from ftplib import FTP
from core.tstcore.testcore import TestCore
from common import utils
from core.tstcore.tvm import utils as tvmutils
from core import executionCore
import os

class tvm(TestCore):

    def __init__(self, exeCore):
        """onboard the test framework"""
        self.execore = exeCore
        import pdb;pdb.set_trace()
        self.perl_script = os.path.join(self.execore.productDir,'core/tstcore/tvm/resources','voip_testcalls.pl')
        self.test_group = "VoIPTest"
        args = {'network': 'tvm_comms', 'subnet_name': 'tvm_comms-sub', 'cidr': '192.168.99.0/24'}
        comms_nw_id = self.execore.createNetwork(**args)
        args = {'network': 'tvm_test', 'subnet_name': 'tvm_test-sub', 'cidr': '192.168.2.0/24'}
        test_nw_id = self.execore.createNetwork(**args)
        args = {'network': 'tvm_mgmt', 'subnet_name': 'tvm_mgmt-sub', 'cidr': '192.168.0.0/24'}
        mgmt_nw_id = self.execore.createNetwork(**args)
        #TODO: Router ID should be from config file instead of hardcoding
        args = {'router_name': 'Router', 'external_network_name': 'public'}
        #args = {'router_name': 'R1', 'external_network_name': 'public'}
        router_id = self.execore.createRouter(**args)

        self.NSD = os.path.join(self.execore.productDir,'core/tstcore/tvm/descriptor','TVM.zip')
        self.templateID = self.execore.onBoard('teravm', self.NSD)

        csObj = self.execore.createServiceRequestObject(router='Router', networks= {'comms-network': comms_nw_id, 'test-network': test_nw_id, 'mgmt-if': mgmt_nw_id})
        csObj['name'] = 'Tvm'
        csObj['qos'] = 'Voip'
        tvm_srv = self.execore.createService(self.templateID, **csObj)
        #self.tvmc_host = tvm_srv['vdus']['Tvm']['vTVMC'][0]['mgmt-ip']
        #self.tvmc_username = tvm_srv['vdus']['Tvm']['vTVMC'][0]['username']
        #self.tvmc_password = tvm_srv['vdus']['Tvm']['vTVMC'][0]['password']
        self.tvmc_host = utils.getVduParameter(tvm_srv['vdus']['Tvm']['vTVMC'][0], 'comms-network')
        self.tvmc_username = utils.getVduParameter(tvm_srv['vdus']['Tvm']['vTVMC'][0], 'username')
        self.tvmc_password = utils.getVduParameter(tvm_srv['vdus']['Tvm']['vTVMC'][0], 'password')

        #self.sip1_ip = tvm_srv['vdus']['Tvm']['vTVMT1'][0]['network-interfaces'][0]['test-nw']['ips']
        self.sip1_ip = self._get_ip(tvm_srv['vdus']['Tvm']['vTVMT1'][0], 'test-network')
        #To change to the 'tvm_test' to get from args
        #self.sip2_ip = tvm_srv['vdus']['Tvm']['vTVMT2'][0]['network-interfaces'][0]['test-nw']['ips']
        self.sip2_ip = self._get_ip(tvm_srv['vdus']['Tvm']['vTVMT2'][0], 'test-network')
        self.gateway_ip = '.'.join(self.sip1_ip.split('.')[:-1])+'.1'
        #get_networks function required Hardcoded as the n/w created by the TF and no gateway specified. So default-considered.
        self.local_path = execore.sessionDir
         
        self.testCaseMap = { 'TEST_SIP_CALLS' : '__exec_sip_calls__',
                             'TEST_SIP_CALLS1' : '__exec_sip_calls__'}
        super(TestCore, self).__init__()

    def __analyze_logs__(self, result_file, *kwargs):
        res_dict =dict()
        tmp_sc = list()
        tmp_fc = list()
        total_sc = 0
        total_fc = 0
        #local_path = '/home/tcs/Music/testF/tvm_scripts'
        with zipfile.ZipFile(self.local_path+'/'+result_file, "r") as z:
            z.extractall(self.local_path+"/tmp_results/")
        with open(self.local_path+"/tmp_results/TestGroup/TestGroupTotals_VoipUA.Normal.csv") as csvfile:
            creader = csv.reader(csvfile)
            for row in creader:
                if row[0] == 'Time':
                    continue
                time = row[0].split('.')[0].replace(' ','\n')
                res_dict[time] = {}
                res_dict[time]['successful_calls'] = int(row[35])
                res_dict[time]['failed_calls'] = int(row[15])
                total_sc = total_sc + int(row[35])
                total_fc = total_fc + int(row[15])

            for val in res_dict.values():
                tmp_sc.append(val['successful_calls'])
                tmp_fc.append(val['failed_calls'])
            result_dict = {'report': {'graph': {}}}
            result_dict['report']['graph'] = {"graph_data" : {}}
            result_dict['report']['graph']['graph_data']['label'] = [tuple(res_dict.keys())]
            result_dict['report']['graph']['graph_data']['data'] = [tuple(tmp_sc),tuple(tmp_fc)]
            result_dict['report']['graph']['graph_data']['legend'] = [("successful_calls","failed_calls")]

            if total_sc+total_fc > 0 :
                cs_rate =  total_sc/(total_sc+total_fc)
        
            if cs_rate == 1:
                test_status = 'PASS'
            else:
                test_status = 'COMPLETE'
            result_dict['report']['table_append'] = {'table_data': {}}
            result_dict['report']['table_append']['table_data']['header'] = ["Test Scenario", "Test Status", "Call Sucess Rate"]
            result_dict['report']['table_append']['table_data']['data'] = [["IMS", test_status, cs_rate]]

        return result_dict


        #return {'report': {'graph': { "graph_data" : {
        #            "label" : [("1","2","3","4","5")],
        #            "data" : [(46,30,35,38,28),(2,14,3,2,1)],
        #            "legend" : [("1","2","3","4","5")]}}}}, self.execore.pdf_obj
        #return {'report': 'graph'}

    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __exec_sip_calls__(self, **kwargs):
        import pdb;pdb.set_trace()
        self._init_args(**kwargs)
        tvmc_ftp = FTP(self.tvmc_host, self.tvmc_username, self.tvmc_password)
        remote_dir_path = '/home/'+self.tvmc_username+'/testframework_tmp'
        result_filename = "tvm_results_"+time.strftime("%Y%m%d-%H%M%S")+".zip"
        
        tvmc_ftp.mkd(remote_dir_path)

        files_list = [self.tvm_config_file, self.caller_list, self.callee_list, self.perl_script]
        file_names = dict(zip(['config_file', 'caller_list', 'callee_list', 'perl_script'],[x.split('/')[-1] for x in files_list]))
        for fil in files_list:
            tvmc_ftp.cwd(remote_dir_path)
            tvmc_ftp.storbinary('STOR '+fil.split('/')[-1], open(fil, 'rb'))
        tvmc_ftp.quit()

        import pdb;pdb.set_trace()
        #time.sleep(180)
        tvmc_client = utils.get_ssh_conn(self.tvmc_host, self.tvmc_username, self.tvmc_password)
        interfaces = tvmutils.get_interfaces(tvmc_client)
        while len(interfaces) != 2:
            interfaces = tvmutils.get_interfaces(tvmc_client)
        #output, err = utils.exec_command("cli listInterfaces| tail --lines=+2 | awk '{print $1}'", client=tvmc_client)
        #interfaces = output.rstrip('\n').split('\n')
        

        import pdb;pdb.set_trace()
        cmd_perl = "perl "+remote_dir_path+'/'+file_names['perl_script']+" --config "+remote_dir_path+'/'+file_names['config_file']+' --calleelist '+remote_dir_path+'/'+file_names['callee_list']+' --callerlist '+remote_dir_path+'/'+file_names['caller_list']
        for interface_num in range(0, len(interfaces)):
            cmd_perl = cmd_perl + ' --interface '+interfaces[interface_num]
        cmd_perl = cmd_perl+"> voip_onecall.xml"
      
        cmds = [cmd_perl, "cli importTestGroup \"//\" voip_onecall.xml", "cli startTestGroup "+self.test_group, "cli listHosts|awk '{print $1, $3}'", "cli listApplications "+self.test_group+"|awk '{print $1, $3}'", "cli saveTestGroupCurrentDetailedResults "+self.test_group+" "+remote_dir_path+"/"+result_filename, "cli stopTestGroup "+self.test_group, "cli deleteTestGroup "+self.test_group]
        for cmd in cmds:
            import pdb;pdb.set_trace()
            try:
                output, err = utils.exec_command(cmd, client=tvmc_client)
            except:
                pass
            if 'awk' in cmd:
                 for line in output.rstrip().split('\n')[1:]:
                     if line.split()[1] != "Active":
                         print "Error"
                         #self.logger.warn("Error: %s not configured!!", line.split()[0])
            elif 'save' in cmd:
                 tvmc_ftp = FTP(self.tvmc_host, self.tvmc_username, self.tvmc_password)
                 tvmc_ftp.cwd(remote_dir_path)
                 tvmc_ftp.retrbinary('RETR '+remote_dir_path+'/'+result_filename, open(self.local_path+'/'+result_filename, 'wb').write)
                 tvmc_ftp.quit()
            elif 'stop' in cmd:
                 tvmc_ftp = FTP(self.tvmc_host, self.tvmc_username, self.tvmc_password)
                 tvmc_ftp.cwd(remote_dir_path)
		 for fil in tvmc_ftp.nlst():
                     tvmc_ftp.delete(fil)
                 tvmc_ftp.cwd('/home/'+self.tvmc_username)
                 tvmc_ftp.rmd(remote_dir_path)
                 tvmc_ftp.quit()
            elif 'start' in cmd:
                 time.sleep(100)    
            else:
                pass
        return self.__analyze_logs__(result_filename)

    def _get_ip(self, vdu_instance, ntw):
        for list_ntw in range(0, len(vdu_instance['network-interfaces'])):
            if ntw in vdu_instance['network-interfaces'][list_ntw].keys():
                return vdu_instance['network-interfaces'][list_ntw][ntw]['ips']
