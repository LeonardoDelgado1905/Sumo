import Lane
import traci
from SimStateAndConfig import SimStateAndConfig
from utils import mean_confidence_interval


class Simulation:

    def __init__(self):
        self.number_vehicles_in_lanes = dict()
        self.avg_speed_vehicles_in_lanes = dict()
        self.density_in_lanes = dict()
        self.lanes = dict()
        self.flow_in_lanes = dict()
        self.config = SimStateAndConfig()
        self.city_density = []
        self.city_flow = []
        self.city_vel = []
        self.lanes_names = ["1to2" , "2to3" , "outr", "8to7" , "7to6" , "outl" , "9to2" , "2to6" , "outs" , "12to7", "7to3" , "outn"]
        # Initialize the lanes
        lane_ids = traci.lane.getIDList()
        for lane_id in lane_ids:
            # Only consider lanes over 40 meters in length, this serves to remove lanes in intersections
            lane_length = traci.lane.getLength(lane_id)
            if lane_length > 40:
                self.lanes[lane_id] = Lane.Lane(lane_id, lane_length, self.config)
            self.number_vehicles_in_lanes[lane_id] = []
            self.avg_speed_vehicles_in_lanes[lane_id] = []
            self.density_in_lanes[lane_id] = []
            self.flow_in_lanes[lane_id] = []
        # The lanes are ready, let each of them figure out their adjacent lanes
        plain_lanes = self.lanes.values()
        for lane in plain_lanes:
            lane.find_adjacent_lanes(plain_lanes)

    def step(self, current_step, traffic_lights):
        self.config.current_step = current_step
        self.config.current_time_seconds = traci.simulation.getTime()
        # Send all lanes the update
        for lane_id in self.lanes:
            self.lanes[lane_id].step(current_step, traffic_lights)
            self.number_vehicles_in_lanes[lane_id].append(len(traci.lane.getLastStepVehicleIDs(lane_id)))
            length_total_veh = 0
            if self.number_vehicles_in_lanes[lane_id][-1] <= 0:
                length_total_veh = 0
            else:
                length_total_veh = (self.number_vehicles_in_lanes[lane_id][-1] * 10 - 5)
            self.density_in_lanes[lane_id].append(length_total_veh/500)
            if len(traci.lane.getLastStepVehicleIDs(lane_id)) == 0:
                val_speed = 0
            else:
                val_speed = mean_confidence_interval([traci.vehicle.getSpeed(veh) for veh in traci.lane.getLastStepVehicleIDs(lane_id)])[0]

            self.avg_speed_vehicles_in_lanes[lane_id].append(val_speed)
            self.flow_in_lanes[lane_id].append(self.density_in_lanes[lane_id][-1] * self.avg_speed_vehicles_in_lanes[lane_id][-1])


        self.city_density.append(float(mean_confidence_interval([v[-1] for k, v in self.density_in_lanes.items() if k[:-2] in self.lanes_names])[0]))
        self.city_flow.append(float(mean_confidence_interval([v[-1] for k, v in self.flow_in_lanes.items() if k[:-2] in self.lanes_names])[0]))
        self.city_vel.append(float(mean_confidence_interval([v[-1] for k, v in self.avg_speed_vehicles_in_lanes.items() if k[:-2] in self.lanes_names])[0]))

