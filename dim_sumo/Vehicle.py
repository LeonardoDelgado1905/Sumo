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
    GAINING_PRIORITY = 2,
    WAITING = 3
class Vehicle:
# esta es una pequeña modificación
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
        self.waiting_since_second = -1
        self.already_negotiation = False
        self.opposite_flaw_yielding_since_second = -1
        # Set the speed mode of the vehicle to ignore intersection right of way
        traci.vehicle.setSpeedMode(self.id, 23) # See: https://sumo.dlr.de/docs/TraCI/Change_Vehicle_State.html#speed_mode_0xb3
        traci.vehicle.setTau(self.id, 0) # Setting the reaction time of the driver to 0 to simulate an autonomous agent       
        self.is_emergency = False
        self.is_flaw = False
        self.should_wait = False
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

        if self.state == Vehicle_State.WAITING:
            if self.waiting_time() < 12:
                print(self.waiting_time())
                return True



        #if self.should_wait:
        #    return self.__resume()
        #Cannot negociate, it's a flaw vehicle
        isFlaw = "_flaw" in self.id
        # Check if there is a leader in the opposite lane that we can negotiate with

        if self.distance_to_intersection < self.config.start_negotiating_at_distance_from_intersection:

            # Should I wait becouse the next line is full?
            leader_request_message = Message.RequestNextLastFollowerMessage(self, self.lane_position,
                                                                            self._yield_time())
            responses = self.lane.send_message_next_last_follower_in_radius(leader_request_message,
                                                                               self.config.max_comunication_distance_next_lane)


            if len(responses) > 0 and responses[0].stopped:
                print("He encontrado respuestas así que probablemente no debería pasar")
                if self.id == 'left2_878':
                    print("Voy a fallar")
                self.__yield()
                self.should_wait = True
                return True
            else:
                leader_request_message = Message.RequestNextLastFollowerMessage(self, self.lane_position,
                                                                                self._yield_time())
                responses = self.lane.send_perception_next_last_follower_in_radius(leader_request_message,
                                                                                self.config.max_perception_distance_next_lane)
                if len(responses) > 0 and responses[0].stopped:
                    self.__yield()
                    self.should_wait = True
                    return True
                else:
                    self.should_wait = False


            #if not isFlaw or self.distance_to_intersection < self.config.start_perception_at_distance_from_intersection:

            if isFlaw:
                # If is a flaw vehilce and it's in a distance from the intersection his state should be Yielding
                #self.state = Vehicle_State.YIELDING
                #return self.__process_yielding(None)
                if self.state == Vehicle_State.GAINING_PRIORITY:
                    return self.__resume()
                self.__yield()
                self.is_flaw = True
                responses = []
            else:
                # Find if there is a leader we can speak to in the opposite lane
                leader_request_message = Message.RequestOppositeLeaderMessage(self, self.lane_position, self._yield_time())
                responses = self.lane.send_message_opposite_leader_in_radius(leader_request_message, self.config.max_comunication_distance_between_leaders)

            if len(responses) > 0:
                if (self.id == 'down3_171' and '20to27' in self.lane.id) or self.id == 'left2_3041' or self.id == 'left2_878':
                    print("Voy a fallar")
                response = responses[0]
                #self.log.debug(self, "opposite leader response", response)
                #print("La respuesta recibida del lider opuesto es: ", response)
                self.already_negotiation = True
                self.should_wait = False
                self.opposite_flaw_yielding_since_second = -1
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

                # Find if there is a leader i can 'see' (perception) to in the opposite lane
                leader_request_message = Message.RequestOppositeLeaderMessage(self, self.lane_position,
                                                                              self._yield_time())
                responses = self.lane.send_perception_opposite_leader_in_radius(leader_request_message,
                                                                                self.config.max_perception_distance_between_leaders)

                if len(responses) > 0: # I don't get a response (i'm a flaw or the opposite leader is a flaw) but I'm 'seeing' another vehicle

                    #print("HUBO RESPUESTA EN PARCEPCION")
                    response = responses[0]
                    if isFlaw:
                        #print("VOY a PROCESAR UNA FALLA PARANDO")
                        #If there is a leader and i'm a flaw i'll handle my yielding
                        return self.__process_gaining_priority(response)
                    else:
                        #if self.should_wait:
                        #    print("yo identificado con ", self.id, " debería parar: ", self.opposite_flaw_yield_time())
                        #    self.state = Vehicle_State.AUTO
                        #    self.__yield()
                        self.handle_flaw_opposite_leader()
                        #If there is a flaw leader then i'll gain priority and thell the convoy there's a flaw
                        #print("Hay una falla al otro lado")
                        if self.state == Vehicle_State.YIELDING:
                            # print("Vehículo: ", self.id, " esta en estado yielding a la negociacion")
                            return self.__process_yielding(response)

                        if self.state == Vehicle_State.GAINING_PRIORITY or self.state == Vehicle_State.AUTO:
                            # print("Vehículo: ", self.id, " esta en estado gaining priority a la negociacion")
                            return self.__process_gaining_priority(response)

                #print("no Recibi respuesta")
           # else:
            #    return self.__process_yielding(None)


        # There is no leader in the opposite lane, we can resume
        # Regla 1.A
        # Regla 1.B no existe (No se si hay manera de probar esto en una sola intersección)
        self.__resume()

        return True

    def __process_auto(self, response) -> bool:
        # There is an opposite vehicle, start the negotiation. At the moment we only consider cases where there is one opposite leader

        responses = self.lane.send_message_in_radius(Message.RequestEmergencyMessage(self),
                                                     self.config.max_comunication_distance_upstream)

        if str(type(self)) == '<class \'EmergencyVehicle.EmergencyVehicle\'>':
            self.is_emergency = True

        for r in responses:
            if isinstance(r, Message.ResponseEmergencyMessage):
                self.is_emergency = True

        if self.__should_yield(response) or str(type(response.sender)) == '<class \'EmergencyVehicle.EmergencyVehicle\'>' :
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
        if self.id == "up_47":
            print("uy")
        if str(type(self)) == '<class \'FlawVehicle.FlawVehicle\'>':
            self.is_flaw = True
        else: # Just send a message if is not a flaw
            # First verify if we should be yielding or should resume according to the basic rules
            responses = self.lane.send_message_in_radius(Message.RequestEmergencyMessage(self),
                                                         self.config.max_comunication_distance_upstream)
            for r in responses:
                if isinstance(r, Message.ResponseEmergencyMessage):
                    self.is_emergency = True

        if str(type(self)) == '<class \'EmergencyVehicle.EmergencyVehicle\'>':
            #print("mi clase es: " + str(type(self)))
            self.is_emergency = True
        
        should_yield = self.__should_yield(response)
        if self.id == "right_50" or self.id == "right_45":
            print("HMM")
        if should_yield and not self.is_emergency:
            # We are yielding, stop the vehicle if possible
            self.__yield()
            # Check if we should start gaining priority either by time or convoy
            convoy_completed, last_vehicle = self._convoy_completed()
            if response is not None and convoy_completed:
                if self.id == "right_49":
                    print("uy")
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
                            type(response.sender)) == '<class \'Vehicle.Vehicle\'>' and self.decision != False:
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

    def waiting_time(self):
        if self.waiting_since_second == -1:
            return 0
        return self.config.current_time_seconds - self.waiting_since_second

    def opposite_flaw_yield_time(self):
        if self.opposite_flaw_yielding_since_second == -1:
            return 0
        return self.config.current_time_seconds - self.opposite_flaw_yielding_since_second

    def __process_gaining_priority(self, response) -> bool:

        if self.id == "down_42":
            print("uy")
        if self.id == "right_278_flaw":
            print("uy")
        if self.is_emergency and response.sender.is_emergency and self.decision is None:
            self.decision = bool(random.randint(0, 1))
            response.sender.decision = not self.decision
        elif self.is_emergency and not response.sender.is_emergency:
            self.decision = None
        elif not self.is_emergency and response.sender.is_emergency:
            self.decision = False
        elif self.should_wait:
            self.decision = False
            response.sender.decision = True
        elif response.sender.should_wait:
            self.decision = True
            response.sender.decision = False
        elif self.is_flaw and response.sender.state != Vehicle_State.YIELDING and response.sender.state != Vehicle_State.WAITING and not response.sender.is_flaw:
            self.decision = False
            response.sender.decision = True
        #elif self.decision is None and self.is_flaw and not response.sender.is_flaw:
        #    self.decision = False
        elif self.state == Vehicle_State.GAINING_PRIORITY and response.sender.state == Vehicle_State.GAINING_PRIORITY:
            self.decision = bool(random.randint(0, 1))
            response.sender.decision = not self.decision
        elif self.decision is None and self.is_flaw and response.sender.is_flaw:
            self.decision = bool(random.randint(0, 1))
            response.sender.decision = not self.decision
        elif self.decision is None and self.is_flaw:
            self.decision = False
            response.sender.decision = True




        if self.decision == True or self.decision is None:
           # print("Veh, " + self.id, " Gaining priority, Soy prioridad? ", self.is_emergency, " decision: ", self.decision)
            self.state = Vehicle_State.GAINING_PRIORITY
        else:
            if self.is_flaw:
                self.__waiting()
            else:
                self.state = Vehicle_State.YIELDING
            #self.__resume()
            return True

        if self.__should_yield(response):
            # Do not resume yet but start exchanging messages to gain priority

            if self.is_flaw:
                responses = self.lane.send_perception_opposite_leader_in_radius(Message.PriorityRequiredMessage(self), self.config.max_perception_distance_between_leaders)            
            else:
                responses = self.lane.send_message_opposite_leader_in_radius(Message.PriorityRequiredMessage(self), self.config.max_comunication_distance_between_leaders)            
            # If any of the responses indicate a non yielding vehicle continue in this state and try again in next step
            self.log.debug(self, "priority requested. Responses:")
            for r in responses:
                self.log.debug(self, r.sender,type(r))
                if type(r) is Message.YieldingNotPossibleMessage:
                    # At least one vehicle can not yield, try again later
                    return True
            #self.__resume()
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
        if self.id == "right_85":
            print("uy")
        if self.id == "down_36":
            print("uy")
        if self.should_wait:
            return True
        if self.is_flaw and not response.sender.should_wait:
            print(self.id, "FALLA VA A PARAR")
            return True
        if not self.__can_stop():
            # We can not stop in time, do not try to yield
            self.log.debug(self, " not yielding, too close to brake")
            if not response.can_brake:
                self.log.info(self, " WARNING, NEITHER VEHICLES CAN BRAKE!", response)
            return False

        if self.id == "right_81":
            print("uy")

        if response.sender.is_flaw:
            self.handle_flaw_opposite_leader()
            
        if response.sender.is_flaw and not self.should_wait:
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

        if type(message) is Message.RequestNextLastFollowerMessage:
            return self.__process_request_next_last_follower_message(message)

        #print(self)

        return

    def handle_flaw_opposite_leader(self):

        if self.id == "right_50" or self.id == "right_45":
            print("HMM")
        upstream_responses = self.lane.send_message_in_radius(Message.RequestFollowerMessage(self),
                                                              self.config.max_comunication_distance_upstream)
        if len(upstream_responses) > 0:
            next_leader = upstream_responses[0].sender
            if self.opposite_flaw_yielding_since_second == -1:
                self.opposite_flaw_yielding_since_second = self.config.current_time_seconds
            init_waiting = self.opposite_flaw_yielding_since_second
            next_leader.opposite_flaw_yielding_since_second = init_waiting
            if self.lane.last_vehicle_convoy is not None and self.lane.last_vehicle_convoy == self\
                    or self.opposite_flaw_yield_time() > self.config.flaw_timeout_in_seconds and not "flaw" in next_leader.id:
                next_leader.should_wait = True
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
        if str(type(self)) == '<class \'EmergencyVehicle.EmergencyVehicle\'>':

            #print("YO, una emergencia soy:"+str(type(self))) #TODO:
            return Message.ResponseEmergencyMessage(self)
        return Message.ResponseNotEmergencyMessage(self)

    def __process_request_next_last_follower_message(self, message):
        return Message.ResponseNextLastFollowerMessage(self, self.lane_position, self.__is_yielding() or (self.speed < 4.5), self._yield_time(), self.__can_stop())

    def __yield(self) -> bool:
        if self.id == 'down3_171' or self.id == 'left2_3041':
            print("Voy a fallar")
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

    def __waiting(self) -> bool:
        self.state = Vehicle_State.WAITING
        self.waiting_since_second = self.config.current_time_seconds
        return True

    def __can_stop(self):
        if self.speed == 0.0 or self.__is_yielding() or self.__is_gaining_priority():
            return True
        min_breaking_distance = self.__min_breaking_distance()
        can_stop = self.distance_to_intersection - self.config.min_braking_distance_to_intersection >= min_breaking_distance
        return can_stop

    def __min_breaking_distance(self):
        if self.speed == 0.0:
            return 0
        min_stop_time = self.__min_breaking_time()
        return max(self.speed, self.speed * min_stop_time + (-1 * self.max_decceleration * min_stop_time ** 2)/2)

    def __min_breaking_time(self):
        """Calculates the minimum time that the vehicles needs to stop given its maximum deceleration and a base time

        Args:
            speed (float): Current speed of the vehicle

        Returns:
            float: Number of seconds expected to stop this car
        """
        return self.speed / self.max_decceleration + self.config.stopping_time_delay

    def __resume(self):

        self.waiting_since_second = -1
        if self.__is_yielding():
            if (self.id == "left_24_flaw"):
                print("SOY 22")
            try:
                traci.vehicle.resume(self.id)
                self.log.debug(self, "RESUME - distance to instersection", self.distance_to_intersection)
                if "flaw" not in self.id:
                    self.state = Vehicle_State.AUTO
                self.yielding_since_seconds = -1

                # traci.vehicle.setSpeed(self.id, -1)
            except Exception as err:
                print(err)
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

