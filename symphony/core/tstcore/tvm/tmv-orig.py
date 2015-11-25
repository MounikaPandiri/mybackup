import time
import zipfile
import csv

from report import report
from ftplib import FTP
from core.tstcore.testcore import testCore
from common import utils
from core.tstcore.tvm import utils as tvmutils
from core import executionCore
import os

class tvm(testCore):

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
        router_id = self.execore.createRouter(**args)

        self.NSD = os.path.join(self.execore.productDir,'core/tstcore/tvm/descriptor','tvm.zip')
        self.templateID = self.execore.onBoard('teravm', self.NSD)

        csObj = self.execore.createServiceRequestObject(router='Router', networks= {'comms-network': comms_nw_id, 'test-network': test_nw_id, 'mgmt': mgmt_nw_id})
        csObj['name'] = 'Tvm'
        csObj['qos'] = 'Voip'
        tvm_srv = self.execore.createService(self.templateID, **csObj)
         
        self.local_path = self.execore.sessionDir
        self.result_filename = "tvm_results.zip"
        self.testCaseMap = { 'TEST_SIP_CALLS' : '__analyze_logs__',
                             'TEST_SIP_CALLS1' : '__analyze_logs1__'}
        super(testCore, self).__init__()

    def __analyze_logs__(self, **kwargs):
        res_dict =dict()
        tmp_sc = list()
        tmp_fc = list()
        #local_path = '/home/tcs/Music/testF/tvm_scripts'
        with zipfile.ZipFile(self.local_path+'/'+self.result_filename, "r") as z:
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

            for val in res_dict.values():
                tmp_sc.append(val['successful_calls'])
                tmp_fc.append(val['failed_calls'])
            result_dict = {'report': {'graph': {}}}
            result_dict['report']['graph'] = {"graph_data" : {}}
            result_dict['report']['graph']['graph_data']['label'] = [tuple(res_dict.keys())]
            result_dict['report']['graph']['graph_data']['data'] = [tuple(tmp_sc),tuple(tmp_fc)]
            result_dict['report']['graph']['graph_data']['legend'] = [("successful_calls","failed_calls")]
            return result_dict, self.execore.pdf_obj


        #return {'report': {'graph': { "graph_data" : {
        #            "label" : [("1","2","3","4","5")],
        #            "data" : [(46,30,35,38,28),(2,14,3,2,1)],
        #            "legend" : [("1","2","3","4","5")]}}}}, self.execore.pdf_obj
        #return {'report': 'graph'}

    def __analyze_logs1__(self, **kwargs):
        return {'report': {'barChart': {"bar_data" : {
                    "label" : [("1","2","3","4","5")],
                    "data" : [(1,2,3,4,5)],
                    "legend" : [tuple("1")]
                    }}}}, self.execore.pdf_obj

    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __exec_sip_calls__(self, **kwargs):
        self._init_args(**kwargs)
        tvmc_ftp = FTP(self.tvmc_host, self.tvmc_username, self.tvmc_password)
        remote_dir_path = '/home/'+self.tvmc_username+'/testframework_tmp'

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
        while len(interfaces) != num_of_test_clients():
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
            output, err = utils.exec_command(cmd, client=tvmc_client)
            if 'awk' in cmd:
                 for line in output.rstrip().split('\n')[1:]:
                     if line.split()[1] != "Active":
                         print "Error"
                         #self.logger.warn("Error: %s not configured!!", line.split()[0])
            elif 'save' in cmd:
                 tvmc_ftp = FTP(self.tvmc_host, self.tvmc_username, self.tvmc_password)
                 tvmc_ftp.cwd(remote_dir_path)
                 tvmc_ftp.retrbinary('RETR '+remote_dir_path+'/'+result_filename, open(self.local_path+'/'+self.result_filename, 'wb').write)
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
           
        #self.analyze_logs(local_path, result_filename)
