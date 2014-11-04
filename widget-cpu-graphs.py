#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: widget-cpu-graphs.py
#   Purpose: GUI widget to display graphs of CPU loads on VMs in a VDC
#   Requires: class VDCApiCall in the file vdc_api_call.py
#       [https://gist.github.com/InterouteGIST/aff2f957b7f0d766fab9]

# Copyright (C) Interoute Communications Limited, 2014

# This program is used in the blog post:
# http://cloudstore.interoute.com/main/knowledge-centre/blog/vdc-api-programming-fun-part-05
 
# How to use (for Linux and Mac OS):
# (0) You must have Python version 2.6 or 2.7 installed in your machine
# (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
# http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
# (2) Put this file and the file vdc_api_call.py in any location
# (3) You can run this file using the command 'python widget-cpu-graphs.py'


import matplotlib
matplotlib.use('TkAgg') 

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.figure as mplfig
import matplotlib.pyplot as plt

from Tkinter import *
import vdc_api_call as vdc
import json
import os
import datetime
import time
import ast
from collections import deque

class Application(Frame):
    def plot_update(self):
        test=self.update_cpu_data()
        if not(test): # API connection was not made to get fresh data
            print("%s: ERROR in plot_update: No API connection or No data returned" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.a.text(min(0.0,-self.plot_interval*(self.plot_points-1)/2.0),0.5,"ERROR: No API connection")
            self.fig.canvas.draw()
            self.after(self.plot_interval*1000,self.plot_update)
            return

        self.fig.clf() #clear the plot
        self.a = self.fig.add_subplot(111)

        vm_names = map(lambda x: x[0],self.cpuData[0])
        ##### REMOVE FROM PUBLIC CODE
        vm_names = vm_names[-5:] # SELECT FEW VMs TO SIMPLIFY SAMPLE OUTPUT
        #####
        data = sum(self.cpuData,[]) #this flattens the data structure
        current_time = data[-1][1][0]

        self.a.set_xlim([-self.plot_interval*(self.plot_points-1),0])
        self.a.set_ylim([0,max(10.0,1.1*max(map(lambda x: x[1][1], data)))])

        for name in vm_names:
            data_per_vm = [d[1] for d in data if d[0]==name]
            try:
                self.a.plot([-(current_time-d[0]).seconds for d in data_per_vm], [d[1] for d in data_per_vm], label=name, linewidth=3)
            except ValueError:
                pass #This will trigger when 'cpuused' data is missing for a VM

        self.a.legend(loc="center left",prop={'size':8})
        self.fig.canvas.draw()        
        self.after(self.plot_interval*1000,self.plot_update)
 
    def update_cpu_data(self):
        # Only data for 'Running' VM will be captured, so non-Running VM will not appear in the plot
        timenow=datetime.datetime.now()
        try:
            result = self.api.listVirtualMachines({})
            testdict = result['virtualmachine'][0] #this should throw exception if result has no content
            self.cpuData.append([[vm['name'],[timenow,self.get_cpuused(vm)]] 
                             for vm in result['virtualmachine'] if vm['state']=='Running'] )
            return 1
        except:
            return 0   # data not returned (mostly when connection to API fails)

    #Test if cpuused is available for returned data about a VM
    #Returns integer value of %age or 'NA'
    def get_cpuused(self,vm):
        if 'cpuused' in vm:
            return int(vm['cpuused'][:-1])
        else:
            return 'NA'   

    def refresh_plot(self):
        #this method is called when the 'REFRESH' button is pressed
        self.plot_update()
        
    def createWidgets(self):
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] = self.quit
        self.QUIT.pack({"side": "right"})

        self.refresh = Button(self)
        self.refresh["text"] = "REFRESH",
        self.refresh["command"] = self.refresh_plot
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
        self.plot_points = 100

        # Create deque object to hold cpu data
        self.cpuData = deque([],self.plot_points)

        # Initialise the plot
        self.fig = mplfig.Figure(figsize=(9,4), dpi=100)
        self.a = self.fig.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.plot_update()

        self.fig.canvas.draw()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
        self.pack()
        self.createWidgets()



root = Tk()
root.title("VM CPU Load Graph widget")
app = Application(master=root)
##root.after(10000,app.plot_update) # start the auto-updating (delay time in milliseconds)
app.mainloop()
root.destroy()
