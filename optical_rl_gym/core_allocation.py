from optical_rl_gym.utils import Path
from optical_rl_gym.envs.rmcsa_env import RMCSAEnv


class CoreAllocation():

    def __init__(self, env: RMCSAEnv):
        self.env = env
        self._last_allocated_core = -1

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
        
        self.last_allocated_core = env.num_spatial_resources
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
                slot_usage.append((cur_core, path_index, num_False))

        return sorted(slot_usage, key=lambda tup: tup[2])
                
    def _used_slots(self, core: int, path: Path) -> [bool]:
        used_slots = []
        for i in range(len(path.node_list) - 1):
            for slot_num in range(self.env.num_spectrum_resources):
                used_slots.append(
                    (
                        slot_num,
                        self.env.topology.graph['available_slots'][
                            core,
                            self.env.topology[path.node_list[i]][path.node_list[i + 1]]['index'],
                            slot_num
                        ] == 0
                    )
                )
        return used_slots