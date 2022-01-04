
class Message:

    def __init__(self, sender):
        self.sender = sender

    def __str__(self):
        return f"Message type: {type(self).__name__} from {self.sender}"

    def __repr__(self):
        return f"Message type: {type(self).__name__} from {self.sender}"

class RequestFollowerMessage(Message):

    def __init__(self, sender):
        Message.__init__(self, sender)
            
class ResponseFollowerMessage(Message):

    def __init__(self, sender, detected_vehicles = 1):
        Message.__init__(self, sender)
        self.detected_vehicles = detected_vehicles


class RequestEmergencyMessage(Message):

    def __init__(self, sender):
        Message.__init__(self, sender)


class ResponseEmergencyMessage(Message):

    def __init__(self, sender, detected_vehicles=1):
        Message.__init__(self, sender)
        self.detected_vehicles = detected_vehicles



class ResponseNotEmergencyMessage(Message):

    def __init__(self, sender, detected_vehicles=1):
        Message.__init__(self, sender)
        self.detected_vehicles = detected_vehicles


class PriorityRequiredMessage(Message):

    def __init__(self, sender):
        Message.__init__(self, sender)

class SlowDownMessage(Message):

    def __init__(self, vehicle, time):
        Message.__init__(self, vehicle)
        self.time = time

class YieldingMessage(Message):

    def __init__(self, vehicle):
        Message.__init__(self, vehicle)

class YieldingNotPossibleMessage(Message):

    def __init__(self, vehicle):
        Message.__init__(self, vehicle)

class OppositeLeaderMessage(Message):

    def __init__(self, vehicle, distance_to_intersection, wait_time):
        Message.__init__(self, vehicle)
        self.distance_to_intersection = distance_to_intersection
        self.wait_time = wait_time

class NextLastFollowerMessage(Message):

    def __init__(self, vehicle, distance_to_intersection, wait_time):
        Message.__init__(self, vehicle)
        self.distance_to_intersection = distance_to_intersection
        self.wait_time = wait_time

class RequestOppositeLeaderMessage(OppositeLeaderMessage):

    def __init__(self, vehicle, distance_to_intersection, wait_time):
        OppositeLeaderMessage.__init__(self, vehicle, distance_to_intersection, wait_time)

class RequestNextLastFollowerMessage(OppositeLeaderMessage):

    def __init__(self, vehicle, distance_to_intersection, wait_time):
        NextLastFollowerMessage.__init__(self, vehicle, distance_to_intersection, wait_time)

class ResponseOppositeLeaderMessage(OppositeLeaderMessage):

    def __init__(self, vehicle, distance_to_intersection, stopped, wait_time, can_brake):
        OppositeLeaderMessage.__init__(self, vehicle, distance_to_intersection, wait_time)
        self.stopped = stopped
        self.can_brake = can_brake

    def __str__(self):
        return f"{OppositeLeaderMessage.__str__(self)} - stopped? {self.stopped} - can_brake? {self.can_brake}"

    def __repr__(self):
        return f"{OppositeLeaderMessage.__repr__(self)} - stopped? {self.stopped} - can_brake? {self.can_brake}"
