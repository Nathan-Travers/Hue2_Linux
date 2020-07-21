#!/bin/python
from liquidctl import driver
devices = driver.find_liquidctl_devices()
print(devices)

for device in devices:
	print(device.connect())
	print(device.initialize())
