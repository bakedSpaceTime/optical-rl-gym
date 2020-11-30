from optical_rl_gym.utils import Path
from optical_rl_gym.envs.rmcsa_env import RMCSAEnv


class CoreAllocation():

    LOWER_USAGE =.25
    MIDDLE_USAGE = .50
    UPPER_USAGE = .75

    def __init__(self, env: RMCSAEnv):
        self.env = env
        self._last_allocated_core = -1
        self._core_usage_lower = .25
        self._core_usage_middle = .50
        self._core_usage_upper = .75

    @property
    def last_allocated_core(self):
        return self._last_allocated_core

    @last_allocated_core.setter
    def last_allocated_core(self, core_num):
        if core_num not in range(self.env.num_spatial_resources):
            raise ValueError(f"Invalid Core number. Core must be in range of RMCSAEnv.num_spatial_resources")
        else:
            self._last_allocated_core = core_num

    def round_robin(self, env: RMCSAEnv):
        for cur_core in self._rr_core_range_list():
            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                num_slots = self.env.get_number_slots(path)

                for slot in range(self.env.num_spectrum_resources):
                    if self.env.is_path_free(cur_core, path, slot, num_slots):
                        self.last_allocated_core = cur_core
                        return [cur_core, path_index, slot]
        
        self.last_allocated_core = env.num_spatial_resources - 1
        return [self.env.num_spatial_resources, self.env.topology.graph['k_paths'], self.env.topology.graph['num_spectrum_resources']]

    def slot_based(self, env: RMCSAEnv):
        for core_set in self._cores_ordered_by_slots_used():
            core, path_index = core_set[0], core_set[1]
            path = self._path_from_index(path_index)
            for slot in range(self.env.num_spectrum_resources):
                num_slots = self.env.get_number_slots(path)
                if self.env.is_path_free(core, path, slot, num_slots):
                    return (core, path_index, slot)
        return [self.env.num_spatial_resources, self.env.topology.graph['k_paths'], self.env.topology.graph['num_spectrum_resources']]
    
    def slot_based_round_robin(self, env: RMCSAEnv):
        cores = self._rr_core_range_list()
        # print(cores, "1")
        for cur_core in self._rr_core_range_list():
            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                slot_usage = self._slot_usage(cur_core, path)
                # print(slot_usage, cur_core, path_index)
                if slot_usage >= self._core_usage_lower:
                    if cur_core in cores:
                        cores.remove(cur_core)
                    if cores == []:
                        # print("All Past Lower")
                        cores = self._rr_core_range_list()
                        # print(cores, "2")
                        for cur_core in self._rr_core_range_list():
                            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                                slot_usage = self._slot_usage(cur_core, path)
                                # print(slot_usage, cur_core, path_index)
                                if slot_usage >= self._core_usage_middle:
                                    if cur_core in cores:
                                        cores.remove(cur_core)
                                    if cores == []:
                                        # print("All Past Middle")
                                        cores = self._rr_core_range_list()
                                        # print(cores, "3")
                                        for cur_core in self._rr_core_range_list():
                                            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                                                slot_usage = self._slot_usage(cur_core, path)
                                                # print(slot_usage, cur_core, path_index)
                                                if slot_usage >= self._core_usage_upper:
                                                    try:
                                                        cores.remove(cur_core)
                                                    except ValueError as e:
                                                        if cores == []:
                                                            # print("All Past Upper")
                                                            cores = self._rr_core_range_list()
                                                            # print(cores, "5")

        # print(cores, "5")
        for core in cores:
            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                num_slots = self.env.get_number_slots(path)
                path = self._path_from_index(path_index)
                for slot in range(self.env.num_spectrum_resources):
                    if self.env.is_path_free(core, path, slot, num_slots):
                        self.last_allocated_core = core
                        # print([core, path_index, slot, slot_usage])
                        # print([core, path_index, slot], "connection made")
                        return [core, path_index, slot]
        # print("no connection made")
        self.last_allocated_core = env.num_spatial_resources - 1
        return [self.env.num_spatial_resources, self.env.topology.graph['k_paths'], self.env.topology.graph['num_spectrum_resources']]    

    def slot_based_round_robin2(self, env: RMCSAEnv):
        for core_set in self._choose_usage_limit_cores():
            core, path_index = core_set[0], core_set[1]
            path = self._path_from_index(path_index)
            num_slots = self.env.get_number_slots(path)
            for slot in range(self.env.num_spectrum_resources):
                if self.env.is_path_free(core, path, slot, num_slots):
                    return (core, path_index, slot)
        return [self.env.num_spatial_resources, self.env.topology.graph['k_paths'], self.env.topology.graph['num_spectrum_resources']]

    def _slot_usage(self, core: int, path: Path) -> [float]:
        cur_used = self._used_slots(core, path)
        num_False = [ slot[1] for slot in cur_used ].count(False)
        num_FalsePerLink = num_False / (len(path.node_list) - 1)
        slot_usage = num_FalsePerLink / self.env.num_spectrum_resources
        true_slot_usage = 1 - slot_usage
        return true_slot_usage

    def _choose_usage_limit_cores(self):
        core_lists = [
            self._lower_usage_cores(),
            self._middle_usage_cores(),
            self._upper_usage_cores(),
        ]
        # print(core_lists)
        min_len = float('inf')
        min_list = []
        for core_list in core_lists:
            if 0 < len(core_list) < min_len:
                min_list = core_list
        # print(min_list)
        return min_list

    def _lower_usage_cores(self):
        lower_usage_core_sets = []
        for core_set in self._cores_ordered_by_slots_used():
            # print(core_set)
            if core_set[2] <= self.LOWER_USAGE:
                lower_usage_core_sets.append(core_set)
        
        return lower_usage_core_sets
    
    def _middle_usage_cores(self):
        middle_usage_cores = []
        for core_set in self._cores_ordered_by_slots_used():
            if self.LOWER_USAGE < core_set[2] < self.UPPER_USAGE:
                middle_usage_cores.append(core_set)
        
        return middle_usage_cores
    
    def _upper_usage_cores(self):
        upper_usage_cores = []
        for core_set in self._cores_ordered_by_slots_used():
            if core_set[2] >= self.UPPER_USAGE:
                upper_usage_cores.append(core_set)
        
        return upper_usage_cores

    def _rr_core_range_list(self) -> [int]:
        return list(range(self.last_allocated_core + 1, self.env.num_spatial_resources)) + list(range(self.last_allocated_core + 1))

    def _path_from_index(self, path_index):
        return self.env.k_shortest_paths[self.env.service.source, self.env.service.destination][path_index]

    def _cores_ordered_by_slots_used(self):
        slot_usage = []
        for cur_core in range(self.env.num_spatial_resources):
            for path_index, path in enumerate(self.env.k_shortest_paths[self.env.service.source, self.env.service.destination]):
                cur_used = self._used_slots(cur_core, path)
                num_False = [ slot[1] for slot in cur_used ].count(False)
                num_FalsePerLink = num_False / (len(path.node_list) - 1)
                slot_usage_avg = num_FalsePerLink / self.env.num_spectrum_resources
                slot_usage.append((cur_core, path_index, slot_usage_avg))

        # print(sorted(slot_usage, key=lambda tup: tup[2]), len (slot_usage))
        return sorted(slot_usage, key=lambda tup: tup[2])
                
    def _used_slots(self, core: int, path: Path) -> [(int,bool)]:
        used_slots = []
        for i in range(len(path.node_list) - 1):
            for slot_num in range(self.env.num_spectrum_resources):
                used_slots.append(
                    (
                        slot_num,
                        self.env.topology.graph['available_slots']
                            [core, self.env.topology[path.node_list[i]][path.node_list[i + 1]]['index'],
                            slot_num] == 0
                    )
                )
        return used_slots