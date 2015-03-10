#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: vdc_starter.py
#   Purpose: Starter file for API programming
#   Requires: class VDCApiCall in the file vdc_api_call.py
# For download and information see the repo:
#   https://github.com/Interoute/API-fun-and-education 
#
# Copyright (C) Interoute Communications Limited, 2014

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
from pprint import pprint
import argparse

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region (Europe, USA or Asia)")
    vdcRegion = parser.parse_args().region
    config_file = parser.parse_args().config
    
    # If config file is found, read its content,
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

    # Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    # Define the request
    #request = {}   

    # Execute the API call
    #result = api.listZones(request)

    #print the result
    #pprint(result)
    
    # FOR ASYNCHRONOUS CALLS ONLY
    #pprint(api.wait_for_job(result['jobid']))

