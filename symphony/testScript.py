from common import utils
from core import executionCore

class testData(object):

    def __init__(self):
        pass

    def run(self, execore):
        self.execore = execore
        execore.set_report_title(title="VoIP test result with Clearwater IMS")
        args = {'network': 'mgmt-if', 'subnet_name': 'mgmt-sub', 'cidr': '30.0.0.0/24'}
        mgmt_nw_id = execore.createNetwork(**args)
        args = {'network': 'private1', 'subnet_name': 'private-sub', 'cidr': '20.0.0.0/24'}
        private_nw_id = execore.createNetwork(**args)
        args = {'router_name': 'vnf','external_network_name':'public'}
        router_id = execore.createRouter(**args)

        ims_templateID = execore.onBoard('ims','/home/openstack/latest_code/templates/Ims/zip/Ims.zip')

        nsArgs={}
        nsArgs['router'] = 'vnf' 
        nsArgs['networks'] = {'mgmt-if': mgmt_nw_id, 'private': private_nw_id}
        nsArgs['name'] = 'Ims'
        nsArgs['qos'] = 'Silver'
        ims_srv = execore.createService(ims_templateID, **nsArgs)

        ntwIf = {'protocol' : ['ICMP','SCTP','TCP'],
                 'service': ims_srv,
                 'VNF' :
                       [{ 'vdu': 'vSprout', 'iface' : 'pkt-in', 'file' : ['/var/log/messages']},
                       { 'vdu' : 'vBono', 'iface' : 'pkt-in', 'file' : ['/var/log/messages']},
                       { 'vdu' : 'vEllis', 'iface' : 'pkt-in', 'file' : ['/var/log/messages']}]
                }
        import pdb;pdb.set_trace()
        #execore.enableDiagnostics(**ntwIf)
        #Initating SIPP as NetworkService
        #execore.startDiagnostics()
        
        '''tstCore = execore.initTest('sipp')
        
        #Get Ellis and Bono details from service object
        self.ellis_ip=utils.getVduParameter(ims_srv['vdus']['Ims']['vEllis'][0], 'pkt-in')
        self.bono_ip=utils.getVduParameter(ims_srv['vdus']['Ims']['vBono'][0], 'pkt-in')
        
        #self.ellis_ip='20.0.0.6'
        #self.bono_ip='20.0.0.7'
        #Test SIP with RTP (10 users)
        
        args={}
        
        args['ellis']=self.ellis_ip
        args['bono']=self.bono_ip

        args['load']='10'
        args['call_count']='5'
        args['concurrency']='5'
        args['time']='1s'
        args['sip_port']='5060'
        args['test_type']='functional'
        
        args['users'] = '5'
        args['test_runs']=1
        
       	tstCore.execute('TEST_SIP_WITHOUT_RTP', **args)
       	tstCore.execute('TEST_SIP_WITH_RTP', **args)'''
	#_______________________________________________
