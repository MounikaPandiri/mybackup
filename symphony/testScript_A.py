from common import utils
from core import executionCore

class testData(object):

    def __init__(self):
        pass

    def run(self, execore):
        execore.set_report_title("TeraVM VOIP Execution with Clearwater IMS.")
        args = {'network': 'mgmt-if', 'subnet_name': 'mgmt-sub', 'cidr': '192.168.10.0/24'}
        mgmt_nw_id = execore.createNetwork(**args)
        args = {'network': 'ims-private', 'subnet_name': 'private-sub', 'cidr': '192.168.11.0/24'}
        private_nw_id = execore.createNetwork(**args)
        args = {'router_name': 'Router', 'external_network_name': 'public'}
        router_id = execore.createRouter(**args)

        ims_templateID = execore.onBoard('ims','/home/tcs/templates/Ims/zip/ims.zip')
        #ims_templateID = execore.onBoard('ims','/home/openstack/urvika/templates/Ims/zip/ims.zip')

        csObj = execore.createServiceRequestObject(router='Router', networks= {'mgmt-if': mgmt_nw_id, 'private': private_nw_id})
        csObj['name'] = 'Ims'
        csObj['qos'] = 'Silver'
        #TOCHK: Is Template ID required for create service??
        ims_srv = execore.createService(ims_templateID,**csObj)
        import pdb;pdb.set_trace()
        sip_external_proxy = utils.getVduParameter(ims_srv['vdus']['Ims']['vBono'][0], 'pkt-in')
        ellis_ip = utils.getVduParameter(ims_srv['vdus']['Ims']['vEllis'][0], 'mgmt-ip')
        import pdb;pdb.set_trace()
        tstCore = execore.initTest('tvm')

        import pdb;pdb.set_trace()
        tvm_ctl = tstCore.__dict__['tvmc_host']
        tvmc_username = tstCore.__dict__['tvmc_username']
        tvmc_password = tstCore.__dict__['tvmc_password']
        users = 5
        base = 6505550000
        sip1_ip = tstCore.__dict__['sip1_ip']
        sip2_ip = tstCore.__dict__['sip2_ip']
        gateway_ip = tstCore.__dict__['gateway_ip']
        file_name = "servers"
        fb = open(execore.sessionDir+'/'+file_name+'.ini', 'wb')
        test_group = "VoIPTest"
        fb.write("TestGroup_Name:"+test_group+"\nTVM1:"+sip1_ip+"/24\nTVM2:"+sip2_ip+"/24\nGateway_IP:"+gateway_ip+"\nSIPProxy_IP:"+sip_external_proxy);
        fb.close()
        cmd = "python /home/tcs/tvm_code/EllisClient.py --ellis_ip " + ellis_ip + " --call_count " + \
              str(users) + " --base_number " + base + "--Dir_path "+execore.sessionDir
        result, error = utils.exec_command(cmd)
        args1 = {}
        args1['tvmc_host'] = tvm_ctl
        args1['tvmc_username'] = tvmc_username
        args1['tvmc_password'] = tvmc_password
        args1['tvm_config_file'] = execore.sessionDir+'/'+file_name+'.ini'
        args1['caller_list'] = execore.sessionDir+'/callerlist.ini'
        args1['callee_list'] = execore.sessionDir+'/calleelist.ini'
        args1['test_group'] = test_group
        import pdb;pdb.set_trace()
        tstCore.execute('TEST_SIP_CALLS', **args1)

        base = base + users
        users = 10
        cmd = "python /home/tcs/tvm_code/EllisClient.py --ellis_ip " + ellis_ip + " --call_count " + \
              str(users) + " --base_number " + base + "--Dir_path "+execore.sessionDir
        result, error = utils.exec_command(cmd)
        tstCore.execute('TEST_SIP_CALLS', **args1)

        base = base + users
        users = 20
        cmd = "python /home/tcs/tvm_code/EllisClient.py --ellis_ip " + ellis_ip + " --call_count " + \
              str(users) + " --base_number " + base + "--Dir_path "+execore.sessionDir
        result, error = utils.exec_command(cmd)
        tstCore.execute('TEST_SIP_CALLS', **args1)

        base = base + users
        users = 50
        cmd = "python /home/tcs/tvm_code/EllisClient.py --ellis_ip " + ellis_ip + " --call_count " + \
              str(users) + " --base_number " + base + "--Dir_path "+execore.sessionDir
        result, error = utils.exec_command(cmd)
        tstCore.execute('TEST_SIP_CALLS', **args1)

        base = base + users
        users = 100
        cmd = "python /home/tcs/tvm_code/EllisClient.py --ellis_ip " + ellis_ip + " --call_count " + \
              str(users) + " --base_number " + base + "--Dir_path "+execore.sessionDir
        result, error = utils.exec_command(cmd)
        tstCore.execute('TEST_SIP_CALLS', **args1)

        
        #flavor_args = {'vcpus':'10','disk':'2048','name':'symphony','ram':'1024'}
        #import pdb;pdb.set_trace()
        #execore.createFlavor(**flavor_args)
        #execore.deleteTemplate(templateID)
        pass
