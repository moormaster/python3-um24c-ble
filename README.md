# Bluetooth Low Energy module for accessing UM24C / A3-B USB Color tester

https://www.amazon.de/USB-Spannungspr%C3%BCfer-Stromtester-Stromz%C3%A4hler-USB-Multimeter-Tester-Multi-function/dp/B07DCS11GM/ref=sr_1_6

## Dependencies

For this library to work bluepy has to be installed. Be sure to run

```
$ pip install -r requirements.txt
```

before using the library.

# BLE protocol

Protocol is based on https://github.com/NiceLabs/atorch-console/blob/master/docs/protocol-design.md
But command codes and reply differs as described at https://sigrok.org/wiki/RDTech_UM_series

App: http://files.banggood.com/2018/05/Android-APP.apk
Manual: https://files.banggood.com/2018/05/A3&A3-B.pdf

