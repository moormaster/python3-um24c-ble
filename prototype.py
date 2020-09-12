#!/usr/bin/python3

from bluepy import btle

import sys

UM24C_SERVICE_UUID            = '0000FFE0-0000-1000-8000-00805F9B34FB'
UM24C_CHARACTERISTICS_UUID    = '0000FFE1-0000-1000-8000-00805F9B34FB'
UM24C_DESCRIPTOR_UUID         = '00002902-0000-1000-8000-00805F9B34FB'

class BD18BLEDelegate(btle.DefaultDelegate):
    def __init__(self):
        self.data = b''

    def handleNotification(self, cHandle, data):
        self.data += data

    def reset(self):
        self.data = b''


def checksum(message):
    return int(sum(message) & 0xff ^ 0x44).to_bytes(1, 'big')

def um24c_package(message_type, device_type, payload):
    message = message_type + device_type + payload
    return b'\xff\x55' + message + checksum(message)

def um24c_command(command):
    return um24c_package(b'\x11', b'\x03', command + b'\x00\x00\x00\x00')

if __name__ == '__main__':
    device_address = sys.argv[1]
    command = sys.argv[2]
    iface='hci0'

    delegate = BD18BLEDelegate()

    peripheral = btle.Peripheral(deviceAddr=device_address, iface=iface.replace('hci', '')).withDelegate(delegate)
    characteristics = peripheral.getCharacteristics(uuid=UM24C_CHARACTERISTICS_UUID)[0]
    descriptor = characteristics.getDescriptors(forUUID=UM24C_DESCRIPTOR_UUID)[0]

    # 0xb0-0xce - set record stop current (0.00 A - 0.30 A)
    # 0xd0-0xd5 - set backlight level 0-5
    # 0xe0-0xef - set backlight off delay (0 min - 15 min)
    # 0xf0 - START MEASURING
    # 0xf1 - NEXT
    # 0xf2 - ROTATE RIGHT
    # 0xf3 - NEXT GROUP
    # 0xf4 - CLEAR

    if command == 'measure':
        # subscribe to notifications
        descriptor.write(b'\x01\x00', withResponse=True)

        command = um24c_command(b'\xf0')
        characteristics.write(command, withResponse=True)
        while len(delegate.data) < 130:
            if not peripheral.waitForNotifications(timeout=10):
                break

        assert len(delegate.data) == 130
            
        # unsubscribe from notifications
        descriptor.write(b'\x00\x00', withResponse=True)

        data = delegate.data
        delegate.reset()

        voltage_in_volt = int.from_bytes(data[2:4], 'big') / 100
        current_in_ampere = int.from_bytes(data[4:6], 'big') / 1000
        power_in_watt = int.from_bytes(data[6:10], 'big') / 1000
        temperature_in_celsius = int.from_bytes(data[10:12], 'big')
        temperature_in_fahrenheit = int.from_bytes(data[12:14], 'big')

        current_group = int.from_bytes(data[15:16], 'big')

        ampere_hours_of_group = []
        watt_hours_of_group = []
        for i in range(10):
            ampere_hours_of_group.append( int.from_bytes(data[16 + i*8:20 + i*8], 'big') / 1000 )
            watt_hours_of_group.append( int.from_bytes(data[20 + i*8:24 + i*8], 'big') / 1000 )
        
        record_ampere_hours = int.from_bytes(data[102:106], 'big') / 1000
        record_watt_hours = int.from_bytes(data[106:110], 'big') / 1000
        record_stop_current_in_ampere = int.from_bytes(data[110:112], 'big') / 100
        record_time_in_seconds = int.from_bytes(data[112:116], 'big')

        backlight_off_delay_in_minutes = int.from_bytes(data[118:120], 'big')
        backlight_level = int.from_bytes(data[120:122], 'big')

        resistante_in_ohm = int.from_bytes(data[122:126], 'big') / 10
        
        usb_d_plus_in_volt = int.from_bytes(data[96:98], 'big') / 100
        usb_d_minus_in_volt = int.from_bytes(data[98:100], 'big') / 100

        # 0 - unknown
        # 1 - QC2.0
        # 2 - QC3.0
        charge_mode = int.from_bytes(data[100:102], 'big')

        print(voltage_in_volt)
        print(current_in_ampere)
        print(power_in_watt)
        print(temperature_in_celsius)
        print(temperature_in_fahrenheit)
        print("")
        print(current_group)
        for i in range(10):
            print("group " + str(i))
            print(ampere_hours_of_group[i])
            print(watt_hours_of_group[i])
            print("")
        print(record_ampere_hours)
        print(record_watt_hours)
        print(record_stop_current_in_ampere)
        print(record_time_in_seconds)
        print("")
        print(backlight_off_delay_in_minutes)
        print(backlight_level)
        print("")
        print(resistante_in_ohm)
        print("")
        print(usb_d_plus_in_volt)
        print(usb_d_minus_in_volt)

    if command == 'set_record_stop_current':
        value = float(sys.argv[3])
        value = int(value*100)
        if value < 0 or value > 30:
            raise Exception('Unsupported value for record stop current. Must be between 0.00 and 0.30 A')

        command = um24c_command((value + b'\xb0').to_bytes(1, 'big'))
        characteristics.write(command)

    if command == 'set_backlight_level':
        value = int(sys.argv[3])
        if value < 0 or value > 5:
            raise Exception('Unsupported value for backlight level. Must be between 0 and 5')

        command = um24c_command((value + b'\xd0').to_bytes(1, 'big'))
        characteristics.write(command)

    if command == 'set_backlight_off_delay':
        value = int(sys.argv[3])
        if value < 0 or value > 15:
            raise Exception('Unsupported value for backlight off delay. Must be between 0 and 15 minutes')

        command = um24c_command((value + b'\xe0').to_bytes(1, 'big'))
        characteristics.write(command)

    if command == 'button_next':
        command = um24c_command(b'\xf1')
        characteristics.write(command)

    if command == 'button_rotate':
        command = um24c_command(b'\xf2')
        characteristics.write(command)

    if command == 'button_group':
        command = um24c_command(b'\xf3')
        characteristics.write(command)

    if command == 'button_clear':
        command = um24c_command(b'\xf4')
        characteristics.write(command)

    if command == 'send':
        cmd = int(sys.argv[3]).to_bytes(1, 'big')
        command = um24c_command(cmd)
        characteristics.write(command)
