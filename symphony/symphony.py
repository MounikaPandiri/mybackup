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
import sys,getopt,socket
from collections import deque
from common import utils
from oslo_config import cfg
#from import_utils import import_module_from, import_module
from common import config
from core import executionCore,eventListner
from core.eventListner import EventListner

def main(argv):
    # the configuration will be read into the cfg.CONF global data structure
    config.init(sys.argv[1:])
    cfgFile = 'None'
    testScript = 'None'
    #Parse command line arguments
    try:
        opts,args = getopt.getopt(argv,"hc:s:",["config-file=","test-script="])

    except getopt.GetoptError:
        print utils.Utils.helpText()
        raise
    for opt, arg in opts:
        if opt == '-h':
            print utils.helpText()
            sys.exit()
        elif opt in ("-c", "--config-file"):
            cfgFile = arg

        elif opt in ("-s", "--test-script"):
            testScript = arg
        else :
            print utils.Utils.helpText()
            raise

    try:
        if cfgFile is 'None':
            print utils.Utils.helpText()
            sys.exit(("FATAL : Unable to proceed without configuration file"))

        elif testScript is 'None':
            print utils.Utils.helpText()
            sys.exit(_("FATAL : Unable to proceed without test script"))            

    	elif not cfg.CONF.config_file:
            sys.exit(_("FATAL : Unable to load the configuration"
                   "Please rerun with --help option"))

        #validate the input arguments
    	#logger = Log #TO-DO: Park for now.. will work on this later

	try:
		host = 'localhost' #cfg.CONF.host
	except Exception:
		host = 'localhost'

	#get a free port number to start the flask server
        try :
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((host, 0))
                port = sock.getsockname()[1]
                sock.close()
        except :
                pass

    	threadExeCore = executionCore.ExecutionCore(cfg,cfgFile,testScript,host,port,utils.comm_queue)
	threadExeCore.start()
	
	objEvent = eventListner.EventListner(host,port,utils.comm_queue,threadExeCore.sessionDir)
    	objEvent.run()

    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        sys.exit(_("ERROR: %s") % e)


if __name__ == "__main__":
    main(sys.argv[1:])

