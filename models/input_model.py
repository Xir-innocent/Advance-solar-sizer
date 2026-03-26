from dataclasses import dataclass
from typing import List

@dataclass
class Appliance:
    name: str
    power: float
    hours: float
    category: str  # day, night, 24h
    surge_factor: float = 1
    duty_cycle: float = 1

@dataclass
class SystemInput:
    appliances: List[Appliance]
    load_drop: float
    backup_hours: float
    battery_type: str
    panel_rating: float
    location_psh: float
    cable_length: float