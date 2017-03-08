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
# Deploys the virtual machine immediately
# or returns JSON parameter data or Cloudmonkey command or runnable URL to perform the deployment
#
# Optional: execute or return commands to create portforwarding rules for ingress to the virtual machine
# Next improvements for portforwarding: check for conflicts on public ports; stronger error check and diagnosis
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
    response=-1
    while response not in range(len(itemlist)):
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
                    help="path/name of the config file to be used for the API URL and API keys (default: ~/.vdcapi)")
    parser.add_argument("-m", "--mode", choices=['deploy','d','print','p'], default='print',
                    help="specify the output mode: deploy (deploy the VM) or print (print the API call) (default: print)")
    parser.add_argument("-f", "--format", choices=['json','j','cloudmonkey','c','url'], default='json',
                        help="specify the format of the printed API call: json, cloudmonkey or url (default: json)")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region: Europe, USA or Asia (default: Europe)")
    parser.add_argument("-k", "--keys", action='store_true', help="ask for choice of SSH keys")
    parser.add_argument("-u", "--userdata", action='store_true', help="ask for input of userdata from plain text file")
    parser.add_argument("-p", "--portforwarding", action='store_true', help="ask for input of portforwarding port(s) and execute create rules or output the create commands")
    parser.add_argument("-a", "--affinity", action='store_true', help="[NOT IMPLEMENTED] ask for selection of affinity group(s)")
    parser.add_argument("-i", "--iso", action='store_true', help="[NOT IMPLEMENTED] deploy from an ISO image")

    vdcRegion = parser.parse_args().region
    config_file = parser.parse_args().config
    mode = parser.parse_args().mode
    printFormat = parser.parse_args().format
    deployFromISO = parser.parse_args().iso
    askForSSHKeys = parser.parse_args().keys
    askForUserdata = parser.parse_args().userdata
    askForAffinityGroup = parser.parse_args().affinity
    askForPortforwarding = parser.parse_args().portforwarding
    
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
    print("ZONES:")
    choice = choose_item_from_list(zonelist, prompt="Select the zone?")
    zone_id = zone_ids[choice['itemindex']]
    print("Selected zone: %s, %s\n" % (zone_id, choice['itemcontent']))

    # STEP: Check if a network exists in selected zone, otherwise terminate
    networks_available = api.listNetworks({'region': vdcRegion, 'zoneid': zone_id})
    if networks_available['count']==0:
        print("ERROR: There are no networks in the selected zone. You must create a network to deploy a virtual machine.")
        sys.exit("FATAL: Program terminating")
    # If 'subtype' is not in the API call response then add the keypair 'subtype':'unknown' to all network dicts in networks_available
    if 'subtype' not in networks_available['network'][0].keys():
        [netwk.update({'subtype':'unknown'}) for netwk in networks_available['network']]

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
       print("TEMPLATES:")
       choice = choose_item_from_list(templatelist, prompt="Select the template?")
       template_id = template_ids[choice['itemindex']]
       print("Selected template: %s, '%s'\n" % (template_id, choice['itemcontent']))

    # STEP: Select the compute/service offering
    # **** TO DO: CPU choice should be based on actual offerings at each RAM level (there are 16 CPU at higher RAM)
    # ****  Note there is an incomplete set of offerings at 49152 MB
    ramlist = [512,1024,2048,4096,6144,8192,12288,16384,24576,32768,65536,131072]
    choice_cpu = -1
    while choice_cpu not in range(1,13):
       choice_cpu = input("Input the number of CPUs? (between 1 and 12): ")
    print('')
    print("RAM MEMORY:")
    choice_ram = choose_item_from_list(map(lambda x: float(x)/1024, ramlist), prompt="Select the amount of RAM (GBytes)?")
    result = api.listServiceOfferings({'region': vdcRegion})
    serviceoffering_id = [s['id'] for s in result['serviceoffering'] if s['name']=='%d-%d'% (ramlist[choice_ram['itemindex']],choice_cpu)][0]
    print("Selected service offering: %s, \'%s\'\n" % (serviceoffering_id, '%d-%d'% (ramlist[choice_ram['itemindex']],choice_cpu)))

    # (optional) STEP: Select the affinity groups (if any exist)
    if askForAffinityGroup:
       print("Error: Select affinity groups not implemented yet, ignoring and continuing")

    # STEP: Select the network(s)
    network_ids = [network['id'] for network in networks_available['network']]
    networklist = ['%s (name: %s, subtype: %s)' % (network['displaytext'],network['name'],network['subtype']) for network in networks_available['network']]
    network_num = -1
    while network_num not in range(1,len(networklist)+1):
       network_num = int(input("Input the number of networks? %s: " % range(1,len(networklist)+1)))
    if network_num == 1:
       choice = choose_item_from_list(networklist, prompt="Select the network from the list? (this will be the default)")
       network_id = network_ids[choice['itemindex']]
       print("Selected network: %s, %s\n" % (network_id, choice['itemcontent']))
    else:
       choice = choose_item_from_list(networklist, prompt="Select network 1? (this will be the default)")
       network_id = network_ids[choice['itemindex']]
       for i in range(1,network_num):
          choice = choose_item_from_list(networklist, prompt="Select network %d?"%(i+1))
          network_id = network_id + ',' + network_ids[choice['itemindex']]
       print("Selected networks: %s\n" % (network_id))

    # (optional) STEP: Select portforwarding ports
    # Note: the case of multiple public IP addresses on one network is not handled.
    #  Only the first IP address in the list returned by the API call will be selected
    # 1 check network list for local with gateway network(s)
    # 2 if zero, exit to next step
    # 3 if more than one network, ask for selection
    # 3a show existing porforwarding rules for the (selected) network
    # 4 ask for number of portforwardings rules
    # 5 for each portwarding rule, ask for public port and private port; NOT DONE!! reject if rule exists for the public port

    if askForPortforwarding and mode=='print' and printFormat=='url':
        print("Warning: URL output for portforwarding rules cannot be generated because the signatures cannot be calculated.\nSkipping the portforwarding rule step...")
        askForPortforwarding = False
    
    if askForPortforwarding:
        networks_selected = {}
        for netid in network_id.split(','):
            networks_selected[netid] = {}
            tempnet = api.listNetworks({'region': vdcRegion, 'id':netid})['network'][0]
            if tempnet['subtype'] == 'internetgateway':
               networks_selected[netid]['network'] = tempnet
               try:
                   ipaddress_id = api.listPublicIpAddresses({'region': vdcRegion, 'associatednetworkid':netid})['publicipaddress'][0]['id']
                   networks_selected[netid]['ipaddressid'] = ipaddress_id
                   try:
                       networks_selected[netid]['pfrules'] = api.listPortForwardingRules({'region': vdcRegion, 'ipaddressid':ipaddress_id})['portforwardingrule']
                       networks_selected[netid]['noPFRules'] = False
                       networks_selected[netid]['noPublicIP'] = False
                   except KeyError:
                       networks_selected[netid]['ipaddressid'] = 'null'
                       networks_selected[netid]['noPFRules'] = True
                       networks_selected[netid]['noPublicIP'] = False
                       networks_selected[netid]['pfrules'] = []
               except KeyError:
                   print("Warning: Network \'%s\' does not have an associated public IP address" % (networks_selected[netid]['network']['displaytext']))
                   networks_selected[netid]['noPublicIP'] = True
                   networks_selected[netid]['noPFRules'] = True
                   networks_selected[netid]['pfrules'] = []
        if all(map(lambda x: not(x), networks_selected.values())):
            print("ERROR: You have not selected any internetgateway networks. Portforwarding rules cannot be created.")
            askForPortforwarding = False
        elif all(map(lambda x: x['noPublicIP'], [n for n in networks_selected.values() if n != {}])):
            print("ERROR: You have not selected any internetgateway networks with public IP addresses. Portforwarding rules cannot be created.")
            askForPortforwarding = False
        else:
            # at least one internetgateway network with public IP was found
            for net in [n for n in networks_selected.values() if n != {}]:
                print("Portforwarding rules for network \'%s\'" % (net['network']['displaytext']))
                if not net['noPFRules']: # if there are existing portforwarding rules for this network
                    print("  The existing rules are: ",end='')
                    for p in net['pfrules']:
                            if p['publicport']!=p['publicendport']:
                                print(" [%s/%s]->"%(p['publicport'],p['publicendport']),end='')
                            else:
                                print(" [%s]->"%(p['publicport']),end='')
                            if p['privateport']!=p['privateendport']:
                                print("[%s/%s]"%(p['privateport'],p['privateendport']),end='')
                            else:
                                print("[%s]"%(p['privateport']),end='')
                    print(" ")
                else:
                    print("  There are no portforwarding rules defined for this network\n")
                pfrule_num = -1
                while pfrule_num < 0:
                   pfrule_num = int(input("Input the number of portforwarding rules for network %s (0 to skip): " % (net['network']['displaytext'])))
                netid = net['network']['id']
                networks_selected[netid]['newpfrules'] = []
                if pfrule_num > 0:
                    for i in range(pfrule_num):
                        print("Enter portforwarding rule %s (TCP protocol is assumed):" % (i+1))
                        newpublicport = int(input("   publicport: "))
                        newpublicendport = raw_input("   publicendport (press enter for blank): ")
                        if newpublicendport == '':
                            newpublicendport = newpublicport
                        else:
                            newpublicendport = int(newpublicendport)
                        newprivateport = int(input("   privateport: "))
                        newprivateendport = raw_input("   privateendport (press enter for blank): ")
                        if newprivateendport == '':
                            newprivateendport = newprivateport
                        else:
                            newprivateendport = int(newprivateendport)
                        networks_selected[netid]['newpfrules'] = networks_selected[netid]['newpfrules'] + [{"protocol":"tcp", "publicport":newpublicport,
                           "publicendport":newpublicendport, "privateport":newprivateport, "privateendport":newprivateendport,
                           "ipaddressid": networks_selected[netid]['ipaddressid']}]
                else:
                    #no newpfrules for this network
                    print("No new portforwarding rules")
   
    # (optional) STEP: Select keys
    if askForSSHKeys:
       result = api.listSSHKeyPairs({'region': vdcRegion})
       if result=={}:
          print("Error: SSH Keypair asked for, but none are set up in this account in this region")
          askForSSHKeys = False
       else:
          keypairnames = [keypair['name'] for keypair in result['sshkeypair']]
          keypairlist = ['%s (%s)' % (keypair['name'],keypair['fingerprint']) for keypair in result['sshkeypair']]
          print("KEY PAIRS:")
          choice = choose_item_from_list(keypairlist, prompt="Select SSH keypair?")
          keypairname = keypairnames[choice['itemindex']]

    # (optional) STEP: Input userdata
    if askForUserdata:
       print('')
       print("USERDATA:")
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

    # If name or displayname are empty strings, then remove these parameter(s) from the API request
    if hostname == '':
        deploy_params.pop('name')
    if displayname == '':
        deploy_params.pop('displayname')

    print('')
    if mode=='print':
        print("-------------------------------------------\nRequired deploy command in %s format\n-------------------------------------------\n" % (printFormat))
        if printFormat=='json':
           print(json.dumps(deploy_params))
           print('')
        elif printFormat=='cloudmonkey':
           # for Cloudmonkey, 'region' is set by a separate command
           deploy_params.pop('region')  
           params = ["%s=%s" % (key, deploy_params[key]) for key in deploy_params]
           print("NOTE: you need to execute the command 'set region %s' for the following deploy command to work...\n" % (vdcRegion))
           print("deploy virtualmachine " + " ".join(params))
           print('')
        else:
           deploy_params['command'] = 'deployVirtualMachine'
           deploy_params['response'] = 'json'
           deploy_params['apiKey'] = apiKey 
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
        pprint.pprint(json.dumps(deploy_params))
        choice = raw_input("Input D to deploy or any other key to exit:")
        if choice=="d" or choice=="D":
           result = api.deployVirtualMachine(deploy_params)
           job_id = result['jobid']
           job_result_vm = api.wait_for_job(job_id)
           pprint.pprint(job_result_vm)

    if askForPortforwarding and pfrule_num > 0: # the second test catches when user skips setting pf rules
        pfrule_params_list = []
        for netid in [nid for nid in network_id.split(',') if networks_selected[nid] != {}]:
            for pfruledict in networks_selected[netid]['newpfrules']:
                pfruledict['openfirewall'] = 'true'
                pfruledict['region'] = vdcRegion
                pfrule_params_list = pfrule_params_list + [pfruledict]
        print('')
        if mode=='print':                                                                       
           print("-------------------------------------------\nPortforwarding command(s) in %s format\n-------------------------------------------\n" % (printFormat))
           print("REQUIRED!: Insert the UUID for \'virtualmachineid\', after the virtual machine has been deployed.\n")
           # for print output, add 'virtualmachineid' with a placeholder for each params dict
           pfrule_params_list_add_vmid = []
           for pfruleparams in pfrule_params_list:
               pfr = pfruleparams.copy()
               pfr.update({'virtualmachineid' : 'X-VMID-X'})
               pfrule_params_list_add_vmid = pfrule_params_list_add_vmid + [pfr]
           if printFormat=='json':
              print(json.dumps(pfrule_params_list_add_vmid))
              print('')
           elif printFormat=='cloudmonkey':
              print("NOTE: you need to execute the command 'set region %s' for the following commands to work...\n" % (vdcRegion))
              for pfruleparams in pfrule_params_list_add_vmid:
                  # for Cloudmonkey, 'region' is set by a separate command
                  pfruleparams.pop('region')
                  params = ["%s=%s" % (key, pfruleparams[key]) for key in pfruleparams]
                  print("create portforwardingrule " + " ".join(params))
                  print('')
        else:
           print("Ready to execute portforwarding rule creation for the following rules:")
           pprint.pprint(json.dumps(pfrule_params_list))
           choice = raw_input("Input E to execute or any other key to exit:")
           if choice=="e" or choice=="E":
              vm_id = job_result_vm['virtualmachine']['id']
              rulenum = 0
              for pfruleparams in pfrule_params_list:
                 rulenum += 1
                 pfruleparams['virtualmachineid'] = vm_id
                 print("Create portforwarding rule %d: %s" % (rulenum, pfruleparams))
                 try:
                    result_pf = api.createPortForwardingRule(pfruleparams)
                    job_id_pf = result_pf['jobid']
                    pprint.pprint(api.wait_for_job(job_id_pf))
                 except:
                    print("Error in creating portforwarding rule %d" % (rulenum))
              print("End of creating portforwarding rules")
        
                    
