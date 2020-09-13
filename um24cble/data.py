from .enums import ChargeMode
from .enums import Screen 

import dataclasses
import typing

@dataclasses.dataclass
class Report:
    @dataclasses.dataclass
    class Measurement:
        @dataclasses.dataclass
        class Group:
            ampere_hours : float
            watt_hours : float
    
        @dataclasses.dataclass
        class Record:
            ampere_hours : float
            watt_hours : float
            recorded_time_in_seconds : int
            is_recording : bool

        voltage_in_volt : float
        current_in_ampere : float
        power_in_watt : float
        temperature_in_celsius : float
        temperature_in_fahrenheit : float
        resistance_in_ohm : float
        usb_d_plus_in_volt : float
        usb_d_minus_in_volt : float
        charge_mode : ChargeMode
        groups : typing.Sequence[Group]
        record : Record
    
    
    @dataclasses.dataclass
    class Settings:
        record_stop_current_in_ampere : float
        backlight_off_delay_in_minutes : int
        backlight_level : int
        active_group : int
        active_screen : Screen

    measurement : Measurement
    settings : Settings

