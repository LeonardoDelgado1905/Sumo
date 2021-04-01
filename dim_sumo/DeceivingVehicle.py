from Vehicle import Vehicle
from SimStateAndConfig import SimStateAndConfig
from Message import ResponseFollowerMessage
import traci
from Log import Log

class DeceivingVehicle(Vehicle):

    def __init__(self, id, lane, config : SimStateAndConfig):
        Vehicle.__init__(self, id, lane, config)
        self.log = Log(config)

    def _convoy_completed(self):
        # Do not check for convoys unless we have been yielding for at least half the minimum time
        if self._yield_time() < self.config.min_yield_timeout_in_seconds/2:
            return False
        # Our deceiving strategy is to always consider the convoy completed after the min timeout is done
        self.log.info(self, "DECEIVING - Telling convoy is complete")
        traci.vehicle.setColor(self.id, (255,0,0) )
        return True

    def _build_follower_response_message(self):
        self.log.info(self, "DECEIVING - Manipulating convoy size")
        traci.vehicle.setColor(self.id, (255,127,80) )
        return ResponseFollowerMessage(self, self.config.min_convoy_size-1)


