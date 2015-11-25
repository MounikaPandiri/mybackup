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

import os
import os.path
import pexpect
import shutil
import simplejson as json
import subprocess
import tarfile
import tempfile
import uuid
import yaml

from distutils.dir_util import copy_tree
from oslo_config import cfg
from time import strftime

from vnfsvc.db.vnf import vnf_db

from vnfsvc.openstack.common import log as logging
from vnfsvc.openstack.common.gettextutils import _
from vnfsvc.client import client

LOG = logging.getLogger(__name__)

diagnostics_dict = dict()
class DiagnosticsManager(object):

    OPTS = [
        cfg.StrOpt(
            'state_path', default = '',
            help=_('Path to nsd directory')),
        cfg.StrOpt(
            'qemu_utils_path', default = '',
            help=_('Path to qemu_nbd.py')),
        cfg.StrOpt(
            'ansible_stop_path', default = '',
            help=_('Path to ansible stop script')), 
        #cfg.StrOpt(
        #    'ssh_pwd', default = '',
        #    help=_('SSH Passoword for host')),
       cfg.StrOpt(
            'mounting_script_path', default = '',
            help=_('Path to mounting script')),
       cfg.StrOpt(
            'file_script_path', default = '',
            help=_('Path to file script')),

        ]
    cfg.CONF.register_opts(OPTS, 'vnf')
    conf = cfg.CONF

    def __init__(self, context, nsd_id, instances, vdu_info):
        self.conf = cfg.CONF
        self.nsd_id = nsd_id
        #self.vdus = vdus
        self.vdu_info = vdu_info
        self.novaclient = self._get_nova_client(context)
        self.neutronclient = self._get_neutron_client(context)

    def enable_diagnostics(self):
        import pdb;pdb.set_trace()
        #self.start_diagnostics(vdu_id, instance_id, diagnostics_map)
        timestamp_path = self.start_mount_and_read()
        return timestamp_path
        
    def _get_nova_client(self, context):
        return client.NovaClient(context)

    def _get_neutron_client(self, context):
        return client.NeutronClient(context)

    def start_diagnostics(self, vdu_id, instance_id, diagnostics_map):
        import pdb;pdb.set_trace()
        global diagnostics_dict
        vdu_instance_info = self.novaclient.server_details(instance_id)
        instance_name = vdu_instance_info.name
        vdu_host = getattr(vdu_instance_info, 'OS-EXT-SRV-ATTR:host')
        host = self.novaclient.check_host(vdu_host)
        host_ip = getattr(host, 'host_ip')
        if vdu_id not in diagnostics_dict.keys():
           diagnostics_dict[vdu_id] = {}
        diagnostics_dict[vdu_id][instance_name] = dict()
        nsd_dir = os.path.join(self.conf.state_path, self.nsd_id)
        diagnostics_dict[vdu_id][instance_name]['host'] = host_ip
        diagnostics_dict[vdu_id][instance_name]['files_list'] = diagnostics_map['files_list']
        try:
            os.chdir(nsd_dir)
        except OSError:
            os.mkdir(nsd_dir)
        if not os.path.exists(os.path.join(nsd_dir, 'hosts')):
           with open(os.path.join(nsd_dir, 'hosts'), 'w') as hosts_file:
                 hosts_file.write("[%s]\n%s\n" % (vdu_host, host_ip))
        else:
           with open(os.path.join(nsd_dir, 'hosts'), 'a') as hosts_file:
                 hosts_file.write("[%s]\n%s\n" % (vdu_host, host_ip))
         

    def rebuild_dict(self, files_list=None):
        original_dict = diagnostics_dict
        new_dict = dict()
        for vdu in original_dict:
            for vdu_id in self.vdu_info:
                if vdu == vdu_id:
                   new_dict[self.vdu_info[vdu_id]] = original_dict[vdu]
        host_dict = dict()
        for vdu, vdu_dict in new_dict.iteritems():
            for instance, instance_dict in vdu_dict.iteritems():
                host = instance_dict['host']
                instance_id = self.novaclient.find_instance(str(instance)).id
                instance_dict['id'] = instance_id
                if host not in host_dict.keys():
                    host_dict[host] = dict()
                if vdu not in host_dict[host].keys():
                    host_dict[host][vdu] = dict()
                host_dict[host][vdu].update({instance:instance_dict})
        return host_dict

    def copy_files(self, archive_path, host_dict, timestamp_path):
        host_dict.pop('file_name')
         
        for vdu, vdu_dict  in host_dict.iteritems():
            if not os.path.exists(os.path.join(timestamp_path, vdu)):
                os.mkdir(os.path.join(timestamp_path, vdu))
                vdu_root = os.path.join(timestamp_path, vdu)
            for instance, instance_dict in vdu_dict.iteritems():
                try:
                    copy_tree(archive_path+'/'+vdu, vdu_root)
                except Exception as e:
                    print e
                    pass
        shutil.rmtree(archive_path)

    def start_mount_and_read(self):
        self.host_dict = self.rebuild_dict()
        state_path = self.conf.state_path
        nsd_path = os.path.join(state_path, self.nsd_id)
        if not os.path.exists(os.path.join(nsd_path, 'diagnostics')):
            os.mkdir(os.path.join(nsd_path, 'diagnostics'))
        timestamp = strftime("%Y%m%d-%H%M%S")
        diagnostics_path = os.path.join(nsd_path, 'diagnostics')
        os.mkdir(os.path.join(diagnostics_path, timestamp))
        timestamp_path = os.path.join(diagnostics_path, str(timestamp))
        for host, host_dict  in self.host_dict.iteritems():
            #write input.json file
            input_json = tempfile.mkstemp()[1]
            host_dict['file_name'] = str(uuid.uuid1())
            with open(input_json, 'w') as file_handler:
                json.dump(host_dict, file_handler, sort_keys=False, indent=4)
            os.chmod(input_json, 0644)
            host_file = tempfile.mkstemp()[1]
            with open(host_file, 'w') as file_handler:
                 file_handler.write('[server]\n'+host)
            os.chmod(host_file, 0644)

            mounting_script_path = self.conf.vnf.mounting_script_path
            dest_path = '/tmp/'+host_dict['file_name']+'.tar.gz'
            ansible_dict = [{'tasks':[
                             {'name': 'Copy mount file',
                              'copy': 'src='+mounting_script_path+' dest=/tmp/'+os.path.basename(mounting_script_path)},
                             {'name': 'Copy input file',
                              'copy': 'src='+input_json+' dest=/tmp/'+os.path.basename(input_json)},
                             {'name': 'Execute mounting script',
                              'command': 'sudo python /tmp/'+os.path.basename(mounting_script_path)+' /tmp/'+os.path.basename(input_json)+ ' >>/tmp/input.log'},
                             {'name': 'Fetch the tar file',
                              'fetch': 'src=/tmp/'+host_dict['file_name']+' dest='+dest_path}
                             ],
                             'hosts' : 'server',
                             'remote_user': self.conf.vnf.compute_user}]

            with open('/tmp/ansible_mount_playbook.yaml', 'w') as yamlfile:
                yamlfile.write(yaml.safe_dump(ansible_dict,
                    default_flow_style=False))


            child = pexpect.spawn('sudo ansible-playbook '+\
                                          '/tmp/ansible_mount_playbook.yaml -i '+\
                                           host_file+' --ask-pass',
                                           timeout=None)
            child.expect('SSH password:')
            child.sendline(self.conf.vnf.ssh_pwd)
            result = child.readlines()
            if not os.path.exists(dest_path):
                print "Unable to fetch the tar"
                raise Exception
            archive = tarfile.open(dest_path)
            os.chdir(nsd_path)
            try:
                archive.extractall()
                archive.close()
            except Exception as e:
                print e
                pass
            os.remove(dest_path)
            root_folder = nsd_path + '/tmp/' + os.listdir(nsd_path+'/tmp/')[0]
            self.copy_files(root_folder, host_dict, timestamp_path)
            try:
                shutil.rmtree(os.path.dirname(root_folder))
            except Exception as e:
                print e
                pass
            return timestamp_path

