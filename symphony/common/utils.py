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
import os,sys
cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
import yaml
from collections import OrderedDict
import subprocess
import paramiko
from collections import deque
import threading
import xmltodict
import schema
import logging.config
import report
from report import report_generator

logger = logging.getLogger(__name__)

comm_queue=deque()
eventNotification = threading.Condition()
pdf = report_generator.PDFInstance()

#This class incorporates static utility functions

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def exec_command(command, client=None, **kwargs):
    """Executes the given command and return the status."""
    try:
        if client:
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read()
            err = stderr.read()
            if len(err) > 0:
                logger.debug(err)
                # sys.exit(0)
            else:
                return (output, err)
        else:
            process = subprocess.Popen(command.split(),
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, 
                                      **kwargs)
            output, err = process.communicate()
            if err:
                logger.debug(err)
            else:
                return (output, err)
    except:
        logger.warn("Unable to execute the given command, Returning as Failed")
        pass


def get_ssh_conn(host, username, password):
    """ Returns an ssh client"""
    retry = 10
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, 22, username, password)
        return client
    except paramiko.ssh_exception.AuthenticationException:
        logger.error("Invalid credentials")
    except paramiko.SSHException:
        logger.error("Unable to establish the connection")
    except:
        logger.debug("Failed to establis SSH Connectivity")
        while (retry > 0):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())
                client.connect(host, 22, username, password)
                if isinstance(client, paramiko.SSHClient):
                    retry = retry - 1
                    break
            except:
                retry = retry - 1
                logger.debug("Unable to establish connection, Retrying to establish.")
        if isinstance(client, paramiko.SSHClient):
            return client
        else:
            logger.warn("Failed to establish connection")

def loadTrafficGenerator(productPath,testModuleName):
	"""Load the requested test module"""
	testModulePath = os.path.join(productPath,'core/tstcore')
        sys.path.append(testModulePath)
        #remove the file name at the end and append to sys.path
        return __import__(testModuleName,globals(), locals(), [], -1)

def getVduParameter(vduinstance, parameter):
    for key in vduinstance.keys():
        if parameter == key:
            return vduinstance[parameter]
        else:
            if isinstance(vduinstance[key], list):
                for param in range(0, len(vduinstance[key])):
                    if isinstance(vduinstance[key][param], dict):
                        for param_key in vduinstance[key][param].keys():
                            if param_key == parameter:
                                if key == 'network-interfaces':
                                    #return vduinstance[key][param][param_key]['ips']
                                    return vduinstance[key][param][param_key]

def getVdu(nsDict, vdu):
    import pdb;pdb.set_trace()
    for vnf in nsDict['vdus']:
        if vdu in nsDict['vdus'][vnf].keys():
            return nsDict['vdus'][vnf][vdu]
        else:
            return None

class Utils(object):

	@staticmethod
	def helpText():
		return 'symphony --config-file [ config file path] --script [test script path]'
		
	@staticmethod
	def touch(fname):
		if os.path.exists(fname):
			os.utime(fname, None)
		else:
			open(fname, 'a').close()

	@staticmethod
	def loadAvailableTestServices() :
		"""Fetch available test modules in test Core"""
		temp = ('tvm','ixia','spirent','sipp')
		return temp
