
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
import sys,os

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
from common import utils
class VersionInfo(object):
    release = "symphony"
    version = "2015.0.1"

    def version_string(self):
        return self.version

    def release_string(self):
        return self.release

    def usage_info(self):
    	return utils.Utils.helpText()

    def default_config(self):
    	return 'None'

version_info = VersionInfo()
