#!/usr/bin/env python
# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2009-2020 German Aerospace Center (DLR) and others.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# https://www.eclipse.org/legal/epl-2.0/
# This Source Code may also be made available under the following Secondary
# Licenses when the conditions for such availability set forth in the Eclipse
# Public License 2.0 are satisfied: GNU General Public License, version 2
# or later which is available at
# https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

# @file    runner.py
# @author  Lena Kalleske
# @author  Daniel Krajzewicz
# @author  Michael Behrisch
# @author  Jakob Erdmann
# @date    2009-03-26

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
from numpy import random
import numpy as np
from pathlib import Path
import datetime
from Simulation import Simulation
import matplotlib.pyplot as plt
from utils import mean_confidence_interval

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa

def generate_routefile(seconds = 3600, pWE = 0.1, pNS = 0.1, pSN=0.1, pEW=0.1, dWE = 0.1, dNS = 0.0, pEmergency = 0.01,
                       routefile=None):
    """ Generates a route file with the level of traffic described by the parameters

    Args:
        seconds (int, optional): Number of seconds to introduce vehicles. Defaults to 3600 (an hour). 
        pWE (float, optional): Number of expected vehicles per second in the W->E direction. Defaults to 0.1.
        pNS (float, optional): Number of expected vehicles per second in the N->S direction. Defaults to 0.1.
        dWE (float, optional): Percentage of deceivers expected in the W->E direction. Defaults to 0.0.
        dNS (float, optional): Percentage of deceivers expected in the N->S direction. Defaults to 0.0.
    """
    random.seed(15)  # make tests reproducible
    deceiver_suffix = "_dec"
    emergency_suffix = "_emergency"
    car_following_model = "IDM" # Suggested options:  IDM, ACC
    tau = 1 # Expected time between vehicles in seconds
    sigma = 0 # Driver imperfection in the range [0,1] where 0=perfect
    following_model = f""" carFollowModel="{car_following_model}" sigma="{sigma}" tau="{tau}" """
    car_specs = """ accel="0.8" decel="4.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger" """
    depart_speed = "desired"

    with open(routefile, "w") as routes:
        print(f"""<routes>
        <vType id="Car" length="5.00" minGap="2.50" maxSpeed="16.67" guiShape="passenger" carFollowModel="IDM" accel="0.8" decel="4.5" tau="1.0"/>

        <route id="right" edges="1to2 2to3 outr" />
        <route id="down" edges="9to2 2to6 outs" />
        <route id="up" edges="12to7 7to3 outn" />
        <route id="left" edges="8to7 7to6 outl" />
        """, file=routes)
        vehNr = 0
        veh_der = 0
        veh_izq = 0
        veh_aba = 0
        veh_arr = 0
        veh_emergency = 0
        dict_routes = {
            "right": veh_der,
            "left": veh_izq,
            "up": veh_arr,
            "down": veh_aba
        }
        routes_list = ["right", "left", "up", "down"]

        for i in range(seconds):

            if random.uniform(0, 1) < pEmergency:
                emergency = emergency_suffix
                color = "red"
                decision_route = routes_list[random.randint(0, len(routes_list))]
                print(f'    <vehicle id="{decision_route}_%i{emergency}" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (vehNr, i), file=routes)
                vehNr += 1
                veh_emergency += 1
                dict_routes[decision_route] += 1

            if random.rand()< pWE:
                color = "yellow"
                print(f'    <vehicle id="right_%i" type="Car" color="{color}" route="right" departSpeed="{depart_speed}" depart="%i" />' % (vehNr, i), file=routes)
                vehNr += 1
                veh_der+=1


            if random.rand() < pNS:
                color = "yellow"
                print(f'    <vehicle id="down_%i" type="Car" color="{color}" route="down" departSpeed="{depart_speed}" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
                veh_arr += 1


            if random.rand() < pSN:
                color = "yellow"
                print(f'    <vehicle id="up_%i" type="Car" color="{color}" route="up" departSpeed="{depart_speed}" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
                veh_aba += 1


            if random.rand() < pEW:
                color = "yellow"
                print(f'    <vehicle id="left_%i" type="Car" color="{color}" route="left" departSpeed="{depart_speed}" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
                veh_izq += 1


        print(" Vehiculos por la izquierda ", veh_izq)

        print(" Vehiculos por la derecha ", veh_der)
        print(" Vehiculos por la arriba ", veh_arr)
        print(" Vehiculos por la abajo ", veh_aba)
        print(" Vehiculos emergencia ", veh_emergency)
        print("</routes>", file=routes)

# The program looks like this
#    <tlLogic id="0" type="static" programID="0" offset="0">
# the locations of the tls are      NESW
#        <phase duration="31" state="GrGr"/>
#        <phase duration="6"  state="yryr"/>
#        <phase duration="31" state="rGrG"/>
#        <phase duration="6"  state="ryry"/>
#    </tlLogic>

def run(traffic_lights=False):
    """execute the TraCI control loop"""
    state = Simulation()

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        state.step(step, traffic_lights)
        if step == 15000:
           break
        step += 1

    step_hot = 1000
    step_stop = 200
    plt.plot(range(len(state.city_density[step_hot:-step_stop])), state.city_density[step_hot:-step_stop])
    print("Average density City: ", mean_confidence_interval(state.city_density[step_hot:-step_stop]))
    plt.title("density")
    plt.show()
    plt.plot(range(len(state.city_flow[step_hot:-step_stop])), state.city_flow[step_hot:-step_stop])
    print("Average flow City: ", mean_confidence_interval(state.city_flow[step_hot:-step_stop]))
    plt.title("flow")
    plt.show()
    plt.plot(range(len(state.city_vel[step_hot:-step_stop])), state.city_vel[step_hot:-step_stop])
    print("Average velocity City: ", mean_confidence_interval(state.city_vel[step_hot:-step_stop]))
    plt.title("vel")
    plt.show()
    traci.close()
    sys.stdout.flush()


def old_run():
    """execute the TraCI control loop"""
    step = 0
    # we start with phase 2 where EW has green
    traci.trafficlight.setPhase("0", 2)
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        if step == 1000:
            print("Vehicles: ")
            print(traci.edge.getLastStepVehicleIDs("1i"))

        if traci.trafficlight.getPhase("0") == 2:
            # we are not already switching
            if traci.inductionloop.getLastStepVehicleNumber("0") > 0:
                # there is a vehicle from the north, switch
                traci.trafficlight.setPhase("0", 3)
            else:
                # otherwise try to keep green for EW
                traci.trafficlight.setPhase("0", 2)
        step += 1
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options

def generate_traffic_and_execute_sumo(sumoBinary, output_path, pWE = 0.1, pNS = 0.1, dWE = 0.1, pEW=0.1, pSN=0.1,
                                      dNS = 0.0, pEmergency=0.01,traffic_lights=False):

    routefile= "data/ciudad2x2_semaforo.rou.xml" if traffic_lights else "data/cross.rou.xml"
    # first, generate the route file for this simulation
    generate_routefile(pWE=pWE, pNS=pNS, pEW=pEW, pSN=pSN, dWE=dWE, dNS=dNS, pEmergency=pEmergency, routefile=routefile)

    cfg_sumo_file = "data/ciudad2x2_semaforo.sumocfg" if traffic_lights else "data/cross.sumocfg"

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([checkBinary('sumo-gui'), "-c", cfg_sumo_file,
                "--collision.mingap-factor", "0",
                "--step-length", "0.2",
                "--tripinfo-output", output_path])
    run(traffic_lights)


def run_batch(sumoBinary, vph_combinations, dec_array, traffic_lights):
    # Create the path to store the results and make sure it exists in the file system
    file_prefix = f"data/results/{datetime.date.today().isoformat()}"
    Path(file_prefix).mkdir(parents=True, exist_ok=True)

    # Iterate the parameter space generating the traffic and executing the simulations
    for vph in vph_combinations:
        for j, we_dec in enumerate(dec_array):
            for ns_dec in dec_array:
                file = f"{file_prefix}/tripinfo__t_{vph[1]}_{vph[0]}__d_{we_dec}_{ns_dec}.xml"
                print(file)
                generate_traffic_and_execute_sumo(sumoBinary, file, pWE=vph[1]/3600, pNS=vph[0]/3600, pSN=vph[0]/3600,
                                                  pEW=vph[0] / 3600, dWE=we_dec, dNS=ns_dec, pEmergency=0.01,
                                                  traffic_lights=traffic_lights)


def main(options = None):
     # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if hasattr(options, "nogui") and (not options.nogui) and False:
        sumoBinary = checkBinary('sumo')
        
        # Run the experiments in batch 
        vph_combinations = np.array([(900,900),(1200,600)])     # Parameter space for traffic level
        dec_array = np.linspace(0.0, 1, 6).round(1)  # Parameter space for deceiving percentage

        run_batch(sumoBinary, vph_combinations, dec_array, traffic_lights=True)
        return

    else:
        sumoBinary = checkBinary('sumo-gui')
    
    generate_traffic_and_execute_sumo(sumoBinary, "data/out-tripinfo.xml", dNS=0.0, dWE=0.0, pNS=720/3600, pWE=720/3600,
                                      pSN=720/3600, pEW=720/3600, pEmergency=0.01, traffic_lights=True)

# this is the main entry point of this script
if __name__ == "__main__":
    main(get_options())

