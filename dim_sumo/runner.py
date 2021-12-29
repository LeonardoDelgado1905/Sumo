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

def get_node_number(i, j, city_size):
    if (i == 0 and j == 0) or (i == 0 and j == (city_size + 1)) or (i == (city_size + 1) and j == 0) or (
            i == (city_size + 1) and j == (city_size + 1)):
        return -1
    if i == 0 or i == (city_size + 1):
        node = city_size * (city_size + 2) + 2 * (j - 1) + 1 + (i != 0)
    else:
        node = (i - 1) * (city_size + 2) + 1 + j
    return node

def generate_routefile(seconds = 3600, pWE = 0.1, pNS = 0.1, pSN=0.1, pEW=0.1, dWE = 0.1, dNS = 0.0, pEmergency = 0.01,
                       routefile=None, city_size=2):
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
            """, file=routes)
        for i in range(1, city_size+1, 2): #Right routes
            id_route = str(int((i+1)/2))
            route = "    <route id=\"right" + id_route + "\" "
            edges = []
            for j in range(city_size):
                node_from = get_node_number(i, j, city_size)
                node_to = get_node_number(i, j+1, city_size)
                edges.append(str(node_from) + "to" + str(node_to))
            edges.append("outr" + id_route)
            route += " edges=\"" + " ".join(edges) + "\" />"
            print(route, file=routes)

        for i in range(2, city_size+1, 2): #Left routes
            id_route = str(int((i)/2))
            route = "    <route id=\"left" + id_route + "\" "
            edges = []
            for j in range(city_size, 0, -1):

                node_from = get_node_number(i, j + 1, city_size)
                node_to = get_node_number(i, j, city_size)
                edges.append(str(node_from) + "to" + str(node_to))
            edges.append("outl" + id_route)
            route += " edges=\"" + " ".join(edges) + "\" />"
            print(route, file=routes)


        for j in range(1, city_size+1, 2): #Down routes
            id_route = str(int((j+1)/2))
            route = "    <route id=\"down" + id_route + "\" "
            edges = []
            for i in range(city_size):
                node_from = get_node_number(i, j, city_size)
                node_to = get_node_number(i + 1, j, city_size)

                edges.append(str(node_from) + "to" + str(node_to))
            edges.append("outs" + id_route)
            route += " edges=\"" + " ".join(edges) + "\" />"
            print(route, file=routes)

        for j in range(2, city_size+1, 2): #Up routes
            id_route = str(int((j)/2))
            route = "    <route id=\"up" + id_route + "\" "
            edges = []
            for i in range(city_size, 0, -1):

                node_from = get_node_number(i + 1, j, city_size)
                node_to = get_node_number(i, j, city_size)
                edges.append(str(node_from) + "to" + str(node_to))
            edges.append("outn" + id_route)
            route += " edges=\"" + " ".join(edges) + "\" />"
            print(route, file=routes)

        """
        
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
        }Nr
        routes_list = ["right", "left", "up", "down"]
        """
        vehNr = 0
        veh_emergency = 0
        routes_list = []

        mid_size = int((city_size+1)/2)
        for i in range(mid_size):
            routes_list.append("right" + str(i+1))
            routes_list.append("down" + str(i + 1))
        for i in range(city_size - mid_size):
            routes_list.append("left" + str(i+1))
            routes_list.append("up" + str(i + 1))

        dict_routes = {}
        for r in routes_list:
            dict_routes[r] = 0


        for i in range(seconds):

            if random.uniform(0, 1) < pEmergency:
                emergency = emergency_suffix
                color = "red"
                decision_route = routes_list[random.randint(0, len(routes_list))]
                print(f'    <vehicle id="{decision_route}_%i{emergency}" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (vehNr, i), file=routes)
                vehNr += 1
                veh_emergency += 1
                dict_routes[decision_route] += 1

            for j in range(mid_size):
                if random.rand()< pWE:
                    color = "yellow"
                    decision_route = "right" + str(j+1)
                    print(f'    <vehicle id="{decision_route}_%i" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (vehNr, i), file=routes)
                    vehNr += 1
                    dict_routes[decision_route] += 1

            for j in range(mid_size):
                if random.rand() < pNS:
                    color = "yellow"
                    decision_route = "down" + str(j + 1)
                    print(f'    <vehicle id="{decision_route}_%i" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (
                        vehNr, i), file=routes)
                    vehNr += 1
                    dict_routes[decision_route] += 1

            for j in range(city_size - mid_size):
                if random.rand() < pSN:
                    color = "yellow"
                    decision_route = "up" + str(j + 1)
                    print(f'    <vehicle id="{decision_route}_%i" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (
                        vehNr, i), file=routes)
                    vehNr += 1
                    dict_routes[decision_route] += 1

            for j in range(city_size - mid_size):
                if random.rand() < pEW:
                    color = "yellow"
                    decision_route = "left" + str(j + 1)
                    print(f'    <vehicle id="{decision_route}_%i" type="Car" color="{color}" route="{decision_route}" departSpeed="{depart_speed}" depart="%i" />' % (
                        vehNr, i), file=routes)
                    vehNr += 1
                    dict_routes[decision_route] += 1


        for r in routes_list:
            print(" Vehiculos por la ruta: ", r, dict_routes[r])

        #print(" Vehiculos por la izquierda ", veh_izq)

        #print(" Vehiculos por la derecha ", veh_der)
        #print(" Vehiculos por la arriba ", veh_arr)
        #print(" Vehiculos por la abajo ", veh_aba)
        print(" Vehiculos totales ", vehNr)
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

def run(traffic_lights=False, trafficlights_flaws=0.25):
    """execute the TraCI control loop"""
    state = Simulation()
    total_trafficlights = list(traci.trafficlight.getIDList())
    print(total_trafficlights)
    #import random as rn
    #flaw_trafficlights = rn.choice(total_trafficlights, max(int(len(total_trafficlights)*trafficlights_flaws), 1))

    #for id in flaw_trafficlights:
    #    new_phase = rn.choice([0, 2])
    #    print("al semaforo", id, " lo vamos poner en fase ", new_phase)
    #    traci.trafficlight.setPhase(id, new_phase)
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
                                      dNS = 0.0, pEmergency=0.01,traffic_lights=False, trafficlights_flaws=0.25, city_size=2):

    name_according_city = str(city_size) + "x" + str(city_size)
    routefile= "data/ciudad" + name_according_city + "_semaforo.rou.xml" if traffic_lights else "data/cross"+ name_according_city + ".rou.xml"
    # first, generate the route file for this simulation
    print(routefile)
    generate_routefile(pWE=pWE, pNS=pNS, pEW=pEW, pSN=pSN, dWE=dWE, dNS=dNS, pEmergency=pEmergency, routefile=routefile, city_size=city_size)

    cfg_sumo_file = f"data/ciudad{city_size}x{city_size}_semaforo.sumocfg" if traffic_lights else f"data/cross{city_size}x{city_size}.sumocfg"



    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([checkBinary('sumo-gui'), "-c", cfg_sumo_file,
                "--collision.mingap-factor", "0",
                "--step-length", "0.2",
                "--tripinfo-output", output_path])
    run(traffic_lights, trafficlights_flaws)


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
                                                  traffic_lights=traffic_lights, city_size=5)


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
    
    generate_traffic_and_execute_sumo(sumoBinary, "data/out-tripinfo.xml", dNS=0.0, dWE=0.0, pNS=3600/3600, pWE=3600/3600,
                                      pSN=3600/3600, pEW=3600/3600, pEmergency=0.01, traffic_lights=False, trafficlights_flaws=0.25, city_size=10)

# this is the main entry point of this script
if __name__ == "__main__":
    main(get_options())

