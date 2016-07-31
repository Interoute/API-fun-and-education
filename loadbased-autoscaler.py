#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: loadbased-autoscaler.py
#   Purpose: Perform autoscaling of virtual machines in VDC based on loading of an HAProxy frontend server
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python loadbased-autoscaler.py -h'
# for usage information
#
# Based on orginal design and Perl script by Stefan Bienek
#
# Copyright (C) Interoute Communications Limited, 2016

from __future__ import print_function
import vdc_api_call as vdc
import sys
import getpass
import json
import os
import string
import datetime
import argparse
import re

if __name__ == '__main__':
    # STEP 1: Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region: Europe, USA or Asia (default Europe)")
    parser.add_argument("-w", "--writediag", action='store_true', help="write a diag file for use with nwdiag")
    parser.add_argument("-f", "--diagfile", default='VDC-network-data.diag',
                    help="name of the output diag file for use with nwdiag")
    parser.add_argument("-z", "--zone", help="filter results by zone name (match by initial characters) ")
    parser.add_argument("-v", "--vmstate", action='store_true', help="display VM state by text colour")
    vdcRegion = parser.parse_args().region
    writeDiag = parser.parse_args().writediag
    config_file = parser.parse_args().config
    zonenameFilter = parser.parse_args().zone
    showVmState =  parser.parse_args().vmstate
    if writeDiag:
       diagfileName = parser.parse_args().diagfile

    # STEP 2: If config file is found, read its content,
    # else query user for the URL, API key, Secret key
    if os.path.isfile(config_file):
        with open(config_file) as fh:
            data = fh.read()
            config = json.loads(data)
            api_url = config['api_url']
            apiKey = config['api_key']
            secret = config['api_secret']
    else:
        print('API url (e.g. http://10.220.18.115:8080/client/api):', end='')
        api_url = raw_input()
        print('API key:', end='')
        apiKey = raw_input()
        secret = getpass.getpass(prompt='API secret:')

    # STEP 3: Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    # STEP 4: API calls to get the information about networks and VMs
