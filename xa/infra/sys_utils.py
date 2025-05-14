import psutil
import platform
from typing import Dict, Any, Optional
import re
import subprocess

"""
This file contains system utilities
These utilities are used to get and manage system information and states
"""

import socket
import random as random


class Random(random.Random):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            assert len(args) + len(kwargs) > 0, "Seed must be provided for the Random object!"
            cls._instance = super(Random, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, seed=None):
        super().__init__(seed)
        self.seed(seed)
    
    def __getattribute__(self, name):
        return super().__getattribute__(name)


def get_cluster_config() -> dict:
    """
    Explore the network and get system specs for all hosts/devices.
    
    Returns:
        dict: A dictionary containing the hosts and their configurations with the following structure:
        {
            'hostname': str,
            'platform': str,
            'architecture': tuple,
            'cpu_count': int,
            'memory_total': int,  # In bytes
            'devices': list[dict]  # List of detected devices (GPUs, accelerators, etc.)
        }
    """
    
    sys_info = {
        'hostname': platform.node(),
        'platform': platform.system(),
        'architecture': platform.architecture(),
        'cpu_count': psutil.cpu_count(logical=True),
        'memory_total': psutil.virtual_memory().total,
        'devices': [] #TODO needs to be defined
    }
    
    return sys_info


def _parse_hl_smi_output(output: str) -> dict:
    """
    Parse the HL-SMI output and convert it into a dictionary.
    
    Args:
        output (str): The HL-SMI output as a string.
    
    Returns:
        dict: A dictionary containing the parsed HL-SMI data.
    """
    data = {}
    aips = re.split(r'\[\d+\] AIP', output)
    for aip in aips[1:]:
        lines = aip.split('\n')
        key = lines[0].strip()
        data[key] = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                data[key][k.strip()] = v.strip()
    return data


def get_accelerator_stats(node: Optional[str] = None) -> dict:
    """
    Get the accelerator stats for the expected host node.
    
    Args:
        node (str, optional): The hostname or IP of the target node.
                              If None, gets stats for the local machine.
    
    Returns:
        dict: A dictionary containing the accelerator stats.
    """
    # Execute the hl-smi command and capture the output
    result = subprocess.run(['sudo', 'hl-smi', '-q'], capture_output=True, text=True)
    hl_smi_output = result.stdout
    
    return _parse_hl_smi_output(hl_smi_output)


def get_system_stats(node) -> dict:
    """
    Get the system stats for the expected host node.
    
    Args:
        node (str, optional): The hostname or IP of the target node.
                            If None, gets stats for the local machine.
    
    Returns:
        dict: A dictionary containing the system stats with the following structure:
        {
            'cpu': dict,      # CPU statistics
            'memory': dict,   # Memory statistics
            'disk': dict,     # Disk statistics
            'network': dict   # Network statistics
        }
    """

    sys_stats = {
        'cpu': {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            'load_avg': psutil.getloadavg()
        },
        'memory': psutil.virtual_memory()._asdict(),
        'disk': {
            'usage': {path: psutil.disk_usage(path)._asdict() 
                     for path in psutil.disk_partitions()},
            'io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
        },
        'network': {
            'interfaces': psutil.net_if_addrs(),
            'io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        }
    }
    
    return sys_stats


def get_system_id() -> str:
    # get the system id
    # return the hostname of the system
    return socket.gethostname()
