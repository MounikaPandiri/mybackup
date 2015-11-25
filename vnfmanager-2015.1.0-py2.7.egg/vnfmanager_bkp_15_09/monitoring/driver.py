class CpuUtilization(object):
    def __init__(self):
        super(CpuUtilization, self).__init__()

    def compute(self, stats):
        return sum(a['cpu_util'] for a in stats.values())

class NetworkIncomingBytes(object):
    def __init__(self):
        super(NetworkIncomingBytes, self).__init__()

    def compute(self, stats):
        sum_nw_bytes = 0.0
        for values in stats.values():
            for iface in values['network.incoming.bytes'].keys():
                sum_nw_bytes = sum_nw_bytes + values['network.incoming.bytes'][iface]
        return sum_nw_bytes
