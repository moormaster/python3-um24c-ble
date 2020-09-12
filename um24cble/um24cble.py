from bluepy import btle

import sys

UM24C_SERVICE_UUID            = '0000FFE0-0000-1000-8000-00805F9B34FB'
UM24C_CHARACTERISTICS_UUID    = '0000FFE1-0000-1000-8000-00805F9B34FB'
UM24C_DESCRIPTOR_UUID         = '00002902-0000-1000-8000-00805F9B34FB'

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

        command = um24c_command(b'\xf0')
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

    def change_record_stop_current(ampere):
        value = float(ampere)
        value = int(value*100)
        if value < 0 or value > 30:
            raise Exception('Unsupported value for record stop current. Must be between 0.00 and 0.30 A')

        command = um24c_command((value + 0xb0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_level(level):
        value = int(level)
        if value < 0 or value > 5:
            raise Exception('Unsupported value for backlight level. Must be between 0 and 5')

        command = um24c_command((value + 0xd0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def change_backlight_off_delay(minutes):
        value = int(minutes)
        if value < 0 or value > 15:
            raise Exception('Unsupported value for backlight off delay. Must be between 0 and 15 minutes')

        command = um24c_command((value + 0xe0).to_bytes(1, 'big'))
        self.characteristics.write(command)

    def button_next():
        command = um24c_command(b'\xf1')
        self.characteristics.write(command)

    def button_rotate():
        command = um24c_command(b'\xf2')
        self.characteristics.write(command)

    def button_group():
        command = um24c_command(b'\xf3')
        self.characteristics.write(command)

    def button_clear():
        command = um24c_command(b'\xf4')
        self.characteristics.write(command)


def checksum(message):
    return int(sum(message) & 0xff ^ 0x44).to_bytes(1, 'big')

def um24c_package(message_type, device_type, payload):
    message = message_type + device_type + payload
    return b'\xff\x55' + message + checksum(message)

def um24c_command(command):
    return um24c_package(b'\x11', b'\x03', command + b'\x00\x00\x00\x00')

def parse_report_response(data):
    response = {}
    response["measurement"] = {}
    
    response["settings"] = {}
    settings = response["settings"]
    measurement = response["measurement"]

    measurement["voltage"] = { "volt": int.from_bytes(data[2:4], 'big') / 100 }
    measurement["current"] = { "ampere": int.from_bytes(data[4:6], 'big') / 1000 }
    measurement["power"] = { "watt": int.from_bytes(data[6:10], 'big') / 1000 }
    measurement["temperature"] = {}
    measurement["temperature"]["celsius"] = int.from_bytes(data[10:12], 'big')
    measurement["temperature"]["fahrenheit"] = int.from_bytes(data[12:14], 'big')
    measurement["resistance"] = { "ohm": int.from_bytes(data[122:126], 'big') / 10 }

    # 0 - unknown
    # 1 - QC2.0
    # 2 - QC3.0
    measurement["charge_mode"] = int.from_bytes(data[100:102], 'big')

    measurement["active_group"] = int.from_bytes(data[15:16], 'big')
    measurement["groups"] = []

    for i in range(10):
        measurement["groups"].append({})
        measurement["groups"][i]["ampere_hours"] = int.from_bytes(data[16 + i*8:20 + i*8], 'big') / 1000
        measurement["groups"][i]["watt_hours"] = int.from_bytes(data[20 + i*8:24 + i*8], 'big') / 1000
    
    measurement["usb"] = {}
    measurement["usb"]["d_plus"] = { "volt": int.from_bytes(data[96:98], 'big') / 100 }
    measurement["usb"]["d_minus"] = { "volt": int.from_bytes(data[98:100], 'big') / 100 }

    measurement["record"] = {}
    measurement["record"]["ampere_hours"] = int.from_bytes(data[102:106], 'big') / 1000
    measurement["record"]["watt_hours"] = int.from_bytes(data[106:110], 'big') / 1000
    measurement["record"]["recorded_time"] = { "seconds": int.from_bytes(data[112:116], 'big') }
    measurement["record"]["is_recording"] = int.from_bytes(data[116:118], 'big')

    settings["record"] = {}
    settings["record"]["stop_current"] = { "ampere" : int.from_bytes(data[110:112], 'big') / 100 }

    settings["backlight"] = {}
    settings["backlight"]["off_delay"] = { "minutes": int.from_bytes(data[118:120], 'big') }
    settings["backlight"]["level"] = int.from_bytes(data[120:122], 'big')

    settings["active_screen"] = int.from_bytes(data[126:128], 'big')
    
    return response 
