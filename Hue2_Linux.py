#!/bin/python
from os import system
from subprocess import check_output
from math import ceil
import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from liquidctl import driver

class Main:
	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Hue2_Linux_GUI.glade")

		window = self.builder.get_object("window")
		device_combo_box = self.builder.get_object("device")
		device_channel_combo_box = self.builder.get_object("device_channel")
		self.device_channel_entry = self.builder.get_object("device_channel_entry")
		refresh_button = self.builder.get_object("refresh")
		presets_apply = self.builder.get_object("presets_apply")

		window.connect("delete-event", Gtk.main_quit)
		device_combo_box.connect("changed", self.onDeviceChanged)
		device_channel_combo_box.connect("changed", self.onDeviceChannelChanged)
		refresh_button.connect("clicked", lambda _: self.refreshDevices())
		presets_apply.connect("clicked", lambda _: self.onPresetsApply())

		self.animations_page = Animations(self)
		self.per_led_page = Per_led(self)
		self.buttons_to_disable = [self.per_led_page.grouping_cb, self.per_led_page.breathing_cb, self.per_led_page.apply, self.animations_page.apply, presets_apply]
		self.speeds, self.mode = ["slowest","slower","normal","faster","fastest"], "super-fixed"

		self.refreshDevices()
		window.show()

	def getHue2Devices(self):
		response, channel, self.devices, count = check_output("liquidctl initialize all", shell=1), "", {}, 0
		for line in response.decode("utf-8").split("\n"):
			if "N" in line:
				device = line.split(" (")[0]
				self.devices[device] = {"id":len(self.devices),
							"channels":{}}
			try:
				channel = re.search("LED \d", line).group(0).replace("LED ", "led")
				if channel not in self.devices[device]["channels"]:
					self.devices[device]["channels"][channel] = 0

				length = int(re.search("\d{3}", line).group(0))
				if length == 300:
					count += 10
				elif length == 250:
					count += 8
				self.devices[device]["channels"][channel] = self.devices[device]["channels"][channel] + count
				count = 0
			except AttributeError:
				pass

	def setLed(self, *colours, backwards=0):
		system(f"liquidctl -d '{self.deviceno}' set {self.channel} color {('backwards-'*backwards)+self.mode} --speed={self.speeds[int(self.builder.get_object('speed').get_value())-1]} {' '.join(colours)}")
		print(f"liquidctl -d '{self.deviceno}' set {self.channel} color {('backwards-'*backwards)+self.mode} --speed={self.speeds[int(self.builder.get_object('speed').get_value())-1]} {' '.join(colours)}")

	def refreshDevices(self):
		device_list = self.builder.get_object("device_liststore")
		device_entry = self.builder.get_object("device_entry")

		device_list.clear()
		device_entry.set_text("")
		self.device_channel_entry.set_text("")

		for button in self.buttons_to_disable:
			button.set_sensitive(0)
		for row in range(5):
			self.per_led_page.led_grid.remove_row(0)

		self.getHue2Devices()
		for device in self.devices.keys():
			device_list.append([device])

	def onDeviceChannelChanged(self, combo_box):
		try:
			self.channel = combo_box.get_child().get_text()
			self.per_led_page.channel_len = self.channels[self.channel]
			self.per_led_page.updateLedGrid()
		except KeyError:
			pass

	def onDeviceChanged(self, combo_box):
		def updateChannels():
			device_channel_list = self.builder.get_object("device_channel_liststore")
			device_channel_list.clear()

			device = combo_box.get_child().get_text()
			if device!="": #when function ran by refreshing devices, no chosen device
				self.channels = self.devices[device]["channels"]
				channel_names = list(self.channels.keys())
				for channel in channel_names:
					device_channel_list.append([channel])
				self.channel=channel_names[0]
				self.device_channel_entry.set_text(self.channel)
				self.deviceno = self.devices[device]["id"]
		updateChannels()
		self.per_led_page.updateLedGrid()

		for button in self.buttons_to_disable:
			button.set_sensitive(1)

	def onPresetsApply(self):
		presets_menu = self.builder.get_object("presets_menu")
		self.mode = presets_menu.get_selected_row().get_children()[0].get_label().lower().replace(" ","-")
		self.setLed("", backwards=self.builder.get_object("presets_direction_b").get_active())

class Per_led(Main):
	def __init__(self, top):
		self.grouping_cb = top.builder.get_object("grouping_checkbox")
		self.breathing_cb = top.builder.get_object("breathing_checkbox")
		self.apply = top.builder.get_object("per_led_apply")
		self.led_grid = top.builder.get_object("led_grid")

		self.grouping_cb.connect("clicked", lambda cb: self.onGroupingCbToggled(top, cb))
		self.breathing_cb.connect("clicked", lambda cb: self.onBreathingCbToggled(top, cb))
		self.apply.connect("clicked", lambda _: self.onApply(top))

		self.group_size, self.channel_len = 1, 0

	def onBreathingCbToggled(self, top, cb):
		breathing_speed_scale = top.builder.get_object("breathing_speed_scale")
		if cb.get_active() == 1:
			top.mode = "super-breathing"
			breathing_speed_scale.set_visible(1)
		else:
			breathing_speed_scale.set_visible(0)
			top.mode = "super-fixed"

	def onGroupingCbToggled(self, top, cb):
		group_size_entry = top.builder.get_object("group_size")
		if cb.get_active()==0:
			group_size_entry.set_visible(0)
			group_size_entry.disconnect(self.group_size_handler_id)
			self.group_size=1
		else:
			group_size_entry.set_visible(1)
			self.group_size_handler_id = group_size_entry.connect("changed", self.onGroupSizeChanged)
			try:
				top.group_size = int(group_size_entry.get_text())
			except ValueError:
				pass
		self.updateLedGrid()

	def onGroupSizeChanged(self, group_size_entry):
		group_size, buffer = group_size_entry.get_text(), ""
		for letter in group_size:
			if letter in "0123456789":
				buffer += letter
		try:
			buffer_int = int(buffer)
			if buffer_int > self.channel_len:
				buffer = str(self.channel_len)
			elif len(buffer)>2:
				buffer = buffer[:2]
			elif buffer_int!=0:
				self.group_size = buffer_int
		except ValueError:
			pass
		group_size_entry.set_text(buffer)
		self.updateLedGrid()

	def updateLedGrid(self):
		for row in range(5):
			self.led_grid.remove_row(0)
		self.led_buttons, x, y = [], -1, 0
		for led in range(ceil(self.channel_len/self.group_size)):
			self.led_buttons.append(Gtk.ColorButton())
			x+=1
			if x==8:
				y+=1
				x=0
			self.led_grid.attach(self.led_buttons[-1],x,y,1,1)
			self.led_buttons[-1].show()

	def onApply(self, top):
		colours = []
		for button in self.led_buttons:
			colour = ""
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour += ("0"*(rgb_channel<10)+format(rgb_channel, "x"))
			for _ in range(self.group_size):
				colours.append(colour)
		top.setLed(*colours)


class Animations(Main):
	def __init__(self, top):
		remove_colour = top.builder.get_object("remove_colour")
		self.add_colour = top.builder.get_object("add_colour")
		self.apply = top.builder.get_object("animations_apply")
		self.custom_colours = top.builder.get_object("custom_colours")
		self.marquee_rb = top.builder.get_object("marquee_rb")

		remove_colour.connect("clicked", self.onRemoveColour)
		self.add_colour.connect("clicked", lambda _: self.onAddColour(remove_colour))
		self.apply.connect("clicked", lambda _: self.onApply(top))
		self.marquee_rb.connect("clicked", lambda btn: self.toggleLengthScale(top, btn))

		self.custom_colours.x, self.custom_colours.y, self.custom_colour_buttons = 0, 0, []

	def onRemoveColour(self, btn):
		child = ""
		if self.custom_colours.x==2:
			self.custom_colours.x, self.custom_colours.y = 1,4
		if self.custom_colours.y==0 and self.custom_colours.x==1: #y before x for lazy evaluation
			self.custom_colours.x, self.custom_colours.y = 0, 3
			child = self.custom_colours.get_child_at(self.custom_colours.x,self.custom_colours.y)
		else:
			child = self.custom_colours.get_child_at(self.custom_colours.x, self.custom_colours.y-1)
			self.custom_colours.y-=1
		del self.custom_colour_buttons[-1]
		child.destroy()

		if len(self.custom_colour_buttons)==0:
			btn.set_sensitive(0)

	def onAddColour(self, btn):
		if self.custom_colours.x!=2:
			self.custom_colour_buttons.append(Gtk.ColorButton())
			self.custom_colours.attach(self.custom_colour_buttons[-1],self.custom_colours.x,self.custom_colours.y,1,1)
			self.custom_colour_buttons[-1].show()
			self.custom_colours.y+=1
			if self.custom_colours.y==4:
				self.custom_colours.y=0
				self.custom_colours.x+=1
			btn.set_sensitive(1)

	def toggleLengthScale(self, top, btn):
		length_scale = top.builder.get_object("length_scale")
		length_scale.set_visible(btn.get_active())

	def onApply(self, top):
		length=int(top.builder.get_object('length').get_value())
		for radio_button in top.builder.get_object("animations_mode_rb").get_group():
			if radio_button.get_active()==1:
				top.mode = radio_button.get_label().lower()
				break
		if top.mode=="marquee":
			if len(self.custom_colour_buttons)<2:
				top.mode=f"marquee-{length}"
			else:
				top.mode=f"covering-marquee"
		colours = []
		for button in self.custom_colour_buttons:
			colour = ""
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour += ("0"*(rgb_channel<10)+format(rgb_channel, "x"))
			colours.append(colour)
		top.setLed(*colours)

if __name__ == "__main__":
	main = Main()
	Gtk.main()
