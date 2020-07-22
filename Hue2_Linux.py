#!/bin/python
import gi, json
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from liquidctl import driver
from math import ceil

class Main:
	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Hue2_Linux_GUI.glade")

		window = self.builder.get_object("window")
		device_combo_box = self.builder.get_object("device")
		self.device_channel_combo_box = self.builder.get_object("device_channel")
		self.device_channel_entry = self.builder.get_object("device_channel_entry")
		refresh_button = self.builder.get_object("refresh")
		presets_apply = self.builder.get_object("presets_apply")
		profiles = self.builder.get_object("profiles_btn")

		window.connect("delete-event", Gtk.main_quit)
		device_combo_box.connect("changed", self.onDeviceChange)
		refresh_button.connect("clicked", lambda _: self.refreshDevices())
		presets_apply.connect("clicked", lambda _: self.onPresetsApply())
		def profilesPopup(_):
			self.saveDeviceState()
			self.profiles.show()
		profiles.connect("clicked", profilesPopup)
		self.speed = self.builder.get_object("speed")
		self.dcc = self.device_channel_combo_box.connect("changed", self.onDeviceChannelChange)

		self.animations_page = Animations(self)
		self.per_led_page = Per_led(self)
		self.profiles = Profiles(self)
		self.pages=[self.per_led_page, self.animations_page]
		self.buttons_to_disable = [self.per_led_page.grouping_cb, self.per_led_page.breathing_cb, self.per_led_page.apply, self.animations_page.apply, presets_apply]
		self.speeds, self.mode = ["slowest","slower","normal","faster","fastest"], "super-fixed"
		self.colours = {}
		self.data={}

		self.refreshDevices()
		for device, device_name in zip(self.devices.values(), self.devices.keys()):
			for channel in device["channels"]:
				self.data[device_name][channel] = {
					"per_led": {
						"colours":[],
						"group_size":1,
						"speed":3.0,
						"breathing":0},
					"animations": {
						"colours":[],
						"mode":"fading",
						"length":3.0,
						"backwards":0}}
		window.show()

	def saveDeviceState(self):
		self.data[self.device][self.channel] = {
			"per_led": {
				"colours":self.per_led_page.getColours(),
				"group_size":self.per_led_page.group_size,
				"speed":self.speed.get_value(),
				"breathing":(self.mode=="super-breathing")}}
		mode, length, backwards = self.animations_page.getOpts()
		self.data[self.device][self.channel]["animations"] = {
			"colours":self.animations_page.getColours(),
			"mode":mode,
			"length":length,
			"backwards":backwards}
	def getHue2Devices(self):
		self.devices={}
		for device in driver.find_liquidctl_devices():
			device.connect()
			device_info = device.initialize()
			device_name = device.description.replace(" (experimental)", "")
			self.devices[device_name] = {"device": device,
						     "version": device_info[0][1],
						     "channels": {}}
			for line in device_info[1:]:
				channel = line[0][:5].lower().replace(" ","")
				if channel not in self.devices[device_name]["channels"]:
					self.devices[device_name]["channels"][channel] = 0
				length = int(line[1][-6:-3])
				if length == 300:
					self.devices[device_name]["channels"][channel] += 10
				elif length == 250:
					self.devices[device_name]["channels"][channel] += 8
			self.data[device_name] = {}

	def setLed(self, *colours, speed=2, backwards=0):
		true_colours=[]
		for colour in colours:
			for _ in range(self.per_led_page.group_size):
				true_colours.append(colour)
		self.devices[self.device]["device"].set_color(self.channel, self.mode, true_colours, speed=self.speeds[int(self.speed.get_value())-1])
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
		self.device=device_list[0][0]
		self.channel = list(self.devices[device]["channels"].keys())[0]

	def onDeviceChannelChange(self, combo_box):
		self.saveDeviceState()
		self.channel = combo_box.get_child().get_text()
		self.updatePage()
	def updatePage(self):
		per_led_page_data, animations_page_data = (list(item.values()) for item in self.data[self.device][self.channel].values())
		self.animations_page.setOpts(self, *animations_page_data[1:])
		self.animations_page.setColours(animations_page_data[0])
		self.per_led_page.channel_len = self.channels[self.channel]
		self.per_led_page.setOpts(self, *per_led_page_data[1:])
		self.per_led_page.updateLedGrid()
		self.per_led_page.setColours(per_led_page_data[0])

	def onDeviceChange(self, combo_box):
		self.device_channel_combo_box.disconnect(self.dcc)
		self.saveDeviceState()
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
			self.device = device
			self.updatePage()
		updateChannels()

		for btn in self.per_led_page.led_buttons:
			btn.set_rgba(Gdk.RGBA(1,1,1,1))
		for button in self.buttons_to_disable:
			button.set_sensitive(1)
		self.dcc = self.device_channel_combo_box.connect("changed", self.onDeviceChannelChange)
		self.onDeviceChannelChange(self.device_channel_combo_box)

	def onPresetsApply(self):
		presets_menu = self.builder.get_object("presets_menu")
		self.mode = presets_menu.get_selected_row().get_children()[0].get_label().lower().replace(" ","-")
		self.mode = ("backwards-"*self.builder.get_object("presets_direction_b").get_active())+self.mode
		self.setLed([0,0,0]) #have to pass empty colours due to error in library coding

class Per_led(Main):
	def __init__(self, top):
		self.grouping_cb = top.builder.get_object("grouping_checkbox")
		self.breathing_cb = top.builder.get_object("breathing_checkbox")
		self.apply = top.builder.get_object("per_led_apply")
		self.led_grid = top.builder.get_object("led_grid")
		self.breathing_speed_scale = top.builder.get_object("breathing_speed_scale")
		self.group_size_entry = top.builder.get_object("group_size")

		self.grouping_cb.connect("clicked", lambda cb: self.onGroupingCbToggle(top, cb))
		self.breathing_cb.connect("clicked", lambda cb: self.onBreathingCbToggle(top, cb))
		self.apply.connect("clicked", lambda _: self.onApply(top))

		self.group_size, self.led_len = 1, (0,0)
		self.x, self.y = -1, 0
		self.led_buttons = []
		self.name = "per_led"

	def onBreathingCbToggle(self, top, cb):
		if cb.get_active() == 1:
			top.mode = "super-breathing"
			self.breathing_speed_scale.set_visible(1)
		else:
			self.breathing_speed_scale.set_visible(0)
			top.mode = "super-fixed"

	def onGroupingCbToggle(self, top, cb):
		if cb.get_active()==0:
			self.group_size_entry.set_visible(0)
			self.group_size_entry.disconnect(self.group_size_handler_id)
			self.group_size=1
			self.updateLedGrid()
		else:
			self.group_size_entry.set_visible(1)
			self.group_size_handler_id = self.group_size_entry.connect("changed", self.onGroupSizeChange)
			try:
				self.group_size = int(self.group_size_entry.get_text())
				self.updateLedGrid()
			except ValueError:
				pass

	def onGroupSizeChange(self, group_size_entry):
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
				self.updateLedGrid()
		except ValueError:
			pass
		group_size_entry.set_text(buffer)

	def updateLedGrid(self):
		self.led_len = (self.led_len[1], ceil(self.channel_len//self.group_size))
		if self.led_len[1]<self.led_len[0]:
			for button in self.led_buttons[:self.led_len[1]-1:-1]:
				button.destroy()
				del self.led_buttons[-1]
				self.x-=1
				if self.x==-1:
					self.y-=1
					self.x=7
		elif self.led_len[1]>self.led_len[0]:
			for led in range(self.led_len[1]-self.led_len[0]):
				self.led_buttons.append(Gtk.ColorButton())
				self.x+=1
				if self.x==8:
					self.y+=1
					self.x=0
				self.led_buttons[-1].set_rgba(Gdk.RGBA(1,1,1,1))
				self.led_grid.attach(self.led_buttons[-1],self.x,self.y,1,1)
				self.led_buttons[-1].show()
	def getColours(self):
		colours = []
		for button in self.led_buttons:
			colour = []
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour.append(rgb_channel)
			colours.append(colour)
		return(colours)

	def onApply(self, top):
		if "super" not in top.mode:
			top.mode="super-fixed"
		top.setLed(*self.getColours())

	def setOpts(self, top, group_size, speed, breathing):
		self.group_size_entry.set_text(str(group_size))
		self.grouping_cb.set_active((group_size>1))
		self.breathing_cb.set_active(breathing)
		top.speed.set_value(speed)
	def setColours(self, colours):
		for button, colour in zip(self.led_buttons, colours):
			colour_float=[]
			for channel in colour:
				colour_float.append(channel/255)
			button.set_rgba(Gdk.RGBA(*colour_float))

class Animations(Main):
	def __init__(self, top):
		remove_colour = top.builder.get_object("remove_colour")
		self.add_colour = top.builder.get_object("add_colour")
		self.apply = top.builder.get_object("animations_apply")
		self.marquee_rb = top.builder.get_object("marquee_rb")
		self.custom_colours = top.builder.get_object("custom_colours")
		self.backwards_btn = top.builder.get_object("animations_direction_b")
		self.length_scale = top.builder.get_object("length_scale")
		remove_colour.connect("clicked", self.onRemove)
		self.add_colour.connect("clicked", lambda btn: self.onAdd(btn, remove_colour))
		self.apply.connect("clicked", lambda _: self.onApply(top))
		self.marquee_rb.connect("clicked", lambda btn: self.onMarqueeSelect(top, btn))

		self.custom_colours.x, self.custom_colours.y, self.custom_colours.buttons = 0, 0, []
		self.radio_buttons = top.builder.get_object("animations_mode_rb").get_group()[::-1]
		self.name = "animations"

	def removeColour(self):
		child = ""
		if self.custom_colours.x==2:
			self.custom_colours.x, self.custom_colours.y = 1,4
		if self.custom_colours.y==0 and self.custom_colours.x==1: #y before x for lazy evaluation
			self.custom_colours.x, self.custom_colours.y = 0, 3
			child = self.custom_colours.get_child_at(self.custom_colours.x,self.custom_colours.y)
		else:
			child = self.custom_colours.get_child_at(self.custom_colours.x, self.custom_colours.y-1)
			self.custom_colours.y-=1
		del self.custom_colours.buttons[-1]
		child.destroy()
	def onRemove(self, btn):
		self.add_colour.set_sensitive(1)
		self.removeColour()
		if len(self.custom_colours.buttons)==0:
			btn.set_sensitive(0)

	def addColour(self):
		if self.custom_colours.x!=2:
			self.custom_colours.buttons.append(Gtk.ColorButton())
			self.custom_colours.attach(self.custom_colours.buttons[-1],self.custom_colours.x,self.custom_colours.y,1,1)
			self.custom_colours.buttons[-1].set_rgba(Gdk.RGBA(1,1,1,1))
			self.custom_colours.buttons[-1].show()
			self.custom_colours.y+=1
			if self.custom_colours.y==4:
				self.custom_colours.y=0
				self.custom_colours.x+=1
	def onAdd(self, btn_self, btn):
		btn.set_sensitive(1)
		if self.custom_colours.x==2:
			btn_self.set_sensitive(0)
		self.addColour()

	def onMarqueeSelect(self, top, btn):
		self.length_scale.set_visible(btn.get_active())
		top.builder.get_object("animations_directions").set_visible(btn.get_active())

	def getOpts(self):
		backwards= 0
		length = int(self.length_scale.get_value())
		for radio_button in self.radio_buttons:
			if radio_button.get_active()==1:
				mode = radio_button.get_label().lower()
				break
		if mode=="marquee":
			backwards = self.backwards_btn.get_active()
			if len(self.custom_colours.buttons)<2:
				mode=f"marquee-{length}"
			else:
				mode=f"covering-marquee"
			if backwards:
				if mode!="covering-marquee":
					mode = "backwards-"+mode
				else:
					mode = "covering-backwards-marquee" #the only mode that doesn't prefix "backwards-"
		return(mode, length, backwards)

	def getColours(self):
		colours = []
		for button in self.custom_colours.buttons:
			colour = []
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour.append(rgb_channel)
			colours.append(colour)
		return(colours)
	def onApply(self, top):
		top.mode = self.getOpts()[0]
		top.setLed(*self.getColours())

	def setColours(self, colours):
		if len(self.custom_colours.buttons)<len(colours):
			for _ in range(len(colours)-len(self.custom_colours.buttons)):
				self.addColour()
		elif len(self.custom_colours.buttons)>len(colours):
			for _ in range(len(self.custom_colours.buttons)-len(colours)):
				self.removeColour()
		for button, colour in zip(self.custom_colours.buttons, colours):
			colour_float=[]
			for channel in colour:
				colour_float.append(channel/255)
			button.set_rgba(Gdk.RGBA(*colour_float))

	def setOpts(self, top, mode, length, backwards):
		for btn in self.radio_buttons:
			if btn.get_label().lower() in mode:
				btn.set_active(1)
				break
		top.builder.get_object("length").set_value(length)
		self.backwards_btn.set_active(backwards)
#top.builder.get_object
class Profiles(Main):
	def __init__(self, top):
		self.window = top.builder.get_object("profiles")
		self.save_btn = top.builder.get_object("profiles_save")
		self.load_btn = top.builder.get_object("profiles_load")
		self.remove_btn = top.builder.get_object("profiles_remove")
		self.exit_btn = top.builder.get_object("profiles_exit")
		self.lb = top.builder.get_object("profiles_lb")
		self.dialog_save = top.builder.get_object("dialog_save")
		self.dialog_save_entry = top.builder.get_object("dialog_save_entry")
		cancel_dialog = top.builder.get_object("dialog_cancel")

		cancel_dialog.connect("clicked", lambda _: top.builder.get_object("save_dialog").hide())

		self.save_btn.connect("clicked", lambda _: self.save(top))
		self.load_btn.connect("clicked", lambda _: self.load(top))
		self.remove_btn.connect("clicked", self.remove)
		self.exit_btn.connect("clicked", lambda _: self.exit())
		self.dialog_save_entry.connect("changed", self.sanitizeEntry)

		self.refreshSaves()

	def refreshSaves(self):
		for child in self.lb.get_children():
			self.lb.remove(child)
		try:
			with open("saved_configurations.json", "r") as f:
				self.saves = json.load(f)
		except:
			self.saves={}
			pass
		if len(self.saves)!=0:
			for save_name in self.saves.keys():
				label = Gtk.Label()
				label.set_text(save_name)
				label.show()
				self.lb.add(label)
				self.remove_btn.set_sensitive(1)
		else:
			self.load_btn.set_sensitive(0)
	def sanitizeEntry(self, entry):
		pass
		#for character in entry.get_text():
		#	if character in "\"\'"
	def show(self):
		self.window.show()

	def save(self, top):
		top.builder.get_object("save_dialog").show()
		def save():
			name = self.dialog_save_entry.get_text()
			self.saves[name] = top.data
			with open("saved_configurations.json", "w") as f:
				json.dump(self.saves, f)
			top.builder.get_object("save_dialog").hide()
			self.refreshSaves()
			self.dialog_save.disconnect(dialog_save_handler_id)
			self.remove_btn.set_sensitive(1)
			self.load_btn.set_sensitive(1)
		dialog_save_handler_id = self.dialog_save.connect("clicked", lambda _: save())

	def load(self, top):
		save = self.saves[self.lb.get_selected_row().get_child().get_text()]
		top.data=save
		top.updatePage()
#		for device in save.values():
#			for channel in device.keys():
#				if channel == top.channel:
#					channel_data = device[channel]
#					for page in top.pages:
#						channel_page_data = list(channel_data[page.name].values())
#						page.setOpts(top, *channel_page_data[1:])
#						page.setColours(channel_page_data[0])
	def remove(self, btn):
		if len(self.saves)==1:
			btn.set_sensitive(0)
			self.load_btn.set_sensitive(0)
		row=self.lb.get_selected_row()
		if row==None:
			row=self.lb.get_children()[-1]
		self.lb.remove(row)
		row = row.get_child().get_text()
		del self.saves[row]

	def exit(self):
		with open("saved_configurations.json", "w") as f:
			json.dump(self.saves, f)
		self.window.hide()
if __name__ == "__main__":
	main = Main()
	Gtk.main()
