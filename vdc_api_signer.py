#! /usr/bin/env python
# Python program to generate a VDC API authentication signature and runnable URL, and optionally execute the call
# 
# For download and information: https://github.com/Interoute/API-fun-and-education

# This program is configured for Python version 2.6/2.7 
#
# Copyright (C) Interoute Communications Limited, 2016
#
# The 'vdcapi' config file should have the form:
# {"api_secret": "ABCDEFe17Pgc5WMs28Jwm3H4Drn9CZa3y2K1RiFj5x9S8TzQo64Yfk0L7GqXp71AdWe3k9E0NzPw56XpHd8n4",
#  "api_key": "GHIJKL7H0XeKt25Ygi6ANp89JrWj46Fbo5L0Zfc7PTn1z9D3MwQy28EaBq42Sdk4RJd85SoHc0s6FBw39LyDp",
#  "api_url": "https://apiserver.example.com/api/"}
#
# EXAMPLE USES:
# $ python vdc_api_signer.py -c vdcapi -x listZones
# $ python vdc_api_signer.py -c vdcapi -x listZones -a '{"region":"asia"}'
# $ python vdc_api_signer.py -c vdcapi -x listZones -a '{"region":"asia"}' -e
# $ python vdc_api_signer.py -c vdcapi -x listZones -a '{"region":"asia"}' -t
# $ python vdc_api_signer.py -c vdcapi -x listVirtualMachines -a '{"region":"asia", "zoneid":"f2e16beb-b8b1-4f1d-b211-6b6feb6bb394"}'
#
# Reference: Accepting a dictionary as an argument with argparse and python
#   http://stackoverflow.com/questions/18608812/accepting-a-dictionary-as-an-argument-with-argparse-and-python

from __future__ import print_function
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib
import urllib2
import getpass
import os
import argparse
import datetime

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-x", "--command", help="API command name")
    parser.add_argument("-a", "--arguments", type=json.loads, default='{}', help="arguments for the API command (you must use single quotes outside, double quotes inside)")
    parser.add_argument("-e", "--execute", action='store_true', help="execute the API call")
    parser.add_argument("-m", "--method", choices=['GET','POST'], default='GET',
                        help="specify the HTTP request method: GET or POST (default: GET)")
    parser.add_argument("-o", "--outfile", default="", help="name of output file to receive the API call response") 
    parser.add_argument("-t", "--timeout", action="store_true", help="add expiry timeout to the API call URL (see -u for setting expiry time)")
    parser.add_argument("-u", "--expiryTime", type=int, default=600, help="expiry time duration for the API call in seconds (default: 600s)")
    config_file = parser.parse_args().config
    command = parser.parse_args().command
    args = parser.parse_args().arguments
    executeCall = parser.parse_args().execute
    httpMethod = parser.parse_args().method
    outfile = parser.parse_args().outfile
    timeoutOn = parser.parse_args().timeout
    expiryTimeout = parser.parse_args().expiryTime
    
    # If config file is found, read its content,
    # else query user for the API endpoint URL, API key, Secret key
    if os.path.isfile(config_file):
        with open(config_file) as fh:
            data = fh.read()
            config = json.loads(data)
            api_url = config['api_url']
            apiKey = config['api_key']
            secret = config['api_secret']
    else:
        print('API endpoint url (e.g. http://10.220.18.115:8080/client/api):', end='')
        api_url = raw_input()
        print('API key:', end='')
        apiKey = raw_input()
        secret = getpass.getpass(prompt='API secret key:')

    args['apiKey'] = apiKey
    args['response'] = 'json'
    args['command'] = command

    #add expiry timeout to the API call
    if timeoutOn:
       expireTime = datetime.datetime.utcnow() + datetime.timedelta(seconds = expiryTimeout)
       args['signatureVersion'] = 3
       args['expires'] = expireTime.strftime("%Y-%m-%dT%H:%M:%S.%f%z")[:-7] + "+0000"

    request = zip(args.keys(), args.values())
    request.sort(key=lambda x: x[0].lower())
    request_data = "&".join(["=".join([r[0], urllib.quote_plus(str(r[1]),safe='*')]) for r in request])
    hashStr = "&".join(
            [
                "=".join(
                    [r[0].lower(),
                     str.lower(urllib.quote_plus(str(r[1]),safe='*')).replace(
                         "+", "%20"
                     )]
                ) for r in request
            ]
        )
    ##print("Request string to be hashed: %s" % hashStr)
    ##print("Base64 encoded signature (HMAC-SHA1): %s" %  base64.b64encode(hmac.new(secret,hashStr,hashlib.sha1).digest()))
    sig = urllib.quote_plus(base64.b64encode(
            hmac.new(
                secret,
                hashStr,
                hashlib.sha1
            ).digest()
        ).strip())

    print("Calculated VDC signature: %s" % sig)

    request_data +=  "&signature=%s" % sig

    if timeoutOn:
       print("Runnable URL (expires after %d seconds at %s): \n%s" % (expiryTimeout, args['expires'], api_url + '?' + request_data))
    else:
       print("Runnable URL: \n%s" % (api_url + '?' + request_data))

    if executeCall:
       try:
           if httpMethod == 'GET':
              connection = urllib2.urlopen(api_url + '?' + request_data)
           else: # POST request
              connection = urllib2.urlopen(api_url, request_data) 
           response = connection.read()
       except urllib2.HTTPError as error:
           print('HTTP Error: %s' % error.code)
           description = str(error.info())
           description = description.split('\n')
           description = [line
                       for line
                       in description
                       if line.startswith('X-Description: ')]

           if len(description) > 0:
               description = description[0].split(':', 1)[-1].lstrip()
           else:
               description = '(No extended error message.)'
           print(description)
           sys.exit()

       if outfile:
           fhout = open(outfile, 'w')
           fhout.write("# API CALL:\n# %s\n#" % (api_url + '?' + request_data))
           fhout.write("\n%s" % response)
           fhout.close()
       else:
           print("Response:\n %s" % response)

