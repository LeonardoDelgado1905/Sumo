import traci
import numpy as np
from Vehicle import Vehicle
from EmergencyVehicle import EmergencyVehicle
from FlawVehicle import FlawVehicle
from SimStateAndConfig import SimStateAndConfig
from Log import Log

class Lane:

    def __init__(self, id, lane_length, config : SimStateAndConfig):
        self.config = config
        self.id = id
        self.lane_length = lane_length
        self.log = Log(config)
        self.vehicles = []
        self.vehicle_ids = []
        self.current_step = 0
        self.shape = list(np.array(xy) for xy in traci.lane.getShape(self.id)) # Convert each of the points in the shape to numpy arrays
        self.edge_id = traci.lane.getEdgeID(self.id)
        self.adjacent_lanes = list() # Will have and entry for each of the points in the shape with the nearby lanes
        # Indicates the last step in which all vehicles in the lane have had their positions updated
        self.updated_in_step = 0
        self.convoy_cross = False
        self.last_vehicle_convoy = None

    def find_adjacent_lanes(self, lanes):        
        # For each of the points in the shape look for adjacent lanes
        for p in self.shape:
            adjacent = list()
            for lane in lanes:
                if lane.id != self.id and lane.is_adjacent_to_point(p):
                    adjacent.append(lane)
            self.adjacent_lanes.append(adjacent)
        #self.log.info(self.id, " adjacent to ", self.adjacent_lanes)
    
    def is_adjacent_to_point(self, point):
        for p in self.shape:
            if np.linalg.norm(p - point) < self.config.max_distance_between_adjacent_lanes:
                return True
        return False

    def step(self, current_step, traffic_lights) -> bool:
        # Keep track of the current step
        self.current_step = current_step
        # Find the id of the vehicles in the lane
        vehicle_ids = traci.lane.getLastStepVehicleIDs(self.id)
        # Create a vehicle object for each of the vehicles in the lane if they don't exist
        for vehicle_id in vehicle_ids:
            if vehicle_id not in self.vehicle_ids:
                # Determine the type of vehicle to insert in the simulation
                vehicle_class = EmergencyVehicle if "_emergency" in vehicle_id else Vehicle
                vehicle_class = FlawVehicle if "_flaw" in vehicle_id else vehicle_class
                # Create the vehicle and add it to the lane along with its id for performance reasons
                self.vehicles.append(vehicle_class(vehicle_id, self, self.config))
                self.vehicle_ids.append(vehicle_id)

        # Remove the leading vehicle if it is no longer in the lane
        if len(self.vehicles) > 0 and self.vehicles[0].id not in vehicle_ids:
            self.vehicles.pop(0)
            self.vehicle_ids.pop(0)

        # Give the leading vehicle a chance to comunicate with other vehicles
        if not traffic_lights:
            if len(self.vehicles) > 0:
                self.vehicles[0].step_leader(self)

    def send_message_in_radius(self, message, radius):
        # Before sending the message make sure all vehicles in the lane are up to date
        if self.updated_in_step < self.current_step:
            for vehicle in self.vehicles:
                vehicle.refresh_position()
            self.updated_in_step = self.current_step

        # Send the message to all the vehicles in the radius ignoring the sender
        responses = list()
        for vehicle in self.vehicles:
            if vehicle != message.sender and vehicle.distance_to_vehicle(message.sender) <= radius:
                responses.append(vehicle.process_message(message))

        self.log.info("Leader: ", message.sender.id, " , respuestas recibidas: ", responses)

        return responses

    def send_message_opposite_leader_in_radius(self, message, radius):
        # Find the endpoing closest to the sender
        min_index = 0
        min_distance = message.sender.distance_to_point(self.shape[0])
        for i in range(1, len(self.shape)):
            distance = message.sender.distance_to_point(self.shape[i])
            if distance < min_distance:
                min_index = i
                min_distance = distance
        
        # Send the message to the leaders in lanes that are opposite to the endpoint found
        responses = list()
        for opposite_lane in self.adjacent_lanes[min_index]:
            response = opposite_lane.send_message_to_leader_in_radius(message, radius)
            if not response is None:
                responses.append(response)

        #self.log.info(message.sender.id, " , mensajes: ", responses)

        return responses

    def send_perception_opposite_leader_in_radius(self, message, radius):
        # Find the endpoing closest to the sender
        min_index = 0
        min_distance = message.sender.distance_to_point(self.shape[0])
        for i in range(1, len(self.shape)):
            distance = message.sender.distance_to_point(self.shape[i])
            if distance < min_distance:
                min_index = i
                min_distance = distance

        # Send the message to the leaders in lanes that are opposite to the endpoint found
        responses = list()
        for opposite_lane in self.adjacent_lanes[min_index]:
            response = opposite_lane.send_perception_to_leader_in_radius(message, radius)
            if response is not None:
                responses.append(response)

        # self.log.info(message.sender.id, " , mensajes: ", responses)

        return responses

    def send_message_to_leader_in_radius(self, message, radius):
        # Get the leader in this lane
        leader = self.vehicles[0] if len(self.vehicles) > 0 else None
        # Check if it exists and is within the radius of the sender
        if (not leader is None 
           and leader.distance_to_intersection < self.config.start_negotiating_at_distance_from_intersection 
           and leader.distance_to_vehicle(message.sender) <= radius):
            # Send the message as requested
            return leader.process_message(message)
        return None

    def send_perception_to_leader_in_radius(self, message, radius):
        # Get the leader in this lane
        leader = self.vehicles[0] if len(self.vehicles) > 0 else None


        # Check if it exists and is within the radius of the sender
        if leader is not None:
            distance_to_vehicle = leader.distance_to_vehicle(message.sender)
            if (leader.distance_to_intersection < self.config.start_perception_at_distance_from_intersection
               and distance_to_vehicle <= radius):
                # Send the message as requested
                return leader.process_message(message)
        return None

    def relay_message_to_next_upstream_in_radius(self, message, relaying_vehicle : Vehicle, radius):
        """ Sends a message to the vehicle behind this the relaying_vehicle in this lane considering provided it is within a given distance

        Args:            
            message (Message): Message to relay
            relaying_vehicle (Vehicle): Vehicle that is relaying the message
            radius (double): Max distance between the vehicles to perform the relaying
        """
        relay_to_index = self.vehicles.index(relaying_vehicle) + 1
        if relay_to_index < len(self.vehicles) and relaying_vehicle.distance_to_vehicle(self.vehicles[relay_to_index]) <= radius:
            return self.vehicles[relay_to_index].process_message(message)

        return None
                
    def __str__(self):
        return self.id

    def __repr__(self):
        return "Lane " + self.id
