from bluepy import btle

import enum
import sys

UM24C_SERVICE_UUID            = '0000FFE0-0000-1000-8000-00805F9B34FB'
UM24C_CHARACTERISTICS_UUID    = '0000FFE1-0000-1000-8000-00805F9B34FB'
UM24C_DESCRIPTOR_UUID         = '00002902-0000-1000-8000-00805F9B34FB'


class ChargeMode(enum.Enum):
    UNKNOWN = 0
    QC2_0 = 1
    QC3_0 = 2


class Screen(enum.Enum):
    MEASUREMENT_MAIN_INTERFACE = 0
    QUICK_CHARGE_RECOGNITION_INTERFACE = 1
    DATA_RECORDING_INTERFACE = 2
    WIRE_IMPEDANCE_MEASUREMENT_INTERFACE = 3
    VOLTAGE_GRAPHING_INTERFACE = 4
    CURRENT_GRAPHING_INTERFACE = 5
    SETTINGS_INTERFACE = 6


class ReportMeasurementGroup:
    def __init__(self, ampere_hours, watt_hours):
        self.ampere_hours = ampere_hours
        self.watt_hours = watt_hours

    def __str__(self):
        return self.__class__.__name__ + "(ampere_hours=" + str(self.ampere_hours) + ", watt_hours=" + str(self.watt_hours) + ")"


class ReportMeasurementRecord:
    def __init__(self, ampere_hours, watt_hours, recorded_time_in_seconds, is_recording):
        self.ampere_hours = ampere_hours
        self.watt_hours = watt_hours
        self.recorded_time_in_seconds = recorded_time_in_seconds
        self.is_recording = is_recording

    def __str__(self):
        return self.__class__.__name__ + "(ampere_hours=" + str(self.ampere_hours) + ", watt_hours=" + str(self.watt_hours) + ", recorded_time_in_seconds=" + str(self.recorded_time_in_seconds) + ", is_recording=" + str(self.is_recording) + ")"


class ReportMeasurement:
    def __init__(self, voltage_in_volt, current_in_ampere, power_in_watt, temperature_in_celsius, temperature_in_fahrenheit, resistance_in_ohm, usb_d_plus_in_volt, usb_d_minus_in_volt, charge_mode, active_group, groups, record):
        self.voltage_in_volt = voltage_in_volt
        self.current_in_ampere = current_in_ampere
        self.power_in_watt = power_in_watt
        self.temperature_in_celsius = temperature_in_celsius
        self.temperature_in_fahrenheit = temperature_in_fahrenheit
        self.resistance_in_ohm = resistance_in_ohm
        self.usb_d_plus_in_volt = usb_d_plus_in_volt
        self.usb_d_minus_in_volt = usb_d_minus_in_volt
        self.charge_mode = charge_mode
        self.active_group = active_group

        self.groups = []
        for group in groups:
            self.groups.append(group)

        self.record = record

    def __str__(self):
        return self.__class__.__name__ + "(voltage_in_volt=" + str(self.voltage_in_volt) + ", current_in_ampere=" + str(self.current_in_ampere) + ", power_in_watt=" + str(self.power_in_watt) + ", temperature_in_celsius=" + str(self.temperature_in_celsius) + ", temperature_in_fahrenheit=" + str(self.temperature_in_fahrenheit) + ", resistance_in_ohm=" + str(self.resistance_in_ohm) + ", usb_d_plus_in_volt=" + str(self.usb_d_plus_in_volt) + ", usb_d_minus_in_volt=" + str(self.usb_d_minus_in_volt) + ", charge_mode=" + str(self.charge_mode) + ", active_group=" + str(self.active_group) + ", groups=" + str(list(map(lambda x: str(x), self.groups))) + ", record=" + str(self.record) + ")"


class ReportSettings:
    def __init__(self, record_stop_current_in_ampere, backlight_off_delay_in_minutes, backlight_level, active_screen):
        self.record_stop_current_in_ampere = record_stop_current_in_ampere
        self.backlight_off_delay_in_minutes = backlight_off_delay_in_minutes
        self.backlight_level = backlight_level
        self.active_screen = active_screen

    def __str__(self):
        return self.__class__.__name__ + "(record_stop_current_in_ampere=" + str(self.record_stop_current_in_ampere) + ", backlight_off_delay_in_minutes=" + str(self.backlight_off_delay_in_minutes) + ", backlight_level=" + str(self.backlight_level) + ", active_screen=" + str(self.active_screen) + ")"


class ReportResponse:
    def __init__(self, measurement, settings):
        self.measurement = measurement
        self.settings = settings

    def __str__(self):
        return self.__class__.__name__ + "(measurement=" + str(self.measurement) + ", settings=" + str(self.settings) + ")"


class UM24CBLEDelegate(btle.DefaultDelegate):
    def __init__(self, debug=False):
        self.debug = False
        if debug:
            self.debug = True

        self.data = b''

    def handleNotification(self, cHandle, data):
        if self.debug:
            print("Received data on cHandle=" + str(cHandle) + ": " + str(data), file=sys.stderr)
        self.data += data

    def consumeNotification(self):
        data = self.data
        self.data = b''

        return data

class UM24CBLE:
    def __init__(self, device_address=None, hci_device=None, debug=False):
        self.device_address=None
        self.debug = False
        self.hci_device='hci0'

        if hci_device:
            self.hci_device = hci_device

        if debug:
            self.debug = debug

        self.delegate = None
        self.peripheral = None
        self.characteristics = None
        self.descriptor = None

        if device_address:
            self.connect(device_address)

    def _connect(self, device_address):
        self.delegate = UM24CBLEDelegate(self.debug)
        self.peripheral = btle.Peripheral(deviceAddr=device_address, iface=self.hci_device.replace('hci', '')).withDelegate(self.delegate)

        if not self.peripheral:
            self._disconnect()

        self.characteristics = self.peripheral.getCharacteristics(uuid=UM24C_CHARACTERISTICS_UUID)[0]
        self.descriptor = self.characteristics.getDescriptors(forUUID=UM24C_DESCRIPTOR_UUID)[0]

        if not self.characteristics or not self.descriptor:
            self._disconnect()

        return self._is_connected()

    def _disconnect(self):
        self.delegate = None
        if not self.peripheral is None:
            self.peripheral.disconnect()
            self.peripheral = None
        self.characteristics = None
        self.descriptor = None

    def _is_connected(self):
        if self.delegate is None:
            return False
        if self.characteristics is None:
            return False
        if self.descriptor is None:
            return False
        if self.peripheral is None:
            return False
        if not self.peripheral.getState() == 'conn':
            return False

        return True

    def connect(self, device_address=None):
        if not device_address:
            device_address = self.device_address

        if not device_address:
            return False

        self._disconnect()
        if not self._connect(device_address):
            return False

        self.device_address = device_address

        return True

    def read(self):    
        # subscribe to notifications
        self.descriptor.write(b'\x01\x00', withResponse=True)

        command = create_um24c_command(b'\xf0')
        self.characteristics.write(command, withResponse=True)
        while len(self.delegate.data) < 130:
            if not self.peripheral.waitForNotifications(timeout=10):
                break
            
        # unsubscribe from notifications
        self.descriptor.write(b'\x00\x00', withResponse=True)

        assert len(self.delegate.data) == 130

        data = self.delegate.consumeNotification()
        response = parse_report_response(data)

        return response

    def change_record_stop_current(self, ampere):
        value = float(ampere)
        value = int(value*100)
        if value < 0 or value > 30:
            raise Exception('Unsupported value for record stop current. Must be between 0.00 and 0.30 A')

        command = create_um24c_command((value + 0xb0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_level(self, level):
        value = int(level)
        if value < 0 or value > 5:
            raise Exception('Unsupported value for backlight level. Must be between 0 and 5')

        command = create_um24c_command((value + 0xd0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_off_delay(self, minutes):
        value = int(minutes)
        if value < 0 or value > 15:
            raise Exception('Unsupported value for backlight off delay. Must be between 0 and 15 minutes')

        command = create_um24c_command((value + 0xe0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def button_next(self):
        command = create_um24c_command(b'\xf1')
        self.characteristics.write(command)

    def button_rotate(self):
        command = create_um24c_command(b'\xf2')
        self.characteristics.write(command)

    def button_group(self):
        command = create_um24c_command(b'\xf3')
        self.characteristics.write(command)

    def button_clear(self):
        command = create_um24c_command(b'\xf4')
        self.characteristics.write(command)


def checksum(message):
    return int(sum(message) & 0xff ^ 0x44).to_bytes(1, 'big')

def create_um24c_package_data(message_type, device_type, payload):
    message = message_type + device_type + payload
    return b'\xff\x55' + message + checksum(message)

def create_um24c_command(command):
    return create_um24c_package_data(b'\x11', b'\x03', command + b'\x00\x00\x00\x00')

def parse_report_response(data):
    groups = []
    for i in range(10):
        groups.append(
            ReportMeasurementGroup(
                ampere_hours=int.from_bytes(data[16 + i*8:20 + i*8], 'big') / 1000,
                watt_hours=int.from_bytes(data[20 + i*8:24 + i*8], 'big') / 1000))

    record = ReportMeasurementRecord(
        ampere_hours=int.from_bytes(data[102:106], 'big') / 1000,
        watt_hours=int.from_bytes(data[106:110], 'big') / 1000,
        recorded_time_in_seconds=int.from_bytes(data[112:116], 'big'),
        is_recording=True if int.from_bytes(data[116:118], 'big') > 0 else False)

    measurement = ReportMeasurement(
        voltage_in_volt=int.from_bytes(data[2:4], 'big') / 100,
        current_in_ampere=int.from_bytes(data[4:6], 'big') / 1000,
        power_in_watt=int.from_bytes(data[6:10], 'big') / 1000,
        temperature_in_celsius=int.from_bytes(data[10:12], 'big'),
        temperature_in_fahrenheit=int.from_bytes(data[12:14], 'big'),
        resistance_in_ohm=int.from_bytes(data[122:126], 'big') / 10,
        usb_d_plus_in_volt=int.from_bytes(data[96:98], 'big') / 100,
        usb_d_minus_in_volt=int.from_bytes(data[98:100], 'big') / 100,
        charge_mode=ChargeMode(int.from_bytes(data[100:102], 'big')),
        active_group=int.from_bytes(data[15:16], 'big'),
        groups=groups,
        record=record)

    settings = ReportSettings(
        record_stop_current_in_ampere=int.from_bytes(data[110:112], 'big') / 100,
        backlight_off_delay_in_minutes=int.from_bytes(data[118:120], 'big'),
        backlight_level=int.from_bytes(data[120:122], 'big'),
        active_screen=Screen(int.from_bytes(data[126:128], 'big')))

    response = ReportResponse(measurement, settings)

    return response 
