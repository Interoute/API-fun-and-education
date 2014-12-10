#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: widget-vm-sparklines-v1.py
#   Purpose: GUI widget to display VM state with sparkine graphs for CPU loading
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education   

#  Requires: pysparklines [https://pypi.python.org/pypi/pysparklines, https://github.com/RedKrieg/pysparklines]

# Copyright (C) Interoute Communications Limited, 2014

# This program is used in the blog post:
# http://cloudstore.interoute.com/main/knowledge-centre/blog/vdc-api-programming-fun-part-07
 
# How to use (for Linux and Mac OS):
# (0) You must have Python version 2.6 or 2.7 installed in your machine
# (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
# http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
# (2) Put this file and the file vdc_api_call.py in any location
# (3) You can run this file using the command 'python widget-vm-sparklines-v1.py'

from Tkinter import *
import vdc_api_call as vdc
import json
import os
import datetime
import time
import ast
from collections import deque

import sparkline

class Application(Frame):
    def vmStates_update(self):
        #this method performs the API call 'listVirtualMachines'

        # Delete all current content
        self.vmStatesText.delete(1.0, END)

        request={}
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        try:
            result = self.api.listVirtualMachines(request)
            testdict = result['virtualmachine'][0] #this should throw exception if dictionary lookup fails
        except:
            # something wrong with the API connection, show error message and exit
            self.vmStatesText.insert('end', "*** Error: VM data not returned by API ***")
            return

        # Only data for Running VM will be added to cpuData
        timenow=datetime.datetime.now()
        self.cpuData.append([[vm['name'],[timenow,self.get_cpuused(vm)]] 
                             for vm in result['virtualmachine'] if vm['state']=='Running'] )

        vm_names = map(lambda x: x[0],self.cpuData[0]) #create a list of VM names
        data = sum(self.cpuData,[]) # flattens data by removing some of the list brackets

        self.vmStatesText.insert('end',"%d VMs in the account '%s'\nchecked at %s" % (result['count'],result['virtualmachine'][1]['account'],checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))

        vmcounter=0
        for vm in result['virtualmachine']:
            vmcounter = vmcounter + 1
            if vm['state'] == 'Running':
               data_per_vm = [d[1] for d in data if d[0]==vm['name']]
               self.vmStatesText.insert('end',"\n  [%2d] %s  |%s|" % (vmcounter,vm['name'],sparkline.sparkify([d[1] for d in data_per_vm])), ('stateRunning'))
            elif vm['state'] == 'Stopped':
               self.vmStatesText.insert('end',"\n  [%2d] %s  (%s)" % (vmcounter,vm['name'],vm['state']), ('stateStopped'))
            else:
               self.vmStatesText.insert('end',"\n  [%2d] %s  (%s)" % (vmcounter,vm['name'],vm['state']), ('stateOther'))
        #set callback to this method after plot_interval seconds
        self.vmStatesText.after(self.plot_interval*1000, self.vmStates_update)

    #Test if cpuused is available for returned data about a VM
    #Returns integer value of %age or 'NA'
    def get_cpuused(self,vm):
        if 'cpuused' in vm:
            return int(vm['cpuused'][:-1])
        else:
            return 'NA'   

    def refresh_states(self):
        #this method is called when the 'REFRESH' button is pressed
        self.vmStates_update()

    def createWidgets(self):
        self.vmStatesText = Text(self)
        self.vmStatesText["font"]=('Courier','14')
        self.vmStatesText["bg"]="white"
        self.vmStatesText["fg"]="black"
        self.vmStatesText.tag_configure('stateStopped',foreground='red')
        self.vmStatesText.tag_configure('stateRunning',foreground='green')
        self.vmStatesText.tag_configure('stateOther',foreground='blue')
        self.vmStatesText.pack({"side":"top"})
        self.vmStates_update()
        
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit
        self.QUIT.pack({"side": "right"})

        self.refresh = Button(self)
        self.refresh["text"] = "REFRESH",
        self.refresh["command"] = self.refresh_states
        self.refresh.pack({"side": "left"})

    def __init__(self, master=None):
        Frame.__init__(self, master)

        config_file = os.path.join(os.path.expanduser('~'), '.vdcapi')
        if os.path.isfile(config_file):
            with open(config_file) as fh:
                data = fh.read()
                config = json.loads(data)
                api_url = config['api_url']
                apiKey = config['api_key']
                secret = config['api_secret']
    
        # Create the api access object
        self.api = vdc.VDCApiCall(api_url, apiKey, secret)

        self.plot_interval = 10 
        self.plot_points = 25

        # Create deque object to hold cpu data
        self.cpuData = deque([],self.plot_points)

        # INITIALISE THE GUI
        self.pack()
        self.createWidgets()

root = Tk()
root.title("VM CPU Sparklines widget version 1")
app = Application(master=root)
app.mainloop()
root.destroy()
