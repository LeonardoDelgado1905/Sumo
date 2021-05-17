import random

import traci
import numpy as np
import Message
import Lane
from enum import Enum
from SimStateAndConfig import SimStateAndConfig
from Log import Log

class Vehicle_State(Enum):
    AUTO = 0,
    YIELDING = 1,
    GAINING_PRIORITY = 2

class Vehicle:

    def __init__(self, id, lane : Lane, config : SimStateAndConfig):
        self.id = id        
        self.config = config
        self.log = Log(config)
        self.current_step = -1
        self.lane = lane
        self.refresh_position()        
        self.state = Vehicle_State.AUTO
        self.distance_to_intersection = self.lane.lane_length
        self.max_decceleration = traci.vehicle.getDecel(self.id)
        self.yielding_since_second = -1
        self.already_negotiation = False
        # Set the speed mode of the vehicle to ignore intersection right of way
        traci.vehicle.setSpeedMode(self.id, 23) # See: https://sumo.dlr.de/docs/TraCI/Change_Vehicle_State.html#speed_mode_0xb3
        traci.vehicle.setTau(self.id, 0) # Setting the reaction time of the driver to 0 to simulate an autonomous agent       
        self.is_emergency = False
        self.decision = None


    def refresh_position(self):
        if self.config.current_step > self.current_step:
            try:
                # We have not updated the position in this step, update now
                self.position = np.array(traci.vehicle.getPosition(self.id))
                self.lane_position = traci.vehicle.getLanePosition(self.id)
                self.speed = traci.vehicle.getSpeed(self.id)
                #traci.vehicle.setSpeed(self.id, 13)
                #traci.vehicle.moveTo(self.id, self.lane.id, 450)

                self.current_step = self.config.current_step
                self.distance_to_intersection = self.lane.lane_length - self.lane_position
                #self.distance_to_intersection = 50
            except:
                pass

    def distance_to_vehicle(self, vehicle):
        return self.distance_to_point(vehicle.position)

    def distance_to_point(self, point):
        """Calculates the distance of this vehicle to a point

        Args:
            point (Numpy list of doubles (x, y)): point to calculate the distance to

        Returns:
            double: distance between the vehicle and the point
        """
        return np.linalg.norm(self.position - point)

    def step_leader(self, lane) -> bool:
        # Update the vehicle lane and position
        self.lane = lane
        self.refresh_position()

        # Check if there is a leader in the opposite lane that we can negotiate with                
        if self.distance_to_intersection < self.config.start_negotiating_at_distance_from_intersection:
            # Find if there is a leader we can speak to in the opposite lane
            leader_request_message = Message.RequestOppositeLeaderMessage(self, self.lane_position, self._yield_time())
            responses = self.lane.send_message_opposite_leader_in_radius(leader_request_message, self.config.max_comunication_distance_between_leaders)

            if len(responses) > 0:
                response = responses[0]
                #self.log.debug(self, "opposite leader response", response)
                #print("La respuesta recibida del lider opuesto es: ", response)
                self.already_negotiation = True
                # There is an opposite leader, behave accordingly to the current state of the vehicle negotiating as required

                if self.state == Vehicle_State.AUTO:
                    #print("Vehículo: ", self.id, " esta en estado auto a la negociacion")

                    return self.__process_auto(response)
                
                if self.state == Vehicle_State.YIELDING:
                   # print("Vehículo: ", self.id, " esta en estado yielding a la negociacion")
                    return self.__process_yielding(response)

                if self.state == Vehicle_State.GAINING_PRIORITY:
                   # print("Vehículo: ", self.id, " esta en estado gaining priority a la negociacion")
                    return self.__process_gaining_priority(response)
            else:
                pass
                #print("no Recibi respuesta")
        # There is no leader in the opposite lane, we can resume
        # Regla 1.A
        # Regla 1.B no existe (No se si hay manera de probar esto en una sola intersección)
        self.__resume()

        return True

    def __process_auto(self, response) -> bool:
        # There is an opposite vehicle, start the negotiation. At the moment we only consider cases where there is one opposite leader

        responses = self.lane.send_message_in_radius(Message.RequestEmergencyMessage(self),
                                                     self.config.max_comunication_distance_upstream)

        if str(type(self)) != '<class \'Vehicle.Vehicle\'>':
            self.is_emergency = True

        for r in responses:
            if isinstance(r, Message.ResponseEmergencyMessage):
                self.is_emergency = True

        if self.__should_yield(response) or str(type(response.sender)) != '<class \'Vehicle.Vehicle\'>' :
            # or sender tiene en cola una emergencia
            # We have to yield the lane
            #self.log.info(self, "w", self._yield_time(), " yielding to ", response.sender)
            #print("Vehiculo: ", self.id, " deberia detenerse")
            self.__yield()
            return True
        # The other vehicle is yielding, continue as normal
       # print("Vehiculo: ", self.id, " no deberia detenerse")
        return True

    def __process_yielding(self, response) -> bool:
        # First verify if we should be yielding or should resume according to the basic rules
        responses = self.lane.send_message_in_radius(Message.RequestEmergencyMessage(self),
                                                     self.config.max_comunication_distance_upstream)

        if str(type(self)) != '<class \'Vehicle.Vehicle\'>':
            self.is_emergency = True

        for r in responses:
            if isinstance(r, Message.ResponseEmergencyMessage):
                self.is_emergency = True

        should_yield = self.__should_yield(response)

        if should_yield and not self.is_emergency:
            # We are yielding, stop the vehicle if possible
            self.__yield()
            # Check if we should start gaining priority either by time or convoy
            convoy_completed, last_vehicle = self._convoy_completed()
            if convoy_completed:
                self.lane.last_vehicle_convoy = last_vehicle
                if response.sender.lane.last_vehicle_convoy is not None:
                    try:
                        last_vehicle_convoy_passed = response.sender.lane.last_vehicle_convoy.lane.id != traci.vehicle.getLaneID(response.sender.lane.last_vehicle_convoy.id)
                        if (self._timeout_expired() or convoy_completed) and last_vehicle_convoy_passed and not response.sender.is_emergency and str(type(response.sender)) == '<class \'Vehicle.Vehicle\'>':
                            self.log.info(self, " convoy completed")
                            self.state = Vehicle_State.GAINING_PRIORITY
                            #response.sender.lane.last_vehicle_convoy = None
                    except Exception as ex:
                        response.sender.lane.last_vehicle_convoy = None
                else:
                    if (self._timeout_expired() or convoy_completed) and not response.sender.is_emergency and str(
                            type(response.sender)) == '<class \'Vehicle.Vehicle\'>':
                        self.log.info(self, " convoy completed")
                        self.state = Vehicle_State.GAINING_PRIORITY

        else:
            # We don't need to keep yielding, transition to the gaining priority state
            #self.log.info(self, " timeout expired", )
            if self.is_emergency and response.sender.is_emergency and self.decision is None:
                self.decision = bool(random.randint(0, 1))
                response.sender.decision = not self.decision
            elif self.is_emergency and not response.sender.is_emergency:
                self.decision = None

            if self.decision == True or self.decision is None:
      #          print("Veh, " + self.id, " Gaining priority, Soy prioridad? ", self.is_emergency, " Deberia detenerme ", should_yield, " decision: ", self.decision)
                self.state = Vehicle_State.GAINING_PRIORITY
            else:
                self.state = Vehicle_State.YIELDING
            
        return True

    def _convoy_completed(self):

        # Message vehicles behind to see if we have a convoy completed
        responses = self.lane.send_message_in_radius(Message.RequestFollowerMessage(self), self.config.max_comunication_distance_upstream)
        # Check how many vehicles were detected
        detected = 0
        for r in responses:
            if isinstance(r, Message.ResponseFollowerMessage):
                detected += r.detected_vehicles

        #print("convoy size", detected, detected == self.config.min_convoy_size)
        # We check the number of responses +1 to cover this vehicle to approve the convoy size

        if detected + 1 >= self.config.min_convoy_size:
            return True, responses[-1].sender
        else:
            if self._yield_time() < self.config.min_yield_timeout_in_seconds:
                return False, None
            else:
                return True, None

    def _timeout_expired(self):
        return self._yield_time() >= self.config.yield_timeout_in_seconds

    def _yield_time(self):
        if self.yielding_since_second == -1:
            return 0
        return self.config.current_time_seconds - self.yielding_since_second

    def __process_gaining_priority(self, response) -> bool:

        if self.is_emergency and response.sender.is_emergency and self.decision is None:
            self.decision = bool(random.randint(0, 1))
            response.sender.decision = not self.decision
        elif self.is_emergency and not response.sender.is_emergency:
            self.decision = None

        if self.decision == True or self.decision is None:
           # print("Veh, " + self.id, " Gaining priority, Soy prioridad? ", self.is_emergency, " decision: ", self.decision)
            self.state = Vehicle_State.GAINING_PRIORITY
        else:
            self.state = Vehicle_State.YIELDING
            #self.__resume()
            return True

        if self.__should_yield(response):
            # Do not resume yet but start exchanging messages to gain priority
            responses = self.lane.send_message_opposite_leader_in_radius(Message.PriorityRequiredMessage(self), self.config.max_comunication_distance_between_leaders)            
            # If any of the responses indicate a non yielding vehicle continue in this state and try again in next step
            self.log.debug(self, "priority requested. Responses:")
            for r in responses:
                self.log.debug(self, r.sender,type(r))
                if type(r) is Message.YieldingNotPossibleMessage:
                    # At least one vehicle can not yield, try again later
                    return True
            return True
        self.log.debug(self, "Resuming after requesting priority.")
        # We do not need to keep yielding, resume
        self.__resume()
        return True

    def __should_yield(self, response) -> bool:
        """Checks if this vehicle should yield to the leader that send the response

        Args:
            response (ResponseOppositeLeaderMessage): Response from the opposite leader 

        Returns:
            bool: boolean indicating if this vehicle should yield
        """
        if not self.__can_stop():
            # We can not stop in time, do not try to yield
            self.log.debug(self, " not yielding, too close to brake")
            if not response.can_brake:
                self.log.info(self, " WARNING, NEITHER VEHICLES CAN BRAKE!", response)
            return False
        if self.__is_yielding() and not response.stopped:
            # We are already stopping and the opposite vehicle is not, we should yield
            """
            #condicion permite comparar dos carros y darle prioridad al mas cercano a la interseccion
            
            if response.distance_to_intersection > self.distance_to_intersection and response.can_brake:
                # Neither vehicles are stopped, and we are farther from the intersection, yield
                self.log.debug(self, " Resume AUTO")
                return False
            """
            self.log.debug(self, " yielding, already yielding and opposite not stopped")
            return True
        if self.__is_gaining_priority() and (not response.can_brake or not response.stopped):
            # We are gaining priority but the opposite vehicle can not stop, continue gaining priority
            self.log.debug(self, " yielding, gaining priority but opposite can not brake in time")
            return True
        if response.stopped:
            # The other vehicle is already stopped, no need to yield
            self.log.debug(self, " not yielding, opposite stopped")
            return False
        # Regla 2.A
        # Regla 2.B no existe (No se si hay manera de probar esto en una sola intersección)
        if response.distance_to_intersection < self.distance_to_intersection:
            # Neither vehicles are stopped, and we are farther from the intersection, yield
            self.log.debug(self, " yielding, none stopped and opposite closer to intersection")
            return True

        # Regla 3 existe pero la marca no existe y se toma "aleatorio" el que debería pasar
        # Implementar Marca
        if response.distance_to_intersection == self.distance_to_intersection and self.id > response.sender.id:
            # Neither vehicles are stopped and are the same distance to the intersection, use the vehicle ids to break the tie
            self.log.debug(self, " yielding, none stopped at same distance, loss tie breaker")
            return True
        # In any other case, do not yield
        self.log.debug(self, " not yielding, default case")
        return False
        
    def process_message(self, message):
        # Before processing the step, make sure the position has been refreshed
        self.refresh_position()        
    
        #self.log.debug(self, " receiving message ", message)

        # A leader wants to know how many vehicles are behind it
        if type(message) is Message.RequestFollowerMessage:
            return self._build_follower_response_message()

        # An opposite leader has completed the conditions to gain priority, we should yield if possible
        if type(message) is Message.PriorityRequiredMessage:
            return self.__process_priority_required_message(message)

        # The leader of an opposite lane wants to know if there are vehicles in conflict:
        if type(message) is Message.RequestOppositeLeaderMessage:
            return self.__process_request_opposite_leader_message(message)

        if type(message) is Message.RequestEmergencyMessage:
            return self.__process_request_emergency_message(message)

        #print(self)

        return

    def _build_follower_response_message(self):
        return Message.ResponseFollowerMessage(self)

    def __process_priority_required_message(self, message):        
        # Check if we are stopped or are able to yield
        if self.__is_yielding() or self.__yield():
            self.log.debug(self, "YIELDING", message)
            # We were able to yield, communicate this to the caller
            return Message.YieldingMessage(self)            
        else:
            self.log.debug(self, "CONTINUING", message)
            # We couldn't yield, forward the message to the next vehicle upstream so it can try to yield
            self.lane.relay_message_to_next_upstream_in_radius(message, self, self.config.max_comunication_distance_upstream)
            # And respond telling the caller that we couldn't yield in this step
            return Message.YieldingNotPossibleMessage(self)

    def __process_request_opposite_leader_message(self, message):
        return Message.ResponseOppositeLeaderMessage(self, self.lane.lane_length - self.lane_position, self.__is_yielding(), self._yield_time(), self.__can_stop())

    def __process_request_emergency_message(self, message):
        if str(type(self)) != '<class \'Vehicle.Vehicle\'>':
            return Message.ResponseEmergencyMessage(self)
        return Message.ResponseNotEmergencyMessage(self)

    def __yield(self) -> bool:
        if not self.__is_yielding():
            if not self.__can_stop(): 
                self.log.debug(self, "CANNOT YIELD, too close to brake")
                return False
            try:
                self.log.debug(self, "STOP AT", self.lane.edge_id, self.lane.lane_length - self.config.min_braking_distance_to_intersection, "current", self.distance_to_intersection, "stopping distance", self.__min_breaking_distance(), "speed", self.speed, "braking time", self.__min_breaking_time(), "max decceleration", self.max_decceleration)
                traci.vehicle.setStop(self.id, self.lane.edge_id, pos=self.lane.lane_length - self.config.min_braking_distance_to_intersection)
                self.state = Vehicle_State.YIELDING
                self.yielding_since_second = self.config.current_time_seconds
            except Exception as ex:
                print(ex)
            return True        
        return True

    def __can_stop(self):
        if self.speed == 0.0 or self.__is_yielding() or self.__is_gaining_priority():
            return True
        can_stop = self.distance_to_intersection - self.config.min_braking_distance_to_intersection >= self.__min_breaking_distance()
        return can_stop

    def __min_breaking_distance(self):
        if self.speed == 0.0:
            return 0
        min_stop_time = self.__min_breaking_time()
        return max(self.speed, self.config.stopping_time_delay * self.speed + self.speed * min_stop_time + (-1 * self.max_decceleration * min_stop_time ** 2)/2)

    def __min_breaking_time(self):
        """Calculates the minimum time that the vehicles needs to stop given its maximum deceleration and a base time

        Args:
            speed (float): Current speed of the vehicle

        Returns:
            float: Number of seconds expected to stop this car
        """
        return self.speed / self.max_decceleration + self.config.stopping_time_delay

    def __resume(self):
        if self.__is_yielding():
            try:
                traci.vehicle.resume(self.id)
                # traci.vehicle.setSpeed(self.id, -1)
                self.log.debug(self, "RESUME - distance to instersection", self.distance_to_intersection)
                self.state = Vehicle_State.AUTO
                self.yielding_since_seconds = -1
            except:
                pass

        elif self.__is_gaining_priority():

           try:
                traci.vehicle.setStop(self.id, self.lane.edge_id, pos=self.lane.lane_length - self.config.min_braking_distance_to_intersection, duration=0)
                self.state = Vehicle_State.AUTO
                self.yielding_since_seconds = -1
           except Exception as e:
               print(e)
        return

    def __str__(self):
        return self.id + "_[" + str(self.state) + "]"

    def __repr__(self):
        return self.id + "_[" + str(self.state) + "]"

    def __is_yielding(self):
        return self.state == Vehicle_State.YIELDING

    def __is_gaining_priority(self):
        return self.state == Vehicle_State.GAINING_PRIORITY

