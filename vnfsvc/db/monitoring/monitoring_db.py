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
"""MongoDB storage backend"""

import calendar
import copy
import datetime
import json
import operator
import uuid

import bson.code
import bson.objectid
from oslo_config import cfg
from oslo.utils import timeutils
import pymongo
import six

from vnfsvc.db.monitoring.mongo import utils as pymongo_utils
from vnfsvc.db.monitoring import pymongo_base

class Connection(pymongo_base.Connection):
    """Put the data into a MongoDB database

    Collections::

        - meter
          - Performance Metrics calculated by customised Driver for every Network Service.
          - Schema:
               {nsd_id: <nsd identifier>, kpi: <Perfoemance Metric>, 'timestamp': <timestamp>}
    """

    CONNECTION_POOL = pymongo_utils.ConnectionPool()

    def __init__(self, url):

        # NOTE(jd) Use our own connection pooling on top of the Pymongo one.
        # We need that otherwise we overflow the MongoDB instance with new
        # connection since we instanciate a Pymongo client each time someone
        # requires a new storage connection.
        self.conn = self.CONNECTION_POOL.connect(url)

        # Require MongoDB 2.4 to use $setOnInsert
        if self.conn.server_info()['versionArray'] < [2, 4]:
            raise storage.StorageBadVersion("Need at least MongoDB 2.4")

        connection_options = pymongo.uri_parser.parse_uri(url)
        self.db = getattr(self.conn, connection_options['database'])
        if connection_options.get('username'):
            self.db.authenticate(connection_options['username'],
                                 connection_options['password'])

        # NOTE(jd) Upgrading is just about creating index, so let's do this
        # on connection to be sure at least the TTL is correcly updated if
        # needed.
        #self.upgrade()

    def record_kpi_data(self, kpi_value, nsd_id, timestamp):
        """Write the data to the backend storage system.

        :param data: a dictionary such as returned by
                     ceilometer.meter.meter_message_from_counter
        """
        data = dict()
        data['kpi'] = kpi_value
        data['nsd_id'] = nsd_id
        data['timestamp'] = pymongo_utils.sanitize_timestamp(timestamp)
 
        self.db.nsdmetering.insert(data)

    def get_kpi_data(self, sample_filter, query=None):
        limit = None
        # TODO(tcs): Query Support still continued in DB,
        #	     eventough Neutron API doesnt support query,
        #            to keep the db code extendible. 

        # In future, if API would support Query parameter, there would
        # be no impact on DB code.

        try:
          if query is None:
              return [m for m in self.get_samples(sample_filter, limit=limit)]
        except KeyError:
              raise
