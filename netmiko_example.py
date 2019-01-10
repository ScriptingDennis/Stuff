#!/usr/bin/python
"""
https://pynet.twb-tech.com/blog/automation/netmiko.html - Kirk Byers
"""

import sys
import os
from netmiko import ConnectHandler
from getpass import getpass
from pprint import pprint

# limber up and be flexible
WIN = 'win' in sys.platform
PY3 = sys.version_info[0] == 3

if not os.getenv('NET_TEXTFSM'):
  if WIN:
    os.environ['NET_TEXTFSM'] = 'M:\\ntc-templates\\templates'
  else:
    os.environ['NET_TEXTFSM'] = '/etc/ansible/library/ntc-ansible/ntc-templates/templates'

if PY3:
  host = input("Enter your hostname: ")
else:
  host = raw_input("Enter your hostname: ")

# get connected
device = {
    'device_type': 'cisco_ios',
    'host': host,
    'username': 'svc_rheltowerro',
    'password': getpass(),
}
net_connect = ConnectHandler(**device)

# do it like a string of text
output = net_connect.send_command("show ip int brief")
print(output)
print("******\n\n")

out_lines = output.splitlines()
for line in out_lines:
  if 'unassigned' not in line:
    print(line)
print("******\n\n")
    
# do it like a list of dicts
parsed_output = net_connect.send_command("show ip int brief", use_textfsm=True)
for interface in parsed_output:
  if interface['ipaddr'] != 'unassigned':
    pprint(interface)
print("******\n\n")

# do it again
print(net_connect.send_command("show version", use_textfsm=True))
