# Copyright 2014,Tata Consultancy Services Ltd.
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

"""
Routines for configuring Symphony
"""

import os
import sys

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
from oslo_config import cfg
from common import version
#from vnfsvc.api.v2 import attributes
#from vnfsvc.common import utils
#from vnfsvc.openstack.common import log as logging
#from vnfsvc import version
#from vnfsvc.common import rpc as n_rpc
#from vnfsvc.openstack.common.gettextutils import _

#LOG = logging.getLogger(__name__)

core_opts = [
    cfg.StrOpt('testID', default='None',
               help=("Identifier for the test case being executed")),
    cfg.StrOpt('module', default='None',
               help=("The test module that should be loaded for execution in this session")),
    cfg.StrOpt('script', default='all',
                help=("Test Script that should be executed from the test module")),
    cfg.StrOpt('vim', default='None',
                help=("Virtual infrastructure manager to be used")),
    cfg.StrOpt('api_version',default='v0.1',
		help=("API version to be used"))

    #cfg.BoolOpt('nova_api_insecure', default=False,
    #            help=_("If True, ignore any SSL validation issues")),
    #cfg.IntOpt('send_events_interval', default=2,
    #           help=_('Number of seconds between sending events to nova if '
    #                  'there are any events to send.')),
]

#
#Register CLI options
cli_options = [
#                cfg.StrOpt('config-file',
#                            default='None',
#                            help='Path for the cofiguration file for execution'),
                cfg.StrOpt('test-script',
                            default='None',
                            help='Path for the test script for execution')
]


#Register openstack group to parse those arguments
openstack_group = cfg.OptGroup(name='openstack',
                                title='Openstack options')

openstack_host  = cfg.StrOpt('host',
                              default='localhost',
                              help='IP/hostname to listen on.')

openstack_port  = cfg.IntOpt('port',
                                 default=5672,
                                 help='Port number to listen on.')

openstack_authURL = cfg.StrOpt('auth_url',
                                default='http://localhost:5000/v2.0',
                                 help='Openstack Auth URL')

openstack_userID  = cfg.StrOpt('user_id',
                               default=None,
                               help='Openstack credentials')

openstack_password = cfg.StrOpt('password',
                                 default=None,
                                 help='Credentials to connect to Openstack.')

openstack_tenant = cfg.StrOpt('tenant',
                               default=None,
                               help='Credentials to connect to Openstack.')



def register_openstack_options(conf):
    conf.CONF.register_group(openstack_group)
    # options can be registered under a group in either of these ways:
    conf.CONF.register_opt(openstack_host, group=openstack_group)
    conf.CONF.register_opt(openstack_port, group=openstack_group)
    conf.CONF.register_opt(openstack_authURL, group=openstack_group)
    conf.CONF.register_opt(openstack_userID, group=openstack_group)
    conf.CONF.register_opt(openstack_password, group=openstack_group)
    conf.CONF.register_opt(openstack_tenant, group=openstack_group)


# Register the configuration options
cfg.CONF.register_opts(core_opts)
register_openstack_options(cfg) #Register options listed under tag openstack
cfg.CONF.register_cli_opts(cli_options) #Register CLI options


def init(args, **kwargs):
    """Initialize the configuration parser as per the user inputs"""
    #We want to use only the values provided by the user
    #for now harcode the indices. TO-DO : Fetch them from the args later
    try :
      default_cfg = args[1]
    except:
      default_cfg = 'None'


    cfg.CONF(args=args,
              project='Symphony',
              prog='symphony',
              version=version.version_info.release_string(),
              usage=version.version_info.usage_info(),
              #default_config_files=version.version_info.default_config(),
              default_config_files=default_cfg,
              validate_default_values=False)
