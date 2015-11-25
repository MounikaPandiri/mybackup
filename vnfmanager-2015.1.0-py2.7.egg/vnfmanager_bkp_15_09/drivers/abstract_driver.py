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



import abc

import six

from vnfsvc.openstack.common import jsonutils


@six.add_metaclass(abc.ABCMeta)
class AbstractDriver(object):

    @abc.abstractmethod
    def pre_configure(self):
        pass

    @abc.abstractmethod
    def configure(self, **kwargs):
        pass

    @abc.abstractmethod
    def update(self, **kwargs):
        """Update the service."""
        pass

    @abc.abstractmethod
    def upgrade(self, **kwargs):
        """Upgrades the software."""
        pass




