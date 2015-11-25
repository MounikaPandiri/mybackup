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

from heat.engine import clients
from heat.engine import constraints
from heat.engine import properties
from heat.engine.resources.neutron import neutron
from heat.openstack.common import log as logging

if clients.neutronclient is not None:
    from neutronclient.common.exceptions import NeutronClientException

logger = logging.getLogger(__name__)

class SecurityHigh(neutron.NeutronResource):
    """
    A resource for the FirewallRule resource in Neutron FWaaS.
    """
    
    props={}
    firewall_ids={}
    firewall_rule_list=[]
    firewall_rule_ids = {}
    firewall_rules={}

    PROPERTIES = (
        NAME, DESCRIPTION, ADMIN_STATE_UP, FIREWALL_POLICY_ID,
         SHARED, AUDITED, FIREWALL_RULES, PROTOCOL, IP_VERSION,
        SOURCE_IP_ADDRESS, DESTINATION_IP_ADDRESS, SOURCE_PORT,
        DESTINATION_PORT, ACTION, ENABLED, SPROP1, SPROP2, SPROP3, SPROP4,
    ) = (
        'name', 'description', 'admin_state_up', 'firewall_policy_id',
        'shared', 'audited', 'firewall_rules', 'protocol', 'ip_version',
        'source_ip_address', 'destination_ip_address', 'source_port',
        'destination_port', 'action', 'enabled', 'sprop1', 'sprop2', 'sprop3', 'sprop4',
    )

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Name for the firewall.'),
            update_allowed=True
        ),
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('Description for the firewall.'),
            update_allowed=True
        ),
        ADMIN_STATE_UP: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Administrative state of the firewall. If false (down), '
              'firewall does not forward packets and will drop all '
              'traffic to/from VMs behind the firewall.'),
            default=True,
            update_allowed=True
        ),
        FIREWALL_POLICY_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the firewall policy that this firewall is '
              'associated with.'),
            #required=True,
            update_allowed=True
        ),
        SHARED: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether this policy should be shared across all tenants.'),
            default=False,
            update_allowed=True
        ),
        AUDITED: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether this policy should be audited. When set to True, '
              'each time the firewall policy or the associated firewall '
              'rules are changed, this attribute will be set to False and '
              'will have to be explicitly set to True through an update '
              'operation.'),
            default=False,
            update_allowed=True
        ),
        FIREWALL_RULES: properties.Schema(
            properties.Schema.LIST,
            _('An ordered list of firewall rules to apply to the firewall.'),
            #required=True,
            update_allowed=True
        ),
        PROTOCOL: properties.Schema(
            properties.Schema.STRING,
            _('Protocol for the firewall rule.'),
            constraints=[
                constraints.AllowedValues(['tcp', 'udp', 'icmp', None]),
            ],
            update_allowed=True
        ),
        IP_VERSION: properties.Schema(
            properties.Schema.STRING,
            _('Internet protocol version.'),
            default='4',
            constraints=[
                constraints.AllowedValues(['4', '6']),
            ],
            update_allowed=True
        ),
        SOURCE_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('Source IP address or CIDR.'),
            update_allowed=True
        ),
        DESTINATION_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('Destination IP address or CIDR.'),
            update_allowed=True
        ),
        SOURCE_PORT: properties.Schema(
            properties.Schema.STRING,
            _('Source port number or a range.'),
            update_allowed=True
        ),
        DESTINATION_PORT: properties.Schema(
            properties.Schema.STRING,
            _('Destination port number or a range.'),
            update_allowed=True
        ),
        ACTION: properties.Schema(
            properties.Schema.STRING,
            _('Action to be performed on the traffic matching the rule.'),
            default='deny',
            constraints=[
                constraints.AllowedValues(['allow', 'deny']),
            ],
            update_allowed=True
        ),
        ENABLED: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether this rule should be enabled.'),
            default=True,
            update_allowed=True
        ),
        SPROP1: properties.Schema(
            properties.Schema.STRING,
            _('Whether this security property should be enabled.'),
            constraints=[
                constraints.AllowedValues(['required','not_required'])
                ],
            default='required',
            update_allowed=True
        ),
        SPROP2: properties.Schema(
            properties.Schema.STRING,
            _('Whether this security property should be enabled.'),
            constraints=[
                constraints.AllowedValues(['required','not_required'])
            ],
            default='required',
            update_allowed=True
        ),
        SPROP3: properties.Schema(
            properties.Schema.STRING,
            _('Whether this security property should be enabled.'),
            constraints=[
                constraints.AllowedValues(['required','not_required'])
            ],
            default='required',
            update_allowed=True
        ),
        SPROP4: properties.Schema(
            properties.Schema.STRING,
            _('Whether this security property should be enabled.'),
            constraints=[
                constraints.AllowedValues(['required','not_required'])
            ],
            default='not_required',
            update_allowed=True
        ),

    

    }

    attributes_schema = {
        'name': _('Name for the firewall.'),
        'description': _('Description of the firewall.'),
        'admin_state_up': _('The administrative state of the firewall.'),
        'firewall_policy_id': _('Unique identifier of the firewall policy '
                                'used to create the firewall.'),
        'status': _('The status of the firewall.'),
        'tenant_id': _('Id of the tenant owning the firewall.'),
        'show': _('All attributes.'),
        'firewall_rules': _('List of firewall rules in this firewall policy.'),
        'shared': _('Shared status of this firewall policy.'),
        'audited': _('Audit status of this firewall policy.'),
        'protocol': _('Protocol value for this firewall rule.'),
        'ip_version': _('Ip_version for this firewall rule.'),
        'source_ip_address': _('Source ip_address for this firewall rule.'),
        'destination_ip_address': _('Destination ip_address for this '
                                    'firewall rule.'),
        'source_port': _('Source port range for this firewall rule.'),
        'destination_port': _('Destination port range for this firewall '
                              'rule.'),
        'action': _('Allow or deny action for this firewall rule.'),
        'enabled': _('Indicates whether this firewall rule is enabled or '
                     'not.'),
        'sprop1': _('allows property1'),
        'sprop2': _('allows property1'),
        'sprop3': _('allows property1'),
        'sprop4': _('allows property1'),
        'position': _('Position of the rule within the firewall policy.')


    }

    update_allowed_keys = ('Properties',)


    def _show_resource(self):
        return self.neutron().show_firewall_rule(
            self.resource_id)['firewall_rule']

    def handle_create(self):
        self.firewall_rule_list=[]
        rule = 0
        self.props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())
    
        if self.props['sprop4']=='required':
            rule = rule + 1
            self._create_firewall_rule('all',rule,'deny')
        else:
            if self.props['sprop1']=='required':
                rule = rule + 1
                self._create_firewall_rule('tcp',rule,'deny')
            if self.props['sprop2']=='required':
                rule = rule + 1
                self._create_firewall_rule('udp',rule,'deny')
            if self.props['sprop3']=='required':
                rule = rule + 1
                self._create_firewall_rule('icmp',rule,'allow')

        ############################################################
        subnets_list=self.neutron().list_subnets()['subnets']
        flag1=0
        for subnet in subnets_list:
            if self.props['source_ip_address']==subnet['cidr']:
                source_subnet_id=subnet['id']
                flag1=1
                break

        if flag1==0:
            network1= self.neutron().create_network(
                {'network': {'name' : self.props['name'] + '_snet','admin_state_up' : self.props['admin_state_up'] ,'shared' : self.props['shared']}})['network']

            self.resource_id_set(network1['id'])
            subnet1= self.neutron().create_subnet(
                {'subnet': {'name' : self.props['name'] + '_ssnet','network_id' : network1['id'],'ip_version' : self.props['ip_version'],'cidr' : self.props['source_ip_address']}})['subnet']
            self.resource_id_set(subnet1['id'])                     

        flag2=0
        for subnet in subnets_list:
            if self.props['destination_ip_address']==subnet['cidr']:
                destination_subnet_id=subnet['id']
                flag2=1
                break

        if flag2==0:
            network2=self.neutron().create_network(
                {'network': {'name' : self.props['name'] + '_dnet','admin_state_up' : self.props['admin_state_up'] ,'shared' : self.props['shared']}})['network']
            self.resource_id_set(network2['id'])
            subnet2= self.neutron().create_subnet(
                {'subnet': {'name' : self.props['name'] + '_dsnet','network_id' : network2['id'],'ip_version' : self.props['ip_version'],'cidr' : self.props['destination_ip_address']}})['subnet']                        
            self.resource_id_set(subnet2['id'])
        ############################################################
        self.firewall_ids['firewall_rule_id'] = self.firewall_rule_ids
        if rule>0:
            policy_id = self._create_firewall_policy()
            self._create_firewall(policy_id)

    def _create_firewall_rule(self,protocol,rule,action):
        firewall_rule_props = {}
        firewall_rule = {}
        firewall_rule_props['protocol']= protocol
        firewall_rule_props['action']= action 
        firewall_rule_props['name']=self.props['name'] + '_rule'
        firewall_rule_props['enabled']=self.props['enabled']
        firewall_rule_props['ip_version']=self.props['ip_version']
        firewall_rule_props['shared']=self.props['shared']
        firewall_rule_props['source_ip_address']=self.props['source_ip_address']
        firewall_rule_props['destination_ip_address']=self.props['destination_ip_address']
        firewall_rule = self.neutron().create_firewall_rule(
             {'firewall_rule': firewall_rule_props})['firewall_rule']
        self.resource_id_set(firewall_rule['id'])
        self.firewall_rule_ids[rule]=firewall_rule['id']
        self.firewall_rule_list.append(firewall_rule['id'])

    def _create_firewall_policy(self):
        firewall_policy_props = {}
        firewall_policy = {}
        firewall_policy_props['shared']=self.props['shared']
        firewall_policy_props['audited']=self.props['audited']
        firewall_policy_props['firewall_rules']=self.firewall_rule_list
        firewall_policy_props['name']=self.props['name'] + '_policy'
        firewall_policy = self.neutron().create_firewall_policy(
            {'firewall_policy': firewall_policy_props})['firewall_policy']
        self.resource_id_set(firewall_policy['id'])
        self.firewall_ids['firewall_policy_id'] = firewall_policy['id']
        return firewall_policy['id']

    def _create_firewall(self,policy_id):
        firewall_properties = {}
        firewall_new = {}
        firewall_properties['admin_state_up']=self.props['admin_state_up']
        firewall_properties['firewall_policy_id']=policy_id
        firewall_properties['name']=self.props['name']
        firewall_new = self.neutron().create_firewall(
            {'firewall': firewall_properties})['firewall']
        self.resource_id_set(firewall_new['id'])
        self.firewall_ids['firewall_id'] =firewall_new['id']

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.neutron().update_firewall_rule(
                self.resource_id, {'firewall_rule': prop_diff})

    def handle_delete(self):
        
        self.firewall_rules = self.firewall_ids['firewall_rule_id']
        
        client = self.neutron()
        try:
            client.delete_firewall(self.firewall_ids['firewall_id'])
            client.delete_firewall_policy(self.firewall_ids['firewall_policy_id'])
            for rules in self.firewall_rules:
               client.delete_firewall_rule(self.firewall_rules[rules])
        except NeutronClientException as ex:
            self._handle_not_found_exception(ex)
        else:
            return self._delete_task()

def resource_mapping():
    if clients.neutronclient is None:
        return {}

    return {
        'OS::Neutron::SecurityHigh': SecurityHigh,
    }
