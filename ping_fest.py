#!/bin/python
'''
ping_fest.py
  call me with a network address, i.e.
  ping_fest.py 172.17.224.0/21
    ok, I can extrapolate a network address from a host IP, if I have to, e.g. 172.17.224.1/21
'''
try: 
    import queue as queue
except ImportError:
    import Queue as queue
import threading
import time
import platform
import subprocess
import ipaddress
import os 

NUM_WORKERS = 100
# The arguments for the 'ping', excluding the address.
if platform.system() == "Windows":
    ping_args = ["ping", "-n", "1", "-l", "1", "-w", "100"]
    hosts = os.path.join('M:\\repos\\NetworkVars\\', 'ntp_servers.txt')
elif platform.system() == "Linux":
    ping_args = ["ping", "-c", "1", "-l", "1", "-s", "1", "-W", "5"]
    hosts = os.path.join('/etc/ansible/NetworkVars/', 'ntp_servers.txt')
else:
    raise ValueError("Unknown platform")

exitFlag = 0
queueLock = threading.Lock()
pending = queue.Queue()
threads = []
responders= []
myTarget = ipaddress.ip_interface(u'172.19.94.0/24')

class myPinger (threading.Thread):
  def __init__(self, threadID, name, q):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.name = name
    self.q = q
  def run(self):
    ping_address(self.q)

def ping_address( q):
  while not exitFlag:
    queueLock.acquire()
    if not pending.empty():
      data = q.get()
      queueLock.release()
      with open(os.devnull, 'w')  as FNULL:
        try:
          subprocess.check_call(ping_args+[data], stdout=FNULL)
          responders.append(data)
        except:
          pass
    else:
      queueLock.release()
      time.sleep(1)

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Ping a network')
  parser.add_argument('network_string', nargs='*', help='Network as CIDR string')
  parser.add_argument('-t', '--thread_count', type=int)
  args = parser.parse_args()
  if args.network_string:
    if platform.python_version()[0] == '2':
      target_string = args.network_string[0].decode('utf-8')
    else:
      target_string = args.network_string[0]
    try:
      myTarget = ipaddress.ip_interface(target_string)
    except Exception as juju:
      print(juju)
      exit(1)



# Create new threads
start = time.time()
for threadID in range(1, NUM_WORKERS):
  thread = myPinger(threadID, "T-{}".format(threadID), pending)
  thread.start()
  threads.append(thread)

# Fill the pending queue
myNet = myTarget.network
queueLock.acquire()
for host in myNet.hosts():
    host_ip = str(host)
    pending.put(host_ip)
queueLock.release()
print ("Pinging {} devices".format(2 ** (myTarget.max_prefixlen - myTarget._prefixlen) - 2))

# Wait for queue to empty
while not pending.empty():
  pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
  t.join()

print ("found {} devices on {}".format(len(responders), str(myTarget.network)))
for ip in responders:
  print(ip)

finish = time.time()
print("Elapsed time: {0} sec".format(finish-start))
