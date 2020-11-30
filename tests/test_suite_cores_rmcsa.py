import gym
from optical_rl_gym.envs.rmcsa_env import shortest_path_first_fit, shortest_available_first_core_first_fit, \
    least_loaded_path_first_fit, SimpleMatrixObservation
from optical_rl_gym.utils import evaluate_heuristic, random_policy
from optical_rl_gym.core_allocation import CoreAllocation

import pickle
import logging
import numpy as np
import json
import os
from datetime import datetime


import matplotlib.pyplot as plt
logging.getLogger('rmsaenv').setLevel(logging.INFO)

DEFAULT_OUT_FILE = f'outdata-{str(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))}.json'

LOAD = 450
SEED = 20
EPISODES = 10
EPISODE_LENGTH = 1000 ########
NUM_SPATIAL_RESOURCES = 5
NUM_SPECTRUM_RESOURCES = 64
SPACIAL_RESOURCE_TEST_RANGE = range(3, 10) # Increase to range(3, 13)
LOAD_TEST_RANGE = range(100, 1500, 100) # Increase to range(100, 2500, 200)
TOPOLOGY_FILE_NAMES = {
    'default': '../examples/topologies/nsfnet_chen_eon_5-paths.h5',
    'germany': '../examples/topologies/germany50_eon_gnpy_5-paths.h5',
}

with open(TOPOLOGY_FILE_NAMES['default'], 'rb') as f:
    DEFAULT_TOPOLOGY = pickle.load(f)

def run_test(env_args, core_alloc_algorithm, test_variable, **kwargs):
    env_sap = gym.make('RMCSA-v0', **env_args)
    core_alloc = CoreAllocation(env_sap, core_alloc_algorithm)
    mean_reward_sap, std_reward_sap = evaluate_heuristic(env_sap, core_alloc.heuristic, n_eval_episodes=EPISODES)

    display_metrics(test_variable, mean_reward_sap, std_reward_sap, env_sap, core_alloc, **kwargs)
    json_file_dump(test_variable, mean_reward_sap, std_reward_sap, env_sap, core_alloc, **kwargs)


def display_metrics(test_variable, mean_reward_sap, std_reward_sap, env_sap, core_alloc, **kwargs):
    # Initial Metrics for Environment
    print('FP-RR:'.ljust(8), f'{mean_reward_sap:.4f}  {std_reward_sap:.4f}')
    print('Bit rate blocking:', (env_sap.episode_bit_rate_requested - env_sap.episode_bit_rate_provisioned) / env_sap.episode_bit_rate_requested)
    print('Request blocking:', (env_sap.episode_services_processed - env_sap.episode_services_accepted) / env_sap.episode_services_processed)

    # Additional Metrics For Environment
    print('Throughput:', env_sap.topology.graph['throughput'])
    print('Compactness:', env_sap.topology.graph['compactness'])
    print('Resource Utilization:', np.mean(env_sap.utilization))
    for key, value in env_sap.core_utilization.items():
        print('Utilization per core ({}): {}'.format(key, np.mean(env_sap.core_utilization[key])))
    print('Default Core Allocations:', core_alloc.default_allocation)
    print('Core Allocation Algorithm:', core_alloc._heuristic)
    print('Test Variable: ', test_variable)
    print("Other Details")
    for k,v in kwargs.items():
        print(f"\t{k} : {v}")
    print()

def json_file_dump(test_variable, mean_reward_sap, std_reward_sap, env_sap, core_alloc, file_name=DEFAULT_OUT_FILE, **kwargs):
    data = {
        'FP-RR:': f'{mean_reward_sap:.4f}  {std_reward_sap:.4f}',
        'Bit rate blocking:': (env_sap.episode_bit_rate_requested - env_sap.episode_bit_rate_provisioned) / env_sap.episode_bit_rate_requested,
        'Request blocking:': (env_sap.episode_services_processed - env_sap.episode_services_accepted) / env_sap.episode_services_processed,
        'Throughput:': env_sap.topology.graph['throughput'],
        'Resource Utilization:': np.mean(env_sap.utilization),
        'Utilization per core': { key: np.mean(env_sap.core_utilization[key]) for key, value in env_sap.core_utilization.items() },
        'Default Core Allocations:': core_alloc.default_allocation,
        'Core Allocation Algorithm:': core_alloc._heuristic,
        'Test Variable: ': test_variable,
        'Other Details': kwargs,
    }

    with open(DEFAULT_OUT_FILE, 'r') as f:
        file_data = json.load(f)
    file_data[core_alloc._heuristic][test_variable].append(data)
    with open(DEFAULT_OUT_FILE, 'w') as f:
        json.dump(file_data, f, indent=4)


def alter_spatial_resources(core_alloc_algorithm):
    test_var = 'Spacial Resources'
    with open(DEFAULT_OUT_FILE, 'r') as f:
        file_data = json.load(f)
    file_data[core_alloc_algorithm][test_var] = []
    with open(DEFAULT_OUT_FILE, 'w') as f:
        json.dump(file_data, f, indent=4)
    
    for num_spatial_resources in SPACIAL_RESOURCE_TEST_RANGE:
        env_args = dict(allow_rejection=True, mean_service_holding_time=25, topology=DEFAULT_TOPOLOGY, 
                            seed=SEED,load=LOAD, episode_length=EPISODE_LENGTH, 
                            num_spectrum_resources=NUM_SPECTRUM_RESOURCES, 
                            num_spatial_resources=num_spatial_resources
                        )

        run_test(env_args, core_alloc_algorithm, test_var, topology_name='default', load=LOAD, num_spatial_resources=num_spatial_resources)

def alter_topology(core_alloc_algorithm):
    test_var = 'Topology'
    with open(DEFAULT_OUT_FILE, 'r') as f:
        file_data = json.load(f)
    file_data[core_alloc_algorithm][test_var] = []
    with open(DEFAULT_OUT_FILE, 'w') as f:
        json.dump(file_data, f, indent=4)
    
    for name, file_name in TOPOLOGY_FILE_NAMES.items():

        with open(file_name, 'rb') as f:
            topology = pickle.load(f)
        env_args = dict(allow_rejection=True, mean_service_holding_time=25, topology=topology, 
                            seed=SEED,load=LOAD, episode_length=EPISODE_LENGTH, 
                            num_spectrum_resources=NUM_SPECTRUM_RESOURCES, 
                            num_spatial_resources=NUM_SPATIAL_RESOURCES
                        )
        run_test(env_args, core_alloc_algorithm, test_var, topology_name=name, load=LOAD, num_spatial_resources=NUM_SPATIAL_RESOURCES)
    

def alter_load(core_alloc_algorithm):
    test_var = 'Load'
    with open(DEFAULT_OUT_FILE, 'r') as f:
        file_data = json.load(f)
    file_data[core_alloc_algorithm][test_var] = []
    with open(DEFAULT_OUT_FILE, 'w') as f:
        json.dump(file_data, f, indent=4)

    for load in LOAD_TEST_RANGE:
        env_args = dict(allow_rejection=True, mean_service_holding_time=25, topology=DEFAULT_TOPOLOGY, 
                            seed=SEED,load=load, episode_length=EPISODE_LENGTH, 
                            num_spectrum_resources=NUM_SPECTRUM_RESOURCES, 
                            num_spatial_resources=NUM_SPATIAL_RESOURCES
                        )
        run_test(env_args, core_alloc_algorithm, test_var, topology_name='default',
            load=load, num_spatial_resources=NUM_SPATIAL_RESOURCES)

if __name__ == "__main__":
    if not os.path.exists(DEFAULT_OUT_FILE):
        with open(DEFAULT_OUT_FILE, 'w') as f:
            file_data = dict.fromkeys(CoreAllocation.HEURISTIC_NAMES, {})
            json.dump(file_data, f)

    for core_alloc_algorithm in CoreAllocation.HEURISTIC_NAMES:

        alter_spatial_resources(core_alloc_algorithm)
        alter_topology(core_alloc_algorithm)
        alter_load(core_alloc_algorithm)
    
    with open(DEFAULT_OUT_FILE, 'r') as f:
        data = json.load(f)
        print(f"Tests Complated.\n{len(data)} Tests Run")
        print(f"Results saved to {DEFAULT_OUT_FILE}")
