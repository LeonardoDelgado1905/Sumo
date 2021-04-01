import Lane
import traci
from SimStateAndConfig import SimStateAndConfig

class Simulation:

    def __init__(self):
        self.lanes = dict()
        self.config = SimStateAndConfig()
        # Initialize the lanes
        lane_ids = traci.lane.getIDList()
        for lane_id in lane_ids:
            # Only consider lanes over 40 meters in length, this serves to remove lanes in intersections
            lane_length = traci.lane.getLength(lane_id)
            if lane_length > 40:
                self.lanes[lane_id] = Lane.Lane(lane_id, lane_length, self.config)
        # The lanes are ready, let each of them figure out their adjacent lanes
        plain_lanes = self.lanes.values()
        for lane in plain_lanes:
            lane.find_adjacent_lanes(plain_lanes)

    def step(self, current_step):
        self.config.current_step = current_step
        self.config.current_time_seconds = traci.simulation.getTime()
        # Send all lanes the update
        for lane_id in self.lanes:
            self.lanes[lane_id].step(current_step)
