from Vehicle import Vehicle
from SimStateAndConfig import SimStateAndConfig
from Message import ResponseFollowerMessage
import traci
from Log import Log

class EmergencyVehicle(Vehicle):

    def __init__(self, id, lane, config : SimStateAndConfig):
        Vehicle.__init__(self, id, lane, config)
        self.log = Log(config)



