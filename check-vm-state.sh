#!/bin/bash

#VDC API
#check-vm-state.sh : Display the state information about VMs in a VDC

. ticktick.sh

cloudmonkey set display json
DATA=`cloudmonkey list virtualmachines`

tickParse "$DATA"

echo
echo -e "Checking states of ``count`` VMs by cloudmonkey at $(date -u) :"

for ((i=0; i<``count``; i++))
{
  index=`printf "%012d" "$i"`
  varread="__tick_data_virtualmachine_${index}_name";
  eval vmname=\$$varread
  varread2="__tick_data_virtualmachine_${index}_state";
  eval vmstate=\$$varread2
  if [ $vmstate = "Running" ]
   then
    printf "  \e[32m %s\e[0m\n" $vmname
  elif [ $vmstate = "Stopped" ]
   then
    printf "  \e[31m %s (%s)\e[0m\n" $vmname $vmstate
  else
    printf "  \e[36m %s (%s)\e[0m\n" $vmname $vmstate 
  fi
}

echo "--VM check complete--"