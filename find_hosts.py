#!/usr/bin/python
'''
  find_hosts.py
    accept network address(cidr)
    ping all addresses on that net
    connect to port 22 of the responders
    print a list of "hosts" suitable for pasting into a static ansible inventory file
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
import socket

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
hosts=[]
myTarget = ipaddress.ip_interface(u'172.19.94.0/24')

class myPinger (threading.Thread):
  def __init__(self, threadID, name, q):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.name = name
    self.q = q
  def run(self):
    self.ping_address(self.q)

  def ping_address(self, q):
    """ read an IPAddr from the queue, call the O/S's ping utility """
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

class myPortConnect (threading.Thread):
  def __init__(self, threadID, name, q):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.name = name
    self.q = q
  def run(self):
    self.connect_port(self.q)

  def connect_port(self, q):
    """read an IPAddr from the queue, attempt to connect to port 22"""
    while not exitFlag:
      queueLock.acquire()
      if not pending.empty():
        serverIP = q.get()
        queueLock.release()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sock.connect_ex((serverIP, 22)) == 0:
          hosts.append(serverIP)
          sock.close()
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

# Fill the pinging queue
myNet = myTarget.network
queueLock.acquire()
for host in myNet.hosts():
    host_ip = str(host)
    pending.put(host_ip)
queueLock.release()
print ("Pinging {} devices on network {}".format((2 ** (myTarget.max_prefixlen - myTarget._prefixlen) - 2), myTarget.network))

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

print ("Checking {} devices on {} for port 22".format(len(responders), str(myTarget.network)))
# Create more threads
exitFlag = 0
for threadID in range(1, len(responders)):
  thread = myPortConnect(threadID, "T-{}".format(threadID), pending)
  thread.start()
  threads.append(thread)

# Fill the port checking queue - ok it's the same queue with a subset of the first queued item
queueLock.acquire()
for host in responders:
    pending.put(host)
queueLock.release()

# Wait for queue to empty
while not pending.empty():
  pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
  t.join()

for ip in hosts:
  print ("    {}:\n      os: ios".format(ip))

print ("found {} hosts in {} devices on {}".format(len(hosts), len(responders), str(myTarget.network)))

finish = time.time()
print("Elapsed time: {0} sec".format(finish-start))
