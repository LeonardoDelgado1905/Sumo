
class SimStateAndConfig:

    def __init__(self):
        self.current_step = -1
        self.current_time_seconds = -1
        self.max_distance_between_adjacent_lanes = 20
        self.start_negotiating_at_distance_from_intersection = 50
        self.start_perception_at_distance_from_intersection = 10
        self.max_comunication_distance_between_leaders = 150
        self.max_perception_distance_between_leaders = 10
        self.max_comunication_distance_upstream = 60
        self.min_yield_timeout_in_seconds = 20
        self.yield_timeout_in_seconds = 150
        self.min_convoy_size = 8
        self.stopping_time_delay = 1
        self.min_braking_distance_to_intersection = 1
        self.log_info = False
        self.log_debug = False
        self.log_filter_regex = None #"right_(127|124|125)|down_(119)"
