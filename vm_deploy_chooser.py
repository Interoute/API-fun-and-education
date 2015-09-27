#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: vm_deploy_chooser.py:
#   Purpose: Chooser-based command line interface to deploy a virtual machine
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# VERSION 2
#
# You can pass options via the command line: type 'python vm_deploy_chooser.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2015
#
# Original code by Kelcey Damage, 2012 & Kraig Amador, 2012
# Revised by Sandy Walker (Interoute), 2013

from __future__ import print_function
from collections import OrderedDict
import base64
import vdc_api_call as vdc
import getpass
import json
import os
import sys
import pprint
import time
import textwrap
import argparse
import urllib
import urllib2
import hashlib
import hmac


# Print a list and return choice of item. Source: http://stackoverflow.com/questions/13354460/simple-terminal-file-chooser-in-python-libraries
def choose_item_from_list(itemlist, prompt='Please select an item by its number'):
    prompt = prompt + ": "
    # this print is for preliminary message..
    # print(textwrap.dedent() )
    item_dict = {index: value for index, value in enumerate(itemlist)}
    item_display_list = ["%2d. %s" % (key, item_dict[key]) for key in item_dict] 
    column_print(item_display_list)
    print('')
    response = int(input(prompt))
    return {'itemindex': response, 'itemcontent': item_dict[response]}

# Print a list by columns. Source: 'col_print' at http://stackoverflow.com/questions/1524126/how-to-print-a-list-more-nicely
# Modified with 'min_length_for_columns' so that short lists must appear in one column
def column_print(lines, term_width=120, indent=0, pad=2, min_length_for_columns=15):
   n_lines = len(lines)
   if n_lines == 0:
      return
   col_width = max(len(line) for line in lines)
   if n_lines < min_length_for_columns:
      n_cols = 1
      col_len = int(n_lines/n_cols) + (0 if n_lines % n_cols == 0 else 1)
   else: 
      n_cols = int((term_width + pad - indent)/(col_width + pad))
      n_cols = min(n_lines, max(1, n_cols))
      col_len = int(n_lines/n_cols) + (0 if n_lines % n_cols == 0 else 1)
      if (n_cols - 1) * col_len >= n_lines:
         n_cols -= 1
   cols = [lines[i*col_len : i*col_len + col_len] for i in range(n_cols)]
   rows = list(zip(*cols))
   rows_missed = zip(*[col[len(rows):] for col in cols[:-1]])
   rows.extend(rows_missed)
   for row in rows:
      print(" "*indent + (" "*pad).join(line.ljust(col_width) for line in row))

if __name__ == '__main__':
    # STEP: Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-m", "--mode", choices=['deploy','d','print','p'], default='print',
                    help="specify the output mode: deploy (deploy the VM) or print (print the API call) (default: print)")
    parser.add_argument("-f", "--format", choices=['json','j','cloudmonkey','c','url'], default='json',
                        help="specify the format of the printed API call: json, cloudmonkey or url (default: json)")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region: Europe, USA or Asia (default Europe)")
    parser.add_argument("-i", "--iso", action='store_true', help="deploy from an ISO image")
    parser.add_argument("-k", "--keys", action='store_true', help="ask for choice of SSH keys")
    parser.add_argument("-u", "--userdata", action='store_true', help="ask for input of userdata by filename")
    parser.add_argument("-a", "--affinity", action='store_true', help="ask for selection of affinity group(s)")
    vdcRegion = parser.parse_args().region
    config_file = parser.parse_args().config
    mode = parser.parse_args().mode
    printFormat = parser.parse_args().format
    deployFromISO = parser.parse_args().iso
    askForSSHKeys = parser.parse_args().keys
    askForUserdata = parser.parse_args().userdata
    askForAffinityGroup = parser.parse_args().affinity
    
    # STEP: If config file is found, read its content,
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

    # STEP: Create the API access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

#TO ADD: CHOOSE REGION OR FIND ZONES FOR ALL REGIONS THAT THE VDC ACCOUNT CAN ACCESS..........................

    # STEP: Select the zone
    result = api.listZones({'region': vdcRegion})
    zonelist = [zone['name'] for zone in result['zone']]
    zone_ids = [zone['id'] for zone in result['zone']]
    choice = choose_item_from_list(zonelist, prompt="Select the zone?")
    zone_id = zone_ids[choice['itemindex']]
    print("Selected zone: %s, %s\n" % (zone_id, choice['itemcontent']))

    # STEP: Select the template or ISO image
    if deployFromISO:
       print("Error: ISO case not implemented yet")
       exit
    else:
       request = {
        'region': vdcRegion,
        'templatefilter': 'executable',
        'zoneid': zone_id,
       }
       result = api.listTemplates(request)
       templates_sorted = sorted(result['template'], key=lambda item: item['name'].upper())
       templatelist = [template['name'] for template in templates_sorted]
       template_ids = [template['id'] for template in templates_sorted]
       choice = choose_item_from_list(templatelist, prompt="Select the template?")
       template_id = template_ids[choice['itemindex']]
       print("Selected template: %s, '%s'\n" % (template_id, choice['itemcontent']))

    # STEP: Select the compute/service offering
    ramlist = [512,1024,2048,4096,6144,8192,16384,24576,32768,65536,131072]
    choice_cpu = input("Input the number of CPUs? (between 1 and 12): ")
    print('')
    choice_ram = choose_item_from_list(map(lambda x: float(x)/1024, ramlist), prompt="Select the amount of RAM (GBytes)?")
    result = api.listServiceOfferings({'region': vdcRegion})
    serviceoffering_id = [s['id'] for s in result['serviceoffering'] if s['name']=='%d-%d'% (ramlist[choice_ram['itemindex']],choice_cpu)][0]
    print("Selected service offering: %s, \'%s\'\n" % (serviceoffering_id, '%d-%d'% (ramlist[choice_ram['itemindex']],choice_cpu)))

    # (optional) STEP: Select the affinity groups (if any exist)
    if askForAffinityGroup:
       print("Error: Select affinity groups not implemented yet")

    # STEP: Select the network(s)
    result = api.listNetworks({'region': vdcRegion, 'zoneid': zone_id})
    network_ids = [network['id'] for network in result['network']]
    networklist = ['%s (%s)' % (network['displaytext'],network['name']) for network in result['network']]
    network_num = input("Input the number of networks?: ")
    if network_num == 1:
       choice = choose_item_from_list(networklist, prompt="Select the network from the list? (this will be the default)")
       network_id = network_ids[choice['itemindex']]
       print("Selected network: %s, %s\n" % (network_id, choice['itemcontent']))
    else:
       choice = choose_item_from_list(networklist, prompt="Select network 1? (this will be the default)")
       network_id = [network_ids[choice['itemindex']]]
       for i in range(1,network_num):
          choice = choose_item_from_list(networklist, prompt="Select network %d?"%(i+1))
          network_id = network_id + [network_ids[choice['itemindex']]]
       print("Selected networks: %s\n" % (network_id))
   
    # (optional) STEP: Select keys
    if askForSSHKeys:
       result = api.listSSHKeyPairs({'region': vdcRegion})
       if result=={}:
          print("Error: SSH Keypair asked for, but none are set up in this account in this region")
          askForSSHKeys = False
       else:
          keypairnames = [keypair['name'] for keypair in result['sshkeypair']]
          keypairlist = ['%s (%s)' % (keypair['name'],keypair['fingerprint']) for keypair in result['sshkeypair']]
          choice = choose_item_from_list(keypairlist, prompt="Select SSH keypair?")
          keypairname = keypairnames[choice['itemindex']]

    # (optional) STEP: Input userdata
    if askForUserdata:
       print('')
       userdataFilename = raw_input('Input the path/name for the PLAIN TEXT file with the userdata: ')
       try:
          with open(userdataFilename) as fh:
             userdata=fh.read()
          userdata_b64 = base64.b64encode(userdata)
       except IOError:
          print("Error: Userdata plain text file not found or cannot be opened. Userdata will not be included in the deploy.")
          askForUserdata = False
          pass
          
       
    # STEP: Enter the VM 'name' and 'displaytext'
    ## TO DO: (1) create a default VM name, (2) do a test to check new name is unique against existing VMs
    #default_hostname =
    print('')
    hostname = raw_input(
       # 'Input name for the new VM (default %s):' % default_hostname
       'Input name for the new VM (name must be unique): ' 
    )
    hostname = hostname.strip()
    #if len(hostname) == 0:
    #    hostname = default_hostname

    default_displayname = hostname
    displayname = raw_input(
        'Input displayname for new VM (press ENTER for default: %s):' % default_displayname
    )
    displayname = displayname.strip()
    if len(displayname) == 0:
        displayname = default_displayname
    
    # STEP: Deploy the VM, or print out the API call
    deploy_params = {
        'region': vdcRegion,
        'serviceofferingid': serviceoffering_id,
        'templateid': template_id,
        'zoneid': zone_id,
        'displayname': displayname,
        'name': hostname,
        'networkids': network_id
    }
    if askForSSHKeys:
        deploy_params['keypair'] = keypairname
    if askForUserdata:
        deploy_params['userdata'] = userdata_b64
    print('')
    if mode=='print':
        print("-------------------------------------------\nRequired deploy command in %s format\n-------------------------------------------\n" % (printFormat))
        if printFormat=='json':
           print(json.dumps(deploy_params))
           print('')
        elif printFormat=='cloudmonkey':
           # For Cloudmonkey, 'region' is set by a separate command
           deploy_params.pop('region')  
           params = ["%s=%s" % (key, deploy_params[key]) for key in deploy_params]
           print("NOTE: you need to execute the command 'set region %s' for the following deploy command to work...\n" % (vdcRegion))
           print("deploy virtualmachine " + " ".join(params))
           print('')
        else:
           deploy_params['command'] = 'deployVirtualMachine'
           httprequest = zip(deploy_params.keys(), deploy_params.values())
           httprequest.sort(key=lambda x: x[0].lower())
           httprequest_data = "&".join(["=".join([r[0], urllib.quote_plus(str(r[1]))])
                                for r in httprequest])
           hashStr = "&".join(
               [
                "=".join(
                    [r[0].lower(),
                     str.lower(urllib.quote_plus(str(r[1]))).replace(
                         "+", "%20"
                     )]
                ) for r in httprequest
            ])
           sig = urllib.quote_plus(base64.b64encode(
             hmac.new(
                 secret,
                 hashStr,
                 hashlib.sha1
             ).digest()
           ).strip())
           httprequest_data += "&signature=%s" % sig
           print(api_url + "?" + httprequest_data)
           print('')
    else:
        print("Ready to deploy VM with these parameters:")
        pprint.print(json.dumps(deploy_params))
        choice = raw_input("Input D to deploy or any other key to exit:")
        if choice=="d" or choice=="D":
           result = api.deployVirtualMachine(deploy_params)
           job_id = result['jobid']
           pprint.pprint(api.wait_for_job(job_id))
