#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: check-vm-state.py
#   Purpose: Print the states of the VMs in a VDC using a colour-coded format
#   Requires: class VDCApiCall in the file vdc_api_call.py
#       [https://gist.github.com/InterouteGIST/aff2f957b7f0d766fab9]

# Copyright (C) Interoute Communications Limited, 2014

# This is a Python version of the bash shell script introduced in the blog post:
# http://cloudstore.interoute.com/main/knowledge-centre/blog/vdc-api-programming-fun-part-02

# How to use (for Linux and Mac OS):
#   (0) You must have Python version 2.6 or 2.7 installed in your machine
#   (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
#         http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
#   (2) Put this file and the file vdc_api_call.py in any location
#   (3) You can run this file using the command 'python check-vm-state.py'
#   (4) Or, run the command 'chmod +x check-vm-state.py' and then you can run with './check-vm-state.py'

# EVERYTHING IN THE FOLLOWING SECTION IS 'BOILERPLATE' CODE (ALWAYS THE SAME) TO ESTABLISH 
# THE API CONNECTION.....................................................................
 
from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import datetime

if __name__ == '__main__':
    cloudinit_scripts_dir = 'cloudinit-scripts'
    config_file = os.path.join(os.path.expanduser('~'), '.vdcapi')
    if os.path.isfile(config_file):
        with open(config_file) as fh:
            data = fh.read()
            config = json.loads(data)
            api_url = config['api_url']
            apiKey = config['api_key']
            secret = config['api_secret']
            try:
                cloudinit_scripts_dir = config['cloudinit_scripts_dir']
            except KeyError:
                pass
    else:
        print('API url (e.g. http://10.220.18.115:8080/client/api):', end='')
        api_url = raw_input()
        print('API key:', end='')
        apiKey = raw_input()
        secret = getpass.getpass(prompt='API secret:')

    # Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

# END OF THE BOILERPLATE SECTION

# NOW HERE IS THE CODE THAT PERFORMS THE TASK OF GETTING INFORMATION ABOUT THE VIRTUAL
# MACHINES AND DISPLAYING THAT INFORMATION IN A COLOUR-CODED FORM.....

    request = {'region':'europe'}

    checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)

    result = api.listVirtualMachines(request)

    print("\nChecking states of %d VMs in the account '%s'\nat %s:" 
        % (result['count'],result['virtualmachine'][1]['account'],checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))    

    for vm in result['virtualmachine']:
        if vm['state'] == 'Running':
           print("  \x1b[32m %s\x1b[0m" % vm['name'])
        elif vm['state'] == 'Stopped':
           print("  \x1b[31m %s (%s)\x1b[0m" % (vm['name'],vm['state']))
        else:
           print("  \x1b[36m %s (%s)\x1b[0m" % (vm['name'],vm['state']))

    print("--VM state check complete--")
