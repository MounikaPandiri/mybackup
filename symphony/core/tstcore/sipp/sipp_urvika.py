import time
from ftplib import FTP
from common import utils
from core.tstcore.sipp import utils as sipputils
from core import executionCore
from core.tstcore.testcore import testCore
import os
import logging.config
from paramiko import *

logger = logging.getLogger(__name__)


class sipp(testCore):

    def __init__(self, exeCore):
        """onboard the test framework"""
        import pdb;pdb.set_trace()
        sipp_config = {}
        self.execore = exeCore
        self.sipp_cfg = sipputils._get_sipp_config()
        self._base = self.sipp_cfg['base_number']
        self.tests_result = []

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
        self.report = sipputils._init_report()

        self.testCaseMap = { 'TEST_SIP_WITH_RTP' : '__exec_sip_rtp__', 
                             'TEST_SIP_WITHOUT_RTP' : '__exec_sip_no_rtp'}
        super(testCore, self).__init__()


    def _init_args(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __exec_sip_rtp__(self, **kwargs):
        #self.sip1_client = utils.get_ssh_conn(self.sip1_ip, self.sip1_username, self.sip1_password) 
        #self.sip2_client = utils.get_ssh_conn(self.sip2_ip, self.sip2_username, self.sip2_password)
        import pdb;pdb.set_trace()
        self._init_args(**kwargs)
        sip1_invite_file = self._register_users(self.sip1_ip, client=self.sip1_client, rtp=True, caller=True)
        self._register_users(self.sip2_ip, client=self.sip2_client, rtp=True)
        import pdb;pdb.set_trace()
        invite_testscript = self.sipp_cfg['remote_files_path'] + "/invite_final_rtp.xml" 
        send_testscript = self.sipp_cfg['remote_files_path'] + "/send_final_rtp.xml"
        result = self._establishCalls(self.sip1_ip, self.sip2_ip, self.sip1_client, self.sip2_client, send_testscript, invite_testscript, sip1_invite_file, rtp=True)

        return sipputils._report(result, self.report)

    def __exec_sip_no_rtp(self, **kwargs):
        self._init_args(**kwargs)


    def _register_users(self, sip_ip, client, rtp=False, caller=False):
        if caller:
            user_file, invite_file = self._generate_users(client, rtp, caller)
        else:
            user_file = self._generate_users(client, rtp, caller)
        try:
            reg_cmd = self._generate_register_cmd(user_file, sip_ip)
            result, error = utils.exec_command(reg_cmd, client)
            time.sleep(30)
            self._base = self._base + self.users
            self._analyze_log(client, result, "register")
            if caller:
                return invite_file
        except:
            logger.debug("Unable to register users.")
            return ""

    def _analyze_log(self, client, result, action, rtp=False):
        """Gets the file from remote server to local and analyzes the log
           against the patameters sdpecified."""
        local_path = self.execore.sessionDir
       
        pid = int(result[result.find("[") + 1: result.find("]")]) - 1
        file_list = []
        if action == "register":
            stats_file_name = "register3_3_" + str(pid) + "_.csv"
            screen_log = "register3_3_" + str(pid) + "_screen.log"
        elif action == "invite":
            if rtp:
                stats_file_name = "invite_final_rtp_" + str(pid) + "_.csv"
                screen_log = "invite_final_rtp_" + str(pid) + "_screen.log"
            else:
                stats_file_name = "invite_final_1_" + str(pid) + "_.csv"
                screen_log = "invite_final_1_" + str(pid) + "_screen.log"
        elif action == "listen":
            if rtp:
                stats_file_name = "send_final_rtp_" + str(pid) + "_.csv"
                screen_log = "send_final_rtp_" + str(pid) + "_screen.log"
            else:
                stats_file_name = "send_final_" + str(pid) + "_.csv"
                screen_log = "send_final_" + str(pid) + "_screen.log"
        else:
            logger.debug("Invalid action %s" % action)
            return
        while True:
            stdin, stdout, stderr = client.exec_command(
                "ps aux | awk '$2 == PID " + str(pid) + "  { print $0}'")
            if len(stderr.read()) == 0 and len(stdout.read()) == 0:
                break
        file_list.append(stats_file_name)
        file_list.append(screen_log)
        for file_name in file_list:
            remote_file_path = self.remote_path + "/" + file_name
            local_file_path = os.path.join(local_path, file_name)
            try:
                os.chdir(local_path)
            except OSError:
                os.mkdir(local_path)
                os.chdir(local_path)
            try:
                sftp = client.open_sftp()
                sftp.get(remote_file_path, local_file_path)
            except IOError as e:
                logger.debug("Unable to get the files from remote machine")
                if e.errno == errno.ENOENT:
                    pid_index = file_name.find(str(pid))
                    if file_name[-3:] == "csv":
                        file_name = file_name[
                            :pid_index] + str(pid - 1) + '_.csv'
                        stats_file_name = file_name
                    else:
                        file_name = file_name[
                            :pid_index] + str(pid - 1) + '_screen.log'
                    sftp = client.open_sftp()
                    try:
                        sftp.get(
                            os.path.join(
                                self.remote_path, file_name), os.path.join(
                                local_path, file_name))
                    except:
                        logger.debug("Unable to analyze log")
        try:
            with open(os.path.join(local_path, stats_file_name), 'rb') as csf:
                reader = csv.reader(csf, delimiter=';')
                data = []
                for row in reader:
                    data.append(row)
                final_result = len(data) - 1
                result = {}
                for item in range(0, len(data[0])):
                    result[data[0][item]] = data[final_result][item]
                logger.debug(
                    "Log analysis for %s action is %s" %
                    (action, pprint.pformat(result)))
                return result
        except:
            logger.debug("Unable to analyze log")


    def _generate_register_cmd(self, csv, ip):
        #need to fix variable ip
        return "/home/tcs/sipp-3.4.1/sipp " + self.ellis + \
               " -sf /home/tcs/scripts/register3_3.xml  -inf " + csv + \
               " -rsa " + self.bono + ":5060 -p " + str(self.sip_port) + " -i " + \
               ip + " -trace_screen -trace_stat -m " + str(self.users) + " -l " + \
               str(self.load) + " -r " + str(self.concurrency) + " -rp " + self.time + " -bg"


    def _generate_users(self, client, rtp=False, caller=False):
        import pdb;pdb.set_trace()
        """ Generated SIP users with IMS """
        if rtp:
            file_name = "register_rtp_"+self.users
        else:
            file_name = "register_no_rtp_"+self.users

        cmd = "python /home/tcs/scripts/EllisClient.py --ellis_ip " + self.ellis + " --call_count " + \
               str(self.users) + " --base_number " + str(self._base) + " --file_name " + file_name

        if caller:
             cmd += " --caller"
        try: 
            result, error = utils.exec_command(cmd, client)
        except:
            logger.debug("Unable to generate sip users.")

        #Get remote path from the config file.
        if caller:
            return self.sipp_cfg['remote_files_path']+'/'+file_name+'.csv', self.sipp_cfg['remote_files_path'] + \
                   "/invite_without_rtp_" + str(self.users) + ".csv"
        else:
            return self.sipp_cfg['remote_files_path']+'/'+file_name+'.csv'


    def _establishCalls(self, sip1_ip, sip2_ip, client1, client2, listen_testscript, invite_testscript, invite_csv, rtp=True):
        import pdb;pdb.set_trace()
        result_details = {}
        result_details['id'] = users
        if rtp:
            result_details['name'] = "Call test with RTP"
        else:
            result_details['name'] = "Call test without RTP"
        result_details['description'] = "Tests the IMS setup by making calls"
        result_details['category'] = self.test_type

        listen_cmd = self._generate_send_command(sip2_ip, listen_testscript)
        listen_result, err = utils.exec_command(listen_cmd, client2)
        time.sleep(50)
        invite_cmd = self._generate_invite_command(sip1_ip, invite_csv, invite_testscript)
        invite_result, err = utils.exec_command(invite_cmd, client1)

        #Analyze the invite and listen result
        invite_result = self._analyze_log(client1, invite_result, "invite", rtp=True)
        listen_result = self.analyze_log(client1, listen_result, "listen", rtp=True)

        if self.test_type == "Performance":
            success_rate = load * 0.95
        else:
            success_rate = load

        if int(invite_result['SuccessfulCall(C)']) >= success_rate:
            result_details['status'] = "PASSED"
        else:
            result_details['status'] = "FAILED"
        result_details['call_rate'] = invite_result['CallRate(C)']
        result_details['successful_calls'] = invite_result['SuccessfulCall(C)']
        result_details['failed_calls'] = invite_result['FailedCall(C)']
        except:
            result_details['status'] = "FAILED"
            result_details['call_rate'] = 0
            result_details['successful_calls'] = 0
            result_details['failed_calls'] = 0
        self.logger.info(
            "Runner - %d: Test Result is %s" %
            (runner, result_details['status']))
        self.tests_result.append(result_details)
        return result_details


    def _generate_invite_command(self, sip_ip, csv, testscript):
        return "/home/tcs/sipp-3.4.1/sipp " + self.bono + " -sf " + testscript + "  -inf " + csv + "  " + self.bono + " -rsa " + self.bono + ":5060 -p " + \
            str(self.sip_port) + " -i " + sip_ip + " -trace_screen -trace_stat -m " + str(self.load) + " -l " + str(self.concurrency) + " -r " + str(self.call_count) + " -rp " + self.time + " -bg"


    def _generate_send_command(self, sip_ip, testscript):
        return "/home/tcs/sipp-3.4.1/sipp " + self.bono + " -sf " + testscript  + " " + \
               self.bono + ":5060 -rsa " + self.bono + ":5060 -p " + \
            str(self.sip_port) + " -i " + sip_ip + " -trace_screen -trace_stat -m " + \
            str(self.load) + " -l " + str(self.concurrency) + " -r " + str(self.call_count) + " -rp " + self.time + \
            " -bg"
