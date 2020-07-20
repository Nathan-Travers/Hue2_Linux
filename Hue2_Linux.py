#!/bin/python
from os import system
from subprocess import check_output
from math import ceil
import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk

class Main:
	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Hue2_Linux_GUI.glade")
		self.x, self.y = 0, 0

		window = self.builder.get_object("window")
		window.connect("delete-event", Gtk.main_quit)
		window.show()

		device_combo_box = self.builder.get_object("device")
		device_combo_box.connect("changed", self.onDeviceChanged)

		device_channel_combo_box = self.builder.get_object("device_channel")
		device_channel_combo_box.connect("changed", self.onDeviceChannelChanged)

		grouping_cb = self.builder.get_object("grouping_checkbox")
		grouping_cb.connect("clicked", self.onGroupingCbToggled)

		breathing_cb = self.builder.get_object("breathing_checkbox")
		breathing_cb.connect("clicked", self.onBreathingCbToggled)

		presets = self.builder.get_object("presets_apply")
		presets.connect("clicked", lambda _: self.onPresetsApply())

		def onAnimationsApply():
			for radio_button in self.builder.get_object("radiobutton1").get_group():
				if radio_button.get_active()==1:
					self.mode = radio_button.get_label().lower()
					break
			colours = []
			for button in self.custom_colour_buttons:
				colour = ""
				for ind, rgb_channel in enumerate(button.get_rgba()):
					if ind !=3:
						rgb_channel = int(rgb_channel*255)
						colour += ("0"*(rgb_channel<10)+format(rgb_channel, "x"))
				colours.append(colour)
			self.setLed(*colours)
		def onRemoveColour(btn):
			child = ""
			custom_colours = self.builder.get_object("custom_colours")
			if self.x==2:
				self.x, self.y = 1,4
			if self.y==0 and self.x==1:
				self.x, self.y = 0, 3
				child = custom_colours.get_child_at(self.x,self.y)
			else:
				child = custom_colours.get_child_at(self.x, self.y-1)
				self.y-=1
			del self.custom_colour_buttons[-1]
			child.destroy()
			if len(self.custom_colour_buttons)==0:
				btn.set_sensitive(0)

		remove_colour = self.builder.get_object("remove_colour")
		remove_colour.connect("clicked", onRemoveColour)
		animations_apply = self.builder.get_object("animations_apply")
		animations_apply.connect("clicked", lambda _: onAnimationsApply())

		add_colour = self.builder.get_object("add_colour")
		add_colour.connect("clicked", lambda _: self.onAddColour(remove_colour))

		self.group_size = 1
		self.speeds, self.custom_colour_buttons = ["slowest","slower","normal","faster","fastest"], []
		self.led_grid = self.builder.get_object("led_grid")

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
			self.setLed(*colours)
		per_led_apply_button = self.builder.get_object("per_led_apply")
		per_led_apply_button.connect("clicked", lambda _: per_led_apply())

		def refresh_devices():
			device_list = self.builder.get_object("device_liststore")
			device_entry = self.builder.get_object("device_entry")
			device_channel_entry = self.builder.get_object("device_channel_entry")
			device_list.clear()
			device_entry.set_text("")
			device_channel_entry.set_text("")
			self.builder.get_object("grouping_checkbox").set_sensitive(0)
			self.builder.get_object("breathing_checkbox").set_sensitive(0)
			self.builder.get_object("presets_apply").set_sensitive(0)
			self.builder.get_object("per_led_apply").set_sensitive(0)
			self.builder.get_object("animations_apply").set_sensitive(0)
			for row in range(5):
				self.led_grid.remove_row(0)

			self.devices = self.getHue2Devices()
			for device in self.devices.keys():
				device_list.append([device])
		refresh_button = self.builder.get_object("refresh")
		refresh_button.connect("clicked", lambda _: refresh_devices())

		refresh_devices()


	def setLed(self, *colours, backwards=0):
		mode=self.mode
		system(f"liquidctl -m '{self.device}' set {self.channel} color {('backwards-'*backwards)+mode} --speed={self.speeds[int(self.builder.get_object('speed').get_value())-1]} {' '.join(colours)}")
		print(f"liquidctl -m '{self.device}' set {self.channel} color {('backwards-'*backwards)+mode} --speed={self.speeds[int(self.builder.get_object('speed').get_value())-1]} {' '.join(colours)}")

	def updateLedGrid(self):
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
			device_channel_entry = self.builder.get_object("device_channel_entry")
			channel_list.clear()
			self.device = combo_box.get_child().get_text()
			try:
				self.channels = self.devices[self.device]
				channels = list(self.channels.keys())
				for channel in channels:
					channel_list.append([channel])
				self.channel=channels[0]
				device_channel_entry.set_text(self.channel)
				self.updateLedGrid()
			except KeyError:
				pass
		updateChannels()
		self.builder.get_object("grouping_checkbox").set_sensitive(1)
		self.builder.get_object("breathing_checkbox").set_sensitive(1)
		self.builder.get_object("presets_apply").set_sensitive(1)
		self.builder.get_object("per_led_apply").set_sensitive(1)
		self.builder.get_object("animations_apply").set_sensitive(1)


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

	def onBreathingCbToggled(self, cb):
		if cb.get_active() == 1:
			self.mode = "super-breathing"
		else:
			self.mode = "super-fixed"
		print("!HD")

	def onGroupSizeChanged(self, group_size_entry):
		group_size, self.group_size, buffer = group_size_entry.get_text(), 1, ""
		for letter in group_size:
			if letter in "0123456789":
				buffer += letter
		try:
			if int(buffer) > self.channels[self.channel]:
				buffer = str(self.channels[self.channel])
			elif len(buffer)>2:
				buffer = buffer[:2]
			elif int(buffer)!=0:
				self.group_size = int(buffer)
		except ValueError:
			pass
		group_size_entry.set_text(buffer)
		self.updateLedGrid()

	def onPresetsApply(self):
		presets_menu = self.builder.get_object("presets_menu")
		self.mode = presets_menu.get_selected_row().get_children()[0].get_label().lower().replace(" ","-")
		self.setLed("", backwards=self.builder.get_object("presets_direction_b").get_active())

	def onAddColour(self, btn):
		if self.x!=2:
			custom_colours = self.builder.get_object("custom_colours")
			self.custom_colour_buttons.append(Gtk.ColorButton())
			custom_colours.attach(self.custom_colour_buttons[-1],self.x,self.y,1,1)
			self.custom_colour_buttons[-1].show()
			self.y+=1
			if self.y==4:
				self.y=0
				self.x+=1
			btn.set_sensitive(1)

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
