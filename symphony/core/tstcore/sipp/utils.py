import time
import os
from ConfigParser import SafeConfigParser
from common import utils
from common import schema


def _get_sipp_config():
    config = {}
    #Get the sipp configuration details from config.ini
    config_parser = SafeConfigParser()
    try:
        config_file = os.path.dirname(os.path.abspath(__file__)) + "/config.ini"
        config_parser.read(config_file)
    except IOError:
        logger.error("Unable to open the config file, No such file existed")
    config['remote_files_path']= config_parser.get(
                                 'sipp',
                                 'remote_files_path')

    config['sipp_network'] = config_parser.get(
                            'sipp',
                            'sipp_network')

    config['mgmt_network'] = config_parser.get(
                             'sipp',
                             'mgmt_network')

    config['base_number'] = config_parser.get(
                            'sipp',
                            'base_number')

    config['sipp_router'] = config_parser.get(
                            'sipp',
                            'sipp_router')
    return config


#def _init_report():
#    report = {'report': {'ptext': {'ptext_data': "VoIP test result with Clearwater IMS"}}}
#    return report
 
#def _report(self, result, report):
def _report(result):
    report = {}
    users = list()
    call_rates =list()
    if type(result) is list and type(result[0]) is dict:
        report['report'] = {'table':{'table_data': {'header': ["Test Case", "Test type", "Status", "Successful","Failed","Call Rate","Users"]}}}
        report['report']['graph'] = {"graph_data" : {}}
        report['report']['table']['table_data']['data'] = []
        for key in result:
            report['report']['table']['table_data']['data'].append([key['name'], key['category'], key['status'], key['successful_calls'],key['failed_calls'],key['call_rate'],key['users']])
            users.append(key['users'])
            call_rates.append(float(key['call_rate']))
        report['report']['graph']['graph_data']['label'] = [tuple(users)]
        report['report']['graph']['graph_data']['data'] = [tuple(call_rates)]
        report['report']['graph']['graph_data']['legend'] = [tuple(["Successful Calls"])]
    else:
        report['report'] = {'table_append':{'table_data': {'header': ["Test Case", "Test type", "Status", "Successful","Failed","Call Rate"]}}}
        report['report']['table_append']['table_data']['data'] = [[result['name'], result['category'], result['status'], result['successful_calls'],result['failed_calls'],result['call_rate']]]
    return report
