from common import config, utils, API, openstack, schema
import packetsniffer
class Diagnostics():

    def __init__(self, execore):
        self.API = execore.API
	self.vnfsvcClient = execore.API.vnfsvc
        self.neutronClient = execore.API.neutronClient
        self.novaClient = execore.API.novaClient
        self.diagnostics_data = {}
        self.taas_data = {}
        self.protocols = []
        self.tapServices = []
        self.tapFlows = []
        self.sniffPkt = None


    def __enable_diagnostics__(self, **kwargs):

        self.protocols.extend(kwargs['protocol'])
        data = kwargs['VNF']
        service_obj = kwargs['service']

        #Extract network service id
        ns_id = service_obj['id']
        self.diagnostics_data[ns_id] = {'nsd_id' : service_obj['id']}
        self.diagnostics_data[ns_id]['files'] = dict()
        self.taas_data[ns_id] = dict()

        for req_vnf_list in data:
            vnfd = service_obj['vdus'].keys()[0]
	    if req_vnf_list['vdu'] in service_obj['vdus'][vnfd].keys():
		    self.diagnostics_data[ns_id]['files'] = \
                             { service_obj['vdus'][vnfd][req_vnf_list['vdu']][0]['id'] : req_vnf_list['file']}
            else:
                raise ValueError('No such VDU found')

            self.taas_data[ns_id][req_vnf_list['vdu']] = req_vnf_list['iface']

        self._enable_taas(service_obj)
        self._enable_dpdk()


    def _enable_taas(self, service):

        #Extract the ports for the requested VDU network ifaces
        ntwInterfaces = []
        #self.diagsDict = {}
        for ns in self.taas_data.keys():
            if ns == service['id']:
                for vdu in self.taas_data[ns].keys():
                    vduInfo = utils.getVdu(service, vdu)
                    if vduInfo:
                        utils.getVduParameter(vduInfo[0], self.taas_data[ns][vdu]).update({"name": vdu})
                        ntwIF = utils.getVduParameter(vduInfo[0], self.taas_data[ns][vdu])
                        ntwInterfaces.append(ntwIF)

        portsList = []
        for interface in ntwInterfaces:
            portID = self._get_port_ID(interface)
            portsList.append(portID)

        #Create tap service on DPDK in-port        
        tapServiceParams = {
                 "tap_service": {
                     "description": "Tap service for diagnostic",
                     "name": "Diagnostics",
                     "network_id": "f3200048-6c40-470e-86ec-239100d58d11",
                     "port_id": "34ec955d-4f11-47e2-893a-dcd957cbed22",
                 }
        }
        tapSvcData = self.API.__create_tap_service__(tapServiceParams)
        self.tapServices.append(tapSvcData['tap_service']['id'])
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



    def _get_port_ID(self, ntwIF):
        port_list =  self.API.__list_ports__()
        for port in port_list['ports']:
            if port["network_id"] == ntwIF['net-id']:
                for fxd_ip in port["fixed_ips"]:
                    if fxd_ip["ip_address"] ==  ntwIF['ips']:
                        return port['id']


    def __disable_diagnostics__(self):
        self._disable_taas()
        self._disable_dpdk()


    def startDiagnostics(self, tcase_dir):
       self._enable_file_capture()
       self._enable_pkt_capture(tcase_dir)


    def stopDiagnostics(self):
       self._enable_file_capture()
       self._disable_pkt_capture()


    def _enable_file_capture(self):
       for service in self.diagnostics_data.keys():
           import pdb;pdb.set_trace()
           data['nsd_id'] = self.diagnostics_data[service]['nsd_id']
           data['files'] = self.diagnostics_data[service]['files']
           svcDetails = self.API.__start_diagnostics__(**data)


    def _enable_pkt_capture(self):
       self.sniffPkt = packetsniffer.packetsniffer(self.protocols, tcase_dir)
       self.sniffPkt.start()


    def _disable_pkt_capture(self):
        if self.sniffPkt.is_alive():
            self.sniffPkt.terminate()


    def _disable_taas(self):
        if self.tapFlows:
            for flow in self.tapFlows:
                self.API.__delete_tap_flow__(flow)
        if self.tapServices:
            for tapService in self.tapServices:
                self.API.__delete_tap_service__(tapService)


    def _enable_dpdk(self):
        startAnalyser = requests.get("http://60.0.0.4:9999/startDPI")


    def _disable_dpdk(self):
        pass
        
