#!/bin/python
from os import system
from subprocess import check_output
from math import ceil
import re
def setLed(deviceno, channel, *colours, mode="fixed", speed="normal", direction="forward"):
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

		grouping_cb = self.builder.get_object("grouping_checkbox")
		grouping_cb.connect("clicked", self.onGroupingCbToggled)

		self.group_size = 1

		def per_led_apply():
			colours = []
			for button in self.led_buttons:
				colour = ""
				for ind, rgb_channel in enumerate(button.get_rgba()):
					if ind !=3:
						rgb_channel = int(rgb_channel*255)
						colour += ("0"*(rgb_channel<10)+format(rgb_channel, "x"))
				for _ in range(self.group_size):
					colours.append(colour)
			setLed(0, self.channel, *colours, mode="super-fixed")
		per_led_apply_button = self.builder.get_object("per_led_apply")
		per_led_apply_button.connect("clicked", lambda _: per_led_apply())

		def refresh_devices():
			device_list = self.builder.get_object("device_liststore")
			device_list.clear()
			self.devices = self.getHue2Devices()
			for device in self.devices.keys():
				device_list.append([device])
		refresh_button = self.builder.get_object("refresh")
		refresh_button.connect("clicked", lambda _: refresh_devices())

		refresh_devices()


	def updateLedGrid(self):
		self.led_grid = self.builder.get_object("led_grid")
		for row in range(5):
			self.led_grid.remove_row(0)
		self.led_buttons, x, y = [], -1, 0
		for led in range(ceil(self.channels[self.channel]/self.group_size)):
			self.led_buttons.append(Gtk.ColorButton())
			x+=1
			if x==8:
				y+=1
				x=0
			self.led_grid.attach(self.led_buttons[-1],x,y,1,1)
			self.led_buttons[-1].show()

	def onDeviceChannelChanged(self, combo_box):
		try:
			self.channel = combo_box.get_child().get_text()
			self.updateLedGrid()
		except KeyError:
			pass

	def onDeviceChanged(self, combo_box):
		def updateChannels():
			channel_list = self.builder.get_object("device_channel_liststore")
			channel_list.clear()
			device = combo_box.get_child().get_text()
			try:
				self.channels, self.channel = self.devices[device], "led1"
				for channel in list(self.channels.keys()):
					channel_list.append([channel])
				self.updateLedGrid()
			except KeyError:
				pass
		updateChannels()

	def onGroupingCbToggled(self, cb):
		group_size_entry = self.builder.get_object("group_size")
		active = cb.get_active()
		group_size_entry.set_visible(active)
		if active==0:
			self.group_size=1
			group_size_entry.disconnect(self.group_size_handler_id)
		else:
			self.group_size_handler_id = group_size_entry.connect("changed", self.onGroupSizeChanged)
			try:
				self.group_size = int(group_size_entry.get_text())
			except ValueError:
				pass
		self.updateLedGrid()

	def onGroupSizeChanged(self, group_size_entry):
		group_size, buffer = group_size_entry.get_text(), ""
		for letter in group_size:
			if letter in "0123456789":
				buffer += letter
		try:
			if int(buffer) > self.channels[self.channel]:
				buffer = "26"
			elif len(buffer)>2:
				buffer = buffer[:2]
			group_size_entry.set_text(buffer)
			self.group_size = int(buffer)
			self.updateLedGrid()
		except ValueError:
			group_size_entry.set_text("")

	def getHue2Devices(self):
		response, channel, devices, count = check_output("liquidctl initialize all", shell=1), "", {}, 0
		for line in response.decode("utf-8").split("\n"):
			if "N" in line:
				device = line.split(" (")[0]
				devices[device] = {}
			try:
				channel = re.search("LED \d", line).group(0).replace("LED ", "led")
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
