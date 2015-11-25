"""Storage backend management
"""
import datetime
from oslo_config import cfg
from oslo_db import options as db_options
import six
import six.moves.urllib.parse as urlparse
from stevedore import driver

import vnfsvc
from vnfsvc.openstack.common import importutils
from vnfsvc.openstack.common.gettextutils import _
from vnfsvc.openstack.common import log
from vnfsvc.db.monitoring.mongo import utils as pymongo_utils

LOG = log.getLogger(__name__)
db_options.set_defaults(cfg.CONF)
cfg.CONF.import_opt('connection', 'oslo_db.options', group='database')

def get_connection(url):
    """Return an open connection to the database."""
    connection_scheme = urlparse.urlparse(url).scheme
    engine_name = connection_scheme.split('+')[0]

    # TODO(tcs): stevedore not used as vnfsvc doesn't support entry points.
    #                Can think of another way as dumping an object of 
    #                driver is not always preferable garabage collection would 
    #                cause issues.

    mongo_db_drv = importutils.import_object('vnfsvc.db.monitoring.monitoring_db.Connection', url)
    return mongo_db_drv

class MetricFilter(object):
    """Holds the properties for building a query from a meter/sample filter.

    :param start: Earliest time point in the request.
    :param start_timestamp_op: Earliest timestamp operation in the request.
    :param end: Latest time point in the request.
    :param end_timestamp_op: Latest timestamp operation in the request.
    :param resource: Optional filter for resource id.
    """
    def __init__(self, start=None, start_timestamp_op=None,
                 end=None, end_timestamp_op=None,
                 resource=None):
        self.start = pymongo_utils.sanitize_timestamp(start)
        self.start_timestamp_op = start_timestamp_op
        self.end = pymongo_utils.sanitize_timestamp(end)
        self.end_timestamp_op = end_timestamp_op
        self.resource = resource
