from .enums import ChargeMode
from .enums import Screen 
from .data import Report

from bluepy import btle

import sys

UM24C_SERVICE_UUID            = '0000FFE0-0000-1000-8000-00805F9B34FB'
UM24C_CHARACTERISTICS_UUID    = '0000FFE1-0000-1000-8000-00805F9B34FB'
UM24C_DESCRIPTOR_UUID         = '00002902-0000-1000-8000-00805F9B34FB'


class UM24CBLE:
    """Class to access a um24c device via bluetooth low energy."""

    class UM24CBLEDelegate(btle.DefaultDelegate):
        def __init__(self, debug: bool = False):
            self.debug = False
            if debug:
                self.debug = True
    
            self.data = b''
    
        def handleNotification(self, cHandle, data):
            if self.debug:
                print("Received data on cHandle=" + str(cHandle) + ": " + str(data), file=sys.stderr)
            self.data += data
    
        def consumeNotification(self) -> None:
            data = self.data
            self.data = b''
    
            return data

    def __init__(self, device_address: str = None, hci_device: str = None, debug: bool = False):
        """Creates an UM24CBLE instance and optionally connects to the given remote device.

        Parameters:
            device_address  - address of the remote device to connect to, i.e. '11:22:33:44:55:66'
            hci_device      - bluetooth device to use. Default: 'hci0'
            debug           - If set to true prints all received data to stderr
        """
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
        self.delegate = UM24CBLE.UM24CBLEDelegate(self.debug)
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

    def connect(self, device_address: str = None) -> bool:
        """Establishes a connection to the given remote device.
        
        Parameters:
            device_address  - address of the remote device to connect to, i.e. '11:22:33:44:55:66'
        """
        if not device_address:
            device_address = self.device_address

        if not device_address:
            return False

        self._disconnect()
        if not self._connect(device_address):
            return False

        self.device_address = device_address

        return True

    def disconnect(self):
        """Disconnects from the remote device."""
        self._disconnect()

    def read(self) -> Report:
        """Read current measurement and settings from the device."""
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

    def change_record_stop_current(self, ampere: float) -> None:
        """Change the value of current in ampere which stops the recording when deceeded.

        Parameters:
            ampere  - current in ampere
        """
        value = float(ampere)
        value = int(value*100)
        if value < 0 or value > 30:
            raise Exception('Unsupported value for record stop current. Must be between 0.00 and 0.30 A')

        command = create_um24c_command((value + 0xb0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_level(self, level: int) -> None:
        """Change backlight level.

        Parameters:
            level   - backlight level (0-5)
        """
        value = int(level)
        if value < 0 or value > 5:
            raise Exception('Unsupported value for backlight level. Must be between 0 and 5')

        command = create_um24c_command((value + 0xd0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_off_delay(self, minutes: int) -> None:
        """Change delay until the backlight is turned off.

        Parameters:
            minutes - amount of minutes
        """
        value = int(minutes)
        if value < 0 or value > 15:
            raise Exception('Unsupported value for backlight off delay. Must be between 0 and 15 minutes')

        command = create_um24c_command((value + 0xe0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def next_screen(self) -> None:
        """Show next screen."""
        command = create_um24c_command(b'\xf1')
        self.characteristics.write(command)

    def show_screen(self, screen: Screen):
        """Show specified screen."""
        screen = Screen(screen)
        report = self.read()

        while screen.value != report.settings.active_screen.value:
            count = screen.value - report.settings.active_screen.value
            if count < 0:
                count += 7

            for i in range(count):
                self.next_screen()

            report = self.read()

    def rotate_screen(self) -> None:
        """Rotate screen right."""
        command = create_um24c_command(b'\xf2')
        self.characteristics.write(command)

    def next_group(self) -> None:
        """Switch to next measurement group."""
        command = create_um24c_command(b'\xf3')
        self.characteristics.write(command)

    def change_group(self, group: int):
        """Change measurement group.

        Parameters:
            group - Index of measurement group (0-9)
        """
        report = self.read()

        while group != report.settings.active_group:
            count = group - report.settings.active_group
            if count < 0:
                count += 10

            for i in range(count):
                self.next_group()

            report = self.read()

    def clear(self) -> None:
        """Clear record and measurement groups."""
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
            Report.Measurement.Group(
                ampere_hours=int.from_bytes(data[16 + i*8:20 + i*8], 'big') / 1000,
                watt_hours=int.from_bytes(data[20 + i*8:24 + i*8], 'big') / 1000))

    record = Report.Measurement.Record(
        ampere_hours=int.from_bytes(data[102:106], 'big') / 1000,
        watt_hours=int.from_bytes(data[106:110], 'big') / 1000,
        recorded_time_in_seconds=int.from_bytes(data[112:116], 'big'),
        is_recording=True if int.from_bytes(data[116:118], 'big') > 0 else False)

    measurement = Report.Measurement(
        voltage_in_volt=int.from_bytes(data[2:4], 'big') / 100,
        current_in_ampere=int.from_bytes(data[4:6], 'big') / 1000,
        power_in_watt=int.from_bytes(data[6:10], 'big') / 1000,
        temperature_in_celsius=int.from_bytes(data[10:12], 'big'),
        temperature_in_fahrenheit=int.from_bytes(data[12:14], 'big'),
        resistance_in_ohm=int.from_bytes(data[122:126], 'big') / 10,
        usb_d_plus_in_volt=int.from_bytes(data[96:98], 'big') / 100,
        usb_d_minus_in_volt=int.from_bytes(data[98:100], 'big') / 100,
        charge_mode=ChargeMode(int.from_bytes(data[100:102], 'big')),
        groups=groups,
        record=record)

    settings = Report.Settings(
        record_stop_current_in_ampere=int.from_bytes(data[110:112], 'big') / 100,
        backlight_off_delay_in_minutes=int.from_bytes(data[118:120], 'big'),
        backlight_level=int.from_bytes(data[120:122], 'big'),
        active_group=int.from_bytes(data[15:16], 'big'),
        active_screen=Screen(int.from_bytes(data[126:128], 'big')))

    response = Report(measurement, settings)

    return response

