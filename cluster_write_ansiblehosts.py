#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: cluster_write_anisblehosts.py:
#   Purpose: Write an 'ansible_hosts' file for a cluster of virtual machines created by cluster_deploy.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python cluster_write_anisblehosts.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2016
#
# Notes
#  This program assumes the cluster data provided is healthy and not missing required values
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

if __name__ == '__main__':
    # STEP: Parse the command line arguments
    parser = argparse.ArgumentParser()
    #parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
    #                help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
    ##parser.add_argument("-x", "--expunge", action='store_true', help="expunge the virtual machines")
    #config_file = parser.parse_args().config
    datafile = parser.parse_args().filename
    ##expunge = parser.parse_args().expunge

    ansiblefile = xxxxxxx
    
    # STEP: Load the cluster data from the JSON file
    with open(datafile) as json_file:
       zonesDict = json.load(json_file)

    # STEP: If VM has a Local Gateway network then execute Ansible call to modify 'ip route'
    for z in zonesDict:
       if 'virtualmachineid' not in zonesDict[z].keys():
          ##### call(["ansible","-i", "ansible_hosts", "SIN1", "-m", "shell", "-a", "ip route add 10.0.0.0/8 via 10.0.107.254"])
           
    # STEP: Use Ansible to check 'ip route' for all VM in the cluster
    print("Checking 'ip route' for all VMs in the cluster:")
    for z zonesDict:
    ##### call(["ansible","-i", "ansible_hosts", "SIN1", "-m", "shell", "-a", "ip route"])
       print("  VM %s in zone %s" % (zonesDict[z]['virtualmachineid'],zonesDict[z]['name']))
        
        



