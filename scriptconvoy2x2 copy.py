#!/usr/bin/env python
"""
@file    runner.py
@author  Lena Kalleske
@author  Daniel Krajzewicz
@author  Michael Behrisch
@author  Jakob Erdmann
@date    2009-03-26
@version $Id: runner.py 24864 2017-06-23 07:47:53Z behrisch $

Tutorial for traffic light control via the TraCI interface.

SUMO, Simulation of Urban MObility; see http://sumo.dlr.de/
Copyright (C) 2009-2017 DLR/TS, Germany

This file is part of SUMO.
SUMO is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.
"""
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import subprocess
import random
import numpy as np

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary

import traci




# The program looks like this
#    <tlLogic id="0" type="static" programID="0" offset="0">
# the locations of the tls are      NESW
#        <phase duration="20" state="GrGr"/>
#        <phase duration="3"  state="yryr"/>
#        <phase duration="20" state="rGrG"/>
#        <phase duration="3"  state="ryry"/>
#    </tlLogic>


# <tlLogic id="2" type="static" programID="0" offset="0">
#         0<phase duration="41" state="GGrr"/>
#         1<phase duration="3" state="yyrr"/>
#         2<phase duration="41" state="rrGG"/>
#         3<phase duration="3" state="rryy"/>
#     </tlLogic>


def run():
    """execute the TraCI control loop"""
    step = 0
    sensoresAH=0
    sensoresAV=0
    umbral=5
    ConvoyCruzo=5
    Convoypasando=0
    Vrestantesc=0
    vehiculosenCalleH=[]
    vehiculosenCalleV=[]
    QvpasandoV = []
    a=[]
    b=[]
    ii=0
    semafs = [2, 3, 6, 7]
    calleposteriorVer = ["2to6", "outn", "outs", "7to3"]
    calleposteriorHor = ["2to3", "outr", "outl", "7to6"]

    # we start with phase 2 where EW has green
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        # if Convoypasando==True:
        #     while traci.edge.getLastStepVehicleNumber(str(i)+"outr_0")<=5:
        for ii in range(0,4):
            if traci.trafficlights.getPhase(str(semafs[ii])) == 0:
                sensoresAH=0
                for i in range(0,5):
                    if traci.inductionloop.getLastStepVehicleNumber(str(i)+"H-int"+str(semafs[ii])) >0:
                        sensoresAH = sensoresAH+1
                        if (sensoresAH==umbral and len(traci.edge.getLastStepVehicleIDs(calleposteriorVer[ii]))>=5):
                               # print('El convoy cruzo en vertical')
                            traci.trafficlight.setPhase(str(semafs[ii]), 2)
 # inicializar convoy horizontal a cero 
 # sensor en calle posterior 
 # resetear el contador del sensor cuando paso el convoy
# vamos a revisar que imprime la función de los id en la calle 
        # vehiculosenCalleV = traci.edge.getLastStepVehicleIDs("outs")
        # if vehiculosenCalleV !=[]:
        #     QvpasandoV = vehiculosenCalleV[0]
        #     print(QvpasandoV)
        
        # vehiculosEnCalleV = traci.edge.getLastStepVehicleIDs("outr")
        # print(vehiculosEnCalleV)
        # print ("Longitud de la lista", len(vehiculosEnCalleV))
        # print ("El tipo vehiculosEnCalle", type (vehiculosEnCalleV))
        # for i in vehiculosEnCalleV:
        #     print ("Los Elementos de la lista", i)
        # if vehiculosEnCalleV:
        # #No Vacia
        #     QvpasandoV.append(vehiculosEnCalleV[0])
        # else:
        # #Vacia
        #     print ("Armando")
        # print (len(QvpasandoV))

                            
               

            if traci.trafficlights.getPhase(str(semafs[ii])) == 2:
                sensoresAV=0
                for i in range(0,5):
                    if traci.inductionloop.getLastStepVehicleNumber(str(i)+"V-int"+str(semafs[ii]))>0:
                        sensoresAV = sensoresAV+1
                        if (sensoresAV==umbral and len(traci.edge.getLastStepVehicleIDs(calleposteriorHor[ii]))>=5):
                               # print('El convoy cruzo en horizontal')
                                traci.trafficlight.setPhase(str(semafs[ii]), 0)


        #             if (sensoresAV==umbral):
        #                 if traci.edge.getLastStepVehicleNumber("outr")==5:
        #                     print('El convoy cruzo')
        #                     traci.trafficlight.setPhase("2", 0)

        # vehiculosenCalleH = traci.edge.getLastStepVehicleIDs("outr")
        #print(vehiculosenCalleH)
            
        step += 1
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')


    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", "ciudad2x2.sumocfg"])
    run()
