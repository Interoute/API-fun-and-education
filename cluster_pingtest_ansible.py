#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: cluster_pingtest_ansible.py:
#   Purpose: Use Ansible to do a complete VM-to-VM ping test for a cluster of virtual machines created by cluster_deploy.py
#   Requires: class VDCApiCall in the file vdc_api_call.py
#   Requires: Ansible runnable in the working directory
#   Requires: Ansible hosts inventory file (see cluster_write_ansiblehosts.py)
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python cluster_pingtest_anisble.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2016
#
# Notes
#  This program assumes the cluster data provided is healthy and not missing required values
#  ....................
#

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import sys
import pprint
import argparse
import re
from subprocess import call

# STEP: Parse the command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
parser.add_argument("-i", "--inventory", default="DEFAULT", help="name of hosts inventory file for Ansible")
datafile = parser.parse_args().filename
ifile = parser.parse_args().inventory
if ifile == 'DEFAULT':
   inventoryFile = datafile.split('.')[0] + "_ansible_hosts"
else:
   inventoryFile = ifile
 
# STEP: Load the cluster data from the JSON file
with open(datafile) as json_file:
   zonesDict = json.load(json_file)

# THIS CODE FOR REUSE IN PING SETUP..............................................

# STEP: If VM has a Local Gateway network then execute Ansible call to modify 'ip route'
#print("Adding routes for VMs in the cluster with 2 networks...")
#for z in zonesDict:
#   if zonesDict[z]['internetipaddress'] != 'MISSING':
#      call(["ansible","-i", inventoryFile, zonesDict[z]['virtualmachinename'], "-s", "-a", "ip route add 10.0.0.0/8 via %s" % (zonesDict[z]['privategateway'])])
       
# STEP: Use Ansible to check 'ip route' for all VMs in the cluster
#print("Checking 'ip route' for all VMs in the inventory file...")
#call(["ansible","-i", inventoryFile, "all", "-m", "shell", "-a", "ip route"])
        
        



