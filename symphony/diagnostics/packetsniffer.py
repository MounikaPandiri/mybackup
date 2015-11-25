import threading
import pyshark
import subprocess
import os

from multiprocessing import Process

#class packetsniffer(threading.Thread):
class packetsniffer(Process):

    def __init__(self, diagsdict):
        super(packetsniffer,self).__init__()
        print 'Packet sniffer started'
        #threading.Thread.__init__(self)
        self.diags = diagsdict

    def run(self):
        output_file = "/home/tcs/ims.pcap"
        fo = open(output_file, "wb")
        fo.close()
        cap = pyshark.LiveCapture(interface="eth0", output_file=output_file)
        #cap = pyshark.LiveCapture(interface="eth2")
        for cp in cap.sniff_continuously():
            if cp.highest_layer == "SIP":
                print cp.pretty_print()
                f = open('/home/tcs/ims_sip.log', 'w')
                print >> f, cp.pretty_print()
            if cp.highest_layer == "HTTP":
                print cp.pretty_print()
                h = open('/home/tcs/ims_http.log', 'w')
                print >> h, cp.pretty_print()

    def stop(self):
        p = subprocess.Popen(['pgrep', '-l' , 'tshark'], stdout=subprocess.PIPE)
        out, err = p.communicate()

        for line in out.splitlines():        
            line = bytes.decode(line)
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)

if __name__ == "__main__":
    a = packetsniffer("urvika")
    a.run()
