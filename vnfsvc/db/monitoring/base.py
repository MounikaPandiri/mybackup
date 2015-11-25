# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Base classes for storage engines
"""

import datetime
import inspect
import math

import six
from six import moves

class Connection(object):
    """Base class for storage system connections."""

    # TODO(tcs): CAPABILITIES to be defined after finalisation of 
    #                the feature.
    """CAPABILITIES = {
        'meters': {'pagination': False,
                   'query': {'simple': False,
                             'metadata': False,
                             'complex': False}},
        'resources': {'pagination': False,
                      'query': {'simple': False,
                                'metadata': False,
                                'complex': False}},
        'samples': {'pagination': False,
                    'groupby': False,
                    'query': {'simple': False,
                              'metadata': False,
                              'complex': False}},
        'statistics': {'pagination': False,
                       'groupby': False,
                       'query': {'simple': False,
                                 'metadata': False,
                                 'complex': False},
                       'aggregation': {'standard': False,
                                       'selectable': {
                                           'max': False,
                                           'min': False,
                                           'sum': False,
                                           'avg': False,
                                           'count': False,
                                           'stddev': False,
                                           'cardinality': False}}
                       },
        'events': {'query': {'simple': False}},
    }"""

    STORAGE_CAPABILITIES = {
    }

    def __init__(self, url):
        """Constructor."""
        pass
