#!/bin/python
from os import system
from subprocess import check_output
import re
def setLed(deviceno, *colours, mode="fixed", speed="normal", direction="forward"):
	for channel in ("led1","led2"):
		system(f"liquidctl -d {deviceno} set {channel} color {mode} {' '.join(colours)}")


import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class Main:
	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Hue2_Linux_GUI.glade")

		window = self.builder.get_object("window")
		window.connect("delete-event", Gtk.main_quit)
		window.show()
		
		device_combo_box = self.builder.get_object("device")
		device_combo_box.connect("changed", self.onDeviceChanged)
		
		device_channel_combo_box = self.builder.get_object("device_channel")
		device_channel_combo_box.connect("changed", self.onDeviceChannelChanged)
		
		def refresh_devices():
			device_list = self.builder.get_object("device_liststore")
			device_list.clear()
			self.devices = self.getHue2Devices()
			for device in self.devices.keys():
				device_list.append([device])
		
		refresh_button = self.builder.get_object("refresh")
		refresh_button.connect("clicked", lambda _: refresh_devices())	
		refresh_devices()
		
	def updateLedGrid(self, length):
		self.led_grid = self.builder.get_object("led_grid")
		for row in range(5):
			self.led_grid.remove_row(0)
		self.led_buttons, x, y = [], -1, 0
		for led in range(length):
			self.led_buttons.append(Gtk.ColorButton())
			x+=1
			if x==8:
				y+=1
				x=0
			self.led_grid.attach(self.led_buttons[-1],x,y,1,1)
			self.led_buttons[-1].show()

		
	def onDeviceChannelChanged(self, combo_box):
		try:
			self.updateLedGrid(self.channels[combo_box.get_child().get_text()])
		except KeyError:
			pass
		
	def onDeviceChanged(self, combo_box):
		def updateChannels():
			channel_list = self.builder.get_object("device_channel_liststore")
			channel_list.clear()
			device = combo_box.get_child().get_text()
			try:
				self.channels = self.devices[device]
				for channel in list(self.channels.keys()):
					channel_list.append([channel])
				self.updateLedGrid(self.channels["LED 1"])
			except KeyError:
				pass
		updateChannels()

	def getHue2Devices(self):
		response, channel, devices, count = check_output("liquidctl initialize all", shell=1), "", {}, 0
		for line in response.decode("utf-8").split("\n"):
			if "N" in line:
				device = line.split(" (")[0]
				devices[device] = {}
			try:
				channel = re.search("LED \d", line).group(0)
				if channel not in devices[device]:
					devices[device][channel] = 0

				length = int(re.search("\d{3}", line).group(0))
				if length == 300:
					count += 10
				elif length == 250:
					count += 8
				devices[device][channel] = devices[device][channel] + count
				count = 0
			except AttributeError:
				pass
		return(devices)

if __name__ == "__main__":
	main = Main()
	Gtk.main()
