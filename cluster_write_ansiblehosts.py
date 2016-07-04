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
    ##parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
    ##                help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
    parser.add_argument("-k", "--sshkeyfile", help="path/name value for ansible_ssh_private_key_file")
    parser.add_argument("-u", "--sshuser", default="root", help="value for ansible_user")
    datafile = parser.parse_args().filename
    sshkeyFile = parser.parse_args().sshkeyfile
    sshUser = parser.parse_args().sshuser

    # STEP: Load the cluster data from the JSON file
    with open(datafile) as json_file:
       zonesDict = json.load(json_file)

    ansiblehostsfile = datafile.split('.')[0] + "_ansible_hosts"
    sshport = zonesDict[zonesDict.keys()[0]]['publicport']

    # STEP: Open ansiblehostsfile
    with open(ansiblehostsfile, 'w') as outfile:
       outfile.write("[%s_HOSTS]\n" % datafile.split('.')[0])
       hostnum = 0
       # STEP: Write hosts information
       for z in zonesDict:
          if zonesDict[z]['internetipaddress'] != 'MISSING':
             hostnum = hostnum + 1
             print("HOST %d>> %s ansible_host=%s ansible_port=%d ansible_user=%s ansible_ssh_private_key_file=%s" % (hostnum, zonesDict[z]['virtualmachinename'], zonesDict[z]['publicipaddress'], sshport, sshUser, sshkeyFile))
             outfile.write("%s ansible_host=%s ansible_port=%d ansible_user=%s ansible_ssh_private_key_file=%s\n" % (zonesDict[z]['virtualmachinename'], zonesDict[z]['publicipaddress'], sshport, sshUser, sshkeyFile))
        
    # Step: File write complete
    print("File %s written. Program terminating." % ansiblehostsfile)

        
        



