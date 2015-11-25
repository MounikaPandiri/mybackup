# Copyright 2014 Tata Consultancy Services Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
###############################################################################
# This module provides the core api to communicate with the execution engine
###############################################################################
try:
	import uuid
	import os
	import sys
	cwd=os.getcwd()
	cwd=cwd.split('/')
	sysPath=''
	for dirName in range(1,len(cwd)-1):	#for determining path to root directory
		sysPath=sysPath+'/'+cwd[dirName]

	sys.path.append(sysPath)
	import inspect
	from oslo_config import cfg
	from common import config, utils, API, openstack, schema
	import shutil
	import eventListner
	from eventListner import EventListner
	import eventlet
	import socket
	import threading
	import xmltodict
	import requests
	import json
	import copy
	from termcolor import colored,cprint
	from report import report_generator
        from diagnostics import packetsniffer
        from diagnostics import diagnostics
except Exception as e:
	import os
	print os.getcwd()
	print 'import error--> ',e
	sys.exit()

def tracefunc(frame, event, arg, indent=[0]):
      if  event == "call" : #) or (event == "return") :
          try:
              if 'executionCore' in frame.f_back.f_globals['__name__'] :
                  print_screen_log(frame.f_code.co_name)
          except:
              pass
      return tracefunc

import sys
sys.settrace(tracefunc)

def print_screen_log(name):
    head = "\n****----"
    tail = "----****"
    if name == 'initTestServices':
       text = head + "Initializing Traffic Generator"+tail
    elif "create_private_sessionDir" == name :
       text =head + "Setting up user session" + tail
    elif name == '__onboard__' :
       text = head+'Onboarding service Template'+tail
    elif name == 'register' :
       text = head+'Registering Event Framework'+tail
    elif name == '__create_service__' :
       text = head+'Triggering Service Creation'+tail
    elif name == 'deleteService' :
       text = head+'Cleanup - Deleting Service'+tail
    elif name =='create_pdf' :
       text = head+'Reporting results'+tail
    elif name == 'deleteTemplate' :
       text = head+"Deleting Service Template"+tail
    else :
       #text = head + " " + name + " " + tail
       #cprint(text,'red',attrs=['underline'])
       ##print text #(text,'red',on_color='on_grey',attrs=['bold'])
       return 

    cprint(text,'green',on_color='on_blue',attrs=['bold'])
    ##print text #,'green',on_color='on_blue',attrs=['bold'])


def __check_queue__(method):
	def dequeue(self,*args,**kwargs):
		try :
			retVal = method(self,*args,**kwargs)
                        if utils.comm_queue.__len__() != 0:
		       	    xmlObj = utils.comm_queue.pop()
			#convert the XML object into serviceDict
			    serviceDict = xmltodict(xmlObj)
			return retVal
		except :
			pass

	return dequeue

class ExecutionCore(threading.Thread):

    """Core module to talk to execution engine"""

    def __init__(self, cfg, configFile, testScript,eventHost='localhost',eventPort=0,queue=utils.comm_queue):
	self.API = API.API(cfg) #execute the API for VNFManager. Preload credentials to connect to VNFManager
        self.sessionID = uuid.uuid4() #geht a uuid based on timestamp and host to track the user session ID
        self.configFile = configFile #TO-DO : Validate the validity of this file
        self.testScript = testScript #TO-DO : Validate the validity of this file
        self.sessionDir = 'None' #Value is set in create_private_sessionDir method when directory is successfully created
        self.testScriptDir = 'None' #Value is set in prepareSession when directory is successfully created
	self.moduleName = 'None'
	self.productDir = os.path.abspath(os.path.curdir)#get directory
	self.testModule = '' #placeholder for the test script python module
        self.eventHost = eventHost
	self.eventPort = eventPort
	self.eventThreadID = -1
	self.eventQueue = queue
        self.baseDir = '/var/symphony/session_data'
	self.serviceInfo = dict()
	self.flavor = dict()
	self.routers = dict()
        self.nsInfo = dict()
	self.networks={}
        self.title = "Report"
        self.ns_diagnostics = {}
        self.diagnostics=diagnostics.Diagnostics(self)
	threading.Thread.__init__(self)


    def run(self):
        try:
	    self.testServices = self.initTestServices()
            self.create_private_sessionDir()
            self.prepareSession()
	    #Start execution of the test module
            self.testModule.run(self)
            self.cleanup()#We completed test script execution. So unboard the services and generate report
        except:
            self.cleanup()#We errored in test script execution. So unboard the services
            raise 
	
    def create_private_sessionDir(self):
        """All session information is stored in the root node
        Each session is allowed to store 50GB of data
        Check for minimum allowed storage and create dir for this session"""
         
        unique_fileName = str(self.sessionID)
        session_dir = os.path.join(self.baseDir,unique_fileName)
        
        try:
            os.mkdir(session_dir) 
            self.sessionDir = session_dir
            #if a directory with the same session ID exists raise exception
        except:
            raise

    def prepareSession(self):
        """Session test script is copied into the session directory
        Test script is prepared as a python module to enable execution"""

        shutil.copy(self.configFile, self.sessionDir)
        
	#copy the test script into the session directory
        shutil.copy(self.testScript, self.sessionDir)

        #create an __init__ file here for us to import test script as <session_id>.script.<test_script>
        session_init_file = os.path.join(self.sessionDir,'__init__.py')
        utils.Utils.touch(session_init_file)
	
	#Extract the name of the test script from input arguments
	#first split the input into directory name and filename.extn
	directoryName,fileName = os.path.split(self.testScript)
	
	#now split filename and extension
	moduleName = os.path.splitext(fileName)[0]
	self.moduleName = moduleName
        
	#the path would be <sessionDir>.script.testModule
        script_import_path = "'"+str(self.sessionID)+'.script.'+moduleName+"'"

        #make sure that the path is available in sys.path
        sys.path.append(self.sessionDir)
        _testModule = __import__(self.moduleName, globals(), locals(), [], -1)
        self.testModule = _testModule.testData()

    def initTest(self,trafficGenerator):
	"""Initialize the traffic generator"""
	if trafficGenerator not in self.availableTestSuite :
		raise ValueError('Unsupported Traffic generator. Please check script')
	
        #load requested traffic module and initialize it
        testModulePath = os.path.join(self.productDir,'core/tstcore',trafficGenerator)
        sys.path.append(testModulePath)
        trafficGen = __import__(trafficGenerator,globals(), locals(), [], -1)
	self.trafficGen = getattr(trafficGen,trafficGenerator)(self)
	return self.trafficGen
	

    def onBoard(self, serviceName=None,path=None):
        """Onboard the service descriptor onto Virtual Infrastructure Manager"""
        objTemplate = self.API.__onboard__(serviceName,path)
	#extract data from template object
	#what if we were'nt able to upload successfully
	if 'VnfsvcError' in objTemplate.keys() :
		raise ValueError(objTemplate['VnfsvcError']['message'])

	templateID = objTemplate['template']['id']
	self.serviceInfo[templateID] = objTemplate
        retryCount = 0
        try:
            self.register(templateID)
        except:
            #Sometimes the flsk server might not be up. Retry for subscription
            if retryCount == 0:
                self.register(templateID)
                retryCount = retryCount+1
            else:
                raise

	return templateID

    @__check_queue__
    def createServiceRequestObject(self, **kwargs):
        #def createServiceRequestObject(self, name=None, qos=None, router=None, networks=None, description=None):
        csObj = {}

        try:
            csObj['name'] = kwargs['name']
            csObj['qos'] = kwargs['qos']
            if 'description' in kwargs.keys():
                csObj['description'] = kwargs['description']
         
            attributes = {'router': None, 'networks': {}, 'subnets': {}}
            if 'router' in kwargs.keys():
                attributes['router'] = kwargs['router']
            #TODO: Wrong Assumption that user will use same name for networks in openstack and in nsd templates
            #      This needs to be changed in future as service create is just a mapping of name in template to
            #      actual network id
            for net, net_id in kwargs['networks'].iteritems():
                #TODO: Change logic here to get Rvalue from networks dict based on ID not on name
                attributes['networks'][net] = net_id
                attributes['subnets'][net] = self.networks[net_id]['subnets']['id']
         
            csObj['attributes'] = attributes
            return csObj
        except:
            raise ValueError("Errored while processing the network servive creation request")


    def createService(self, templateID, block=True,**kwargs) :
        try:
            svcObj = self.createServiceRequestObject(**kwargs)
	    objTemplate = self.serviceInfo[templateID]
	    serviceName = objTemplate['template']['service_type']
	    svcDetails = self.API.__create_service__(serviceName, **svcObj)
	    if block:
                return self.waitForServiceCreate(templateID, svcDetails['service']['id'])
        except:
            raise

    def deleteService(self, serviceID, block=True):
        if serviceID in self.nsInfo.keys() :
            try :
                self.API.__delete_service__(serviceID)
                svcInfo = self.getServiceInfo(serviceID)
                templateID = svcInfo.get('template_id', None)
                if block:
                    self.waitForServiceDelete(templateID, serviceID)
            except:
                raise ValueError("uanble to delete the service")
        else :
            raise ValueError("Invalid service ID.")

    @__check_queue__
    def deleteTemplate(self,templateID) :
	if templateID in self.serviceInfo.keys() :
		return self.API.__del_template__(templateID)
	raise ValueError('Template ID does not exist. Invalid delete operation')


    def initTestServices(self) :
	"""Initialize the testCore"""
	self.availableTestSuite = utils.Utils.loadAvailableTestServices()
	return

    def createFlavor(self,**kwargs):
	retVal = self.API.__flavor_create__(**kwargs)
	#capture the required information in flavor dictionary
	flavorName = kwargs['name']
	if 'conflictingRequest' in retVal :
		#flavor already exists. get the info
		flavorList = self.API.__flavor_list__()
		if any(flavorName in flavor['name'] for flavor in flavorList['flavors']) :
			raise ValueError('Flavor already exists')
	else :
		self.flavor[retVal['flavor']['id']] = retVal
		return retVal['flavor']['id']

    def deleteFlavor(self, flavorID):
	if flavorID in self.flavor :
		self.API.__flavor_delete__(flavorID)

    def createSerialConsole(self,**kwargs):
        retVal = self.API.__create_serial_console__(**kwargs)
        #capture the required information in flavor dictionary
        if not retVal:
            return None

        return retVal['console']['url']

    def createNetwork(self,**kwargs):
	#does this network already exist in our db
	if 'network' in kwargs.keys():
		network_name=kwargs['network']
	else :
		raise ValueError("missing arguments to create network")
	#search for this network name
	#if not any(network.get('name',None) == network_name for network in self.networks):
	if network_name in self.networks.keys():
		return self.networks[network_name]['id']
	else :
		retVal = self.API.__create_network__(**kwargs)
		#we get the network dict. Add this to execore
		self.networks[retVal['id']] = retVal
        
        return retVal['id']


    def createRouter(self,**kwargs):
	"""Create a router"""
	retVal = self.API.__create_router__(**kwargs)
	self.routers[retVal['router']['id']] = retVal['router']
	return retVal['router']['id']

    def checkServiceStatus(self,templateID, nsID):
	try:
	    eventObj = utils.comm_queue.pop()
            cprint(eventObj,'green',on_color='on_blue',attrs=['bold'])         
            eventObj = eventObj.lower()

	except:
	    return False

        if ("error" in eventObj) or ("exception" in eventObj):
           raise ValueError("FATAL : Service creation failed.")

        if "complete" in eventObj:
            return True

        else:
            return False

    def waitForServiceCreate(self,templateID, nsid):
	'''Wait for the event notification on service creation'''
        loopCount = 0
	utils.eventNotification.acquire()
	while not self.checkServiceStatus(templateID, nsid):
            loopCount = loopCount+1
            if loopCount >= schema.MAX_RETRIES: 
                raise ValueError("Max Retries exceeded. Unable to create service.")
            else :
                utils.eventNotification.wait()

        loopCount = 0
        servicedict = self.getSvcObj(templateID, nsid)
        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
        self.nsInfo[nsid] = self.buildNSinfo(servicedict)
        print "********************************************************************\n"
        print self.nsInfo[nsid]

        if utils.diagnostics_enabled:
           self.ns_diagnostics.update(self.nsinfo)
           

	utils.eventNotification.release()
        return self.nsInfo[nsid]

    def waitForServiceDelete(self,templateID, nsid):
        '''Wait for the event notification on service creation'''
        utils.eventNotification.acquire()
        while not self.checkServiceStatus(templateID, nsid):
                utils.eventNotification.wait()
        del self.nsInfo[nsid]
        utils.eventNotification.release()

    def register(self, templateid, uname='default', pwd='default'):
        """Register the user with Virtual Infrastructure Manager"""
        #get the endpoint in the form http://127.0.0.1:3123/Insert
        endpoint = "http://"+socket.gethostbyname(self.eventHost)+":"+str(self.eventPort)+"/Insert"
        try:
            objRegister = self.API.__register__(uname, pwd, endpoint, templateid)
        except:
            raise ValueError('Event Subscription failed')

        if 'VnfsvcError' in objRegister.keys() :
                raise ValueError(objRegister['VnfsvcError']['message'])
        userID = objRegister['register']['id']
        #self.serviceInfo[userID] = objRegister
        return userID

    def getSvcObj(self, templateID, nsID):
        tafEndpoint = "http://"+socket.gethostbyname(self.eventHost)+":"+str(self.eventPort)+"/nsinfo"
        uri = tafEndpoint+'?template_id='+templateID+'&ns_id='+nsID
        xmlObj = requests.get(uri)
        serviceDict = json.dumps(xmltodict.parse(xmlObj.content))
        serviceInfo = schema.ns_dict
        return serviceDict

    def buildNSinfo(self, servicedict):
        serviceDict = json.loads(servicedict)
        SvcDict = schema.service_dict
        vduList = []
        nsDict = schema.ns_dict
        vnfDict = {}
        for vnf in serviceDict['ns']['vnfds']:
            vnfDict[vnf] = {}
            if isinstance(serviceDict['ns']['vnfds'][vnf]['item'], list):
                for vdu in range (0, len(serviceDict['ns']['vnfds'][vnf]['item'])):
                    vduInfo = self._getVDUspecs(serviceDict['ns']['vnfds'][vnf]['item'][vdu])
                    vnfDict[vnf].update(vduInfo)
            else:
                vduInfo = self._getVDUspecs(serviceDict['ns']['vnfds'][vnf]['item'])
                vnfDict[vnf].update(vduInfo)
        for nsSpec in serviceDict['ns']:
            if nsSpec in nsDict.keys():
                nsDict[nsSpec] = serviceDict['ns'][nsSpec]
        ns_info = copy.deepcopy(nsDict)
        for key in SvcDict.keys():
            if key == "vdus":
                SvcDict['vdus'] = vnfDict
            else:
                SvcDict['nsd'] = ns_info
        SvcDict['id'] = serviceDict['ns']['nsd-id']
        SvcInfo = copy.deepcopy(SvcDict)
        return SvcInfo

    def _getVDUspecs(self, vdudata):
        vduSchema = schema.vdu
        ntwSchema = schema.network
        instanceList = []
        vduDict = {}
        if isinstance(vdudata['instance_list']['item'], list):
            instance_list = vdudata['instance_list']['item']
        else:
            instance_list = [vdudata['instance_list']['item']]
        vduname  = vdudata['name']
        for instance in instance_list:
            instanceDict = {}
            ntwList = []
            for vdu_spec in vdudata.keys():
                if vdu_spec in vduSchema.keys():
                    if vdu_spec == 'mgmt-ip':
                        if vdudata[vdu_spec]:
                            vduSchema[vdu_spec] = vdudata[vdu_spec][instance]
                        else:
                            vduSchema[vdu_spec] = None
                    else:
                        vduSchema[vdu_spec] = vdudata[vdu_spec]
                if vdu_spec == "vm-spec":
                    for vmSpec in vdudata[vdu_spec].keys():
                        if vmSpec in vduSchema.keys():
                            if vmSpec == "network-interfaces":
                                for ntw in vdudata[vdu_spec][vmSpec].keys():
                                    ntw_info = {}
                                    for ntw_spec in vdudata[vdu_spec][vmSpec][ntw].keys():
                                        if ntw_spec in ntwSchema.keys():
                                            if ntw_spec == "ips":
                                                ntwSchema.update({ntw_spec: vdudata[vdu_spec][vmSpec][ntw][ntw_spec][instance]})
                                            else:
                                                ntwSchema.update({ntw_spec: vdudata[vdu_spec][vmSpec][ntw][ntw_spec]})
                                    ntw_info[ntw] = copy.deepcopy(ntwSchema)
                                    ntwList.append(ntw_info)
                                vduSchema[vmSpec] = ntwList
                            else:
                                vduSchema[vmSpec] = vdudata[vdu_spec][vmSpec]
                        elif vmSpec == "image_details":
                            for imgSpec in vdudata[vdu_spec][vmSpec].keys():
                                if imgSpec in vduSchema.keys():
                                    vduSchema[imgSpec] = vdudata[vdu_spec][vmSpec][imgSpec]
            instInfo = copy.deepcopy(vduSchema)
            instInfo['name'] = instance
            #instanceDict[instance] = instInfo
            instanceDict = instInfo
            instanceList.append(instanceDict)
        vduDict[vduname] = instanceList
        return vduDict

    def getServiceInfo(self, nsID):
        return self.nsInfo[nsID]

    def enableDiagnostics(self, **kwargs):
	'''
	Extract NS and VNF details from service object
		File To be capture
		Netwrok interfaces
	And given as input to VNFSVC API
	'''


        self.diagnostics.__enable_diagnostics__(**kwargs)

	'''service_obj = kwargs['service']
	self.protocols_data = kwargs['protocol']
	data = kwargs['VNF']
        self.diagnostics_data = dict()


        #Extract network service id
        self.diagnostics_data['nsd_id'] = service_obj['id']
        self.diagnostics_data['files'] = dict()
        self.taas_data = dict()
        self.file_capture = dict()

        for req_vnf_list in data:
                #self.diagnostics_data['vdus'].extend([req_vnf_list['vdu']]);
                vnfd = service_obj['vdus'].keys()[0]
                if req_vnf_list['vdu'] in service_obj['vdus'][vnfd].keys():
                   self.diagnostics_data['files'][service_obj['vdus'][vnfd][req_vnf_list['vdu']][0]['id']] = req_vnf_list['file']
                else:
                   raise ValueError('No such VDU found')
                self.taas_data[req_vnf_list['vdu']] = req_vnf_list['iface']
		self.file_capture[req_vnf_list['vdu']] = req_vnf_list['iface'] 

	#self.enable_taas()'''


    def enable_taas(self):

        #Extract the ports for the requested VDU network ifaces
	ntwInterfaces = []
        diagsDict = dict()
        for vdu in self.taas_data.keys():
            vduInfo = utils.getVdu(self.nsInfo, vdu)
            if vduInfo:
                utils.getVduParameter(vduInfo[0], self.taas_data[vdu]).update({"name": vdu})
                ntwIF = utils.getVduParameter(vduInfo[0], self.taas_data[vdu])
                ntwInterfaces.append(ntwIF)
                diagsDict[ntwIF['ips']] = {"name": vdu, "interface": self.taas_data[vdu]}

        portsList = []
        for interface in ntwInterfaces:
            portID = self._get_port_ID(interface)
            portsList.append(portID)

        #Create tap service on DPDK in-port        
        tapServiceParams = {
                 "tap_service": {
                     "description": "Tap service for diagnostic",
                     "name": "Diagnostics",
                     "network_id": "b5878681-83eb-44a3-84c2-169934bd879c",
                     "port_id": "948448ed-337e-4789-81e3-7da2a6cc2217",
                 } 
        }
        tapSvcData = self.API.__create_tap_service__(tapServiceParams)  
        self.tapServiceID = tapSvcData['tap_service']['id']
        print tapSvcData

        #Create tap flows for all the requested vdu network interfaces
        for port in portsList:
            tapFlowParams = {
                     "tap_flow": {
                         "description": "Test_flow1",
                         "direction": "BOTH",
                         "name": "flow"+port[:8],
                         "source_port": port,
                         "tap_service_id": tapSvcData['tap_service']['id'],
                          }
                     }      
            tapFlowData = self.API.__create_tap_flow__(tapFlowParams)        
            print tapFlowData
            self.tapFlows.append(tapFlowData['tap_flow']['id'])

        startAnalyser = requests.get("http://60.0.0.11:9999/startDPI") 

    def _get_port_ID(self, ntwIF):
        port_list =  self.API.__list_ports__()
        for port in port_list['ports']:
            if port["network_id"] == ntwIF['net-id']:
                for fxd_ip in port["fixed_ips"]:
                    if fxd_ip["ip_address"] ==  ntwIF['ips']:
                        return port['id']

    def startDiagnostics(self):
   
       # Sniffing packets on eth2 interface of concerto
    
       #self.sniffPkt = packetsniffer.packetsniffer(diagsDict)
       data = dict()
       data['nsd_id'] = self.diagnostics_data['nsd_id']
       data['files'] = self.diagnostics_data['files']
       import pdb;pdb.set_trace()
       svcDetails = self.API.__start_diagnostics__(**data)
       self.sniffPkt = packetsniffer.packetsniffer({})
       self.sniffPkt.start()
  
    def Stopdiagnostics(self):
        self.sniffPkt.stop()

    def stopDiagnostics(self):
        if self.tapFlows:
            for flow in self.tapFlows:
                self.API.__delete_tap_flow__(flow)
        if self.tapServiceID:
            self.API.__delete_tap_service__(self.tapServiceID)

    def deleteEventServer(self):
        shutdown_uri = "http://"+socket.gethostbyname(self.eventHost)+":"+str(self.eventPort)+"/shutdown"
        r = requests.post(shutdown_uri)

    def vyatta_report(self, **kwargs):
        utils.pdf.table(kwargs)

    def cleanup(self):
        utils.pdf.create_pdf(self.title, self.productDir,self.sessionDir)
        #self.stopDiagnostics()
        for networkService in self.nsInfo.keys():
            self.deleteService(networkService)
        for template in self.serviceInfo.keys():
            self.deleteTemplate(template)

    def set_report_title(self, title="Report"):
        self.title = title
