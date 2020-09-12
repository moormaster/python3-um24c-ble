# Atorch protocol design

## Initial connection information

### Bluetootch LE

Device broadcast name: UD18-BLE

| Type           | UUID                                   |
| -------------- | -------------------------------------- |
| Service        | `0000FFE0-0000-1000-8000-00805F9B34FB` |
| Characteristic | `0000FFE1-0000-1000-8000-00805F9B34FB` |
| Descriptor     | `00002902-0000-1000-8000-00805F9B34FB` |

## Packet layout

|    Offset | Field        | Block size | Note                                      |
| --------: | ------------ | ---------- | ----------------------------------------- |
|      `00` | Magic Header | 2 byte     | `FF 55`                                   |
|      `02` | Message Type | 1 byte     | `11` |
|      `03` | Payload      |            |                                           |
| Last byte | Checksum     | 1 byte     | [Checksum Algorithm](#checksum-algorithm) |


### USB Meter Report

| Offset | Field                                           | Block size | Note                                |
| -----: | ----------------------------------------------- | ---------- | ----------------------------------- |
|   `02` | Voltage                                         | 2 byte     | 16 bit BE (divide by 100)           |
|   `04` | Current                                         | 2 byte     | 16 bit BE (divide by 1000)          |
|   `06` | Power in watt                                   | 4 byte     | 32 bit BE (divide by 1000)          |
|   `0A` | Temperature in celsius                          | 2 byte     | 16 bit BE                           |
|   `0C` | Temperature in fahrenheit                       | 2 byte     | 16 bit BE                           |
|   `0F` | Active group                                    | 1 byte     | 8 bit BE                            |
|   `10` | Ampere hours group 0                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `14` | Watt hours group 0                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `18` | Ampere hours group 1                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `1C` | Watt hours group 1                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `20` | Ampere hours group 2                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `24` | Watt hours group 2                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `28` | Ampere hours group 3                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `2C` | Watt hours group 3                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `30` | Ampere hours group 4                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `34` | Watt hours group 4                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `38` | Ampere hours group 5                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `3C` | Watt hours group 5                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `40` | Ampere hours group 6                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `44` | Watt hours group 6                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `48` | Ampere hours group 7                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `4C` | Watt hours group 7                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `50` | Ampere hours group 8                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `54` | Watt hours group 8                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `58` | Ampere hours group 9                            | 4 byte     | 32 bit BE (divide by 1000)          |
|   `5C` | Watt hours group 9                              | 4 byte     | 32 bit BE (divide by 1000)          |
|   `60` | USB D+ voltage                                  | 2 byte     | 16 bit BE (divide by 100)           |
|   `62` | USB D- voltage                                  | 2 byte     | 16 bit BE (divide by 100)           |
|   `64` | Charge mode (0 - unknown, 1 - QC2.0, 2 - QC3.0) | 2 byte     | 16 bit BE                           |
|   `66` | Recorded ampere hours                           | 4 byte     | 32 bit BE (divide by 1000)          |
|   `6A` | Recorded watt hours                             | 4 byte     | 32 bit BE (divide by 1000)          |
|   `6E` | Record-Stop current in ampere                   | 2 byte     | 16 bit BE (divide by 100)           |
|   `70` | Recorded time in seconds                        | 4 byte     | 32 bit BE                           |
|   `76` | Backlight off delay in minutes                  | 2 byte     | 16 bit BE                           |
|   `78` | Backlight level                                 | 2 byte     | 16 bit BE                           |
|   `7A` | Resistance in Ohm                               | 4 byte     | 32 bit BE (divide by 10)            |

### Command

| Offset | Field       | Block size | Note                           |
| -----: | ----------- | ---------- | ------------------------------ |
|   `03` | Device Type | 1 byte     | `03`                           |
|   `04` | Command     | 1 byte     |                                |
|   `05` | Value       | 4 byte     | `00000000`                     |

| Command      | Action                                    |
| -----------: | ----------------------------------------- |
|    `b0`-`ce` | Set record-stop current (0.00 A - 0.30 A) |
|    `d0`-`d5` | Set backlight level (0-5)                 |
|    `e0`-`ef` | Set backlight off delay (0 min - 15 min)  |
|    `f0`      | start measuring                           |
|    `f1`      | NEXT button                               |
|    `f2`      | ROTATE button                             |
|    `f3`      | GROUP button                              |
|    `f4`      | CLEAR button                              |


## Checksum Algorithm

> Without **Magic Header**

```javascript
const packet = Buffer.from('FF551103310000000001', 'hex');

const payload = packet.slice(2, -1);
// "11033100000000" (hex string)

const checksum = payload.reduce((acc, item) => (acc + item) & 0xff, 0) ^ 0x44;
// checksum: 0x01

packet[packet.length - 1] == checksum;
// returns true
```

## Thanks

- <https://github.com/msillano/UD18-protocol-and-node-red>
