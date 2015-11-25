import time
class CpuUtilization(object):
    def __init__(self):
        super(CpuUtilization, self).__init__()

    def compute(self, stats):
        return sum(a['cpu_util'] for a in stats.values())

class NetworkIncomingBytes(object):
    def __init__(self):
        super(NetworkIncomingBytes, self).__init__()
        self.meter = {}
        self.ts_curr = 0.0
        self.ts_prev = float(time.time())
        self.meter[self.ts_prev] = 0.0
        self.sum_nw_bytes = 0.0

    def compute(self, stats):
        for values in stats.values():
            for iface in values['network.incoming.bytes'].keys():
                self.sum_nw_bytes = self.sum_nw_bytes + values['network.incoming.bytes'][iface]

        self.ts_curr = float(time.time())
        ts_diff = self.ts_curr - self.ts_prev
        diff_nw_bytes = self.sum_nw_bytes - self.meter[self.ts_prev]
        byte_rate = diff_nw_bytes/float(ts_diff)
        kbps = int(byte_rate/1000000)
        self.ts_prev = self.ts_curr
        self.meter[self.ts_prev] = self.sum_nw_bytes
        return str(kbps) + " Mbps"
