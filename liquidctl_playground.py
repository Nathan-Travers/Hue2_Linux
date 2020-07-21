#!/bin/python
from liquidctl import driver
devices = driver.find_liquidctl_devices()
print(devices)

for device in devices:
	device.connect()
	print(device.initialize())
	print(device.description)
	device.set_color("led1","fixed",[[0,0,0],[0,0,0],[0,0,0]])

