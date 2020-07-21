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
		profiles.connect("clicked", lambda _: self.profilesPopup(self))

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
		window.show()

	def profilesPopup(self, top):
		top.profiles.show()
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

	def setLed(self, *colours, backwards=0):
		if backwards:
			if self.mode!="covering-marquee":
				self.mode = "backwards-"+self.mode
			else:
				self.mode = "covering-backwards-marquee" #the only mode that doesn't prefix "backwards-"
		self.devices[self.device]["device"].set_color(self.channel,self.mode, colours)

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

	def onDeviceChannelChange(self, combo_box):
		try:
			self.channel = combo_box.get_child().get_text()
			self.per_led_page.channel_len = self.channels[self.channel]
			self.per_led_page.led_len = (self.per_led_page.led_len[1], self.per_led_page.channel_len)
			self.per_led_page.updateLedGrid()
			self.data[self.device][self.channel] = {"animations":self.animations_page.getColours(),
						"per_led":self.per_led_page.getColours()}
		except KeyError:
			pass

	def onDeviceChange(self, combo_box):
		self.device_channel_combo_box.disconnect(self.dcc)
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
			self.data[self.device][self.channel] = {"animations":self.animations_page.getColours(),
						"per_led":self.per_led_page.getColours()}
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
		self.setLed([0,0,0], backwards=self.builder.get_object("presets_direction_b").get_active()) #have to pass empty colours due to error in library coding

class Per_led(Main):
	def __init__(self, top):
		self.grouping_cb = top.builder.get_object("grouping_checkbox")
		self.breathing_cb = top.builder.get_object("breathing_checkbox")
		self.apply = top.builder.get_object("per_led_apply")
		self.led_grid = top.builder.get_object("led_grid")

		self.grouping_cb.connect("clicked", lambda cb: self.onGroupingCbToggled(top, cb))
		self.breathing_cb.connect("clicked", lambda cb: self.onBreathingCbToggled(top, cb))
		self.apply.connect("clicked", lambda _: self.onApply(top))

		self.group_size, self.led_len = 1, (0,0)
		self.x, self.y = -1, 0
		self.led_buttons = []

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
			#self.group_size=1
		else:
			group_size_entry.set_visible(1)
			self.group_size_handler_id = group_size_entry.connect("changed", self.onGroupSizeChanged)
			try:
				top.group_size = int(group_size_entry.get_text())
			except ValueError:
				pass

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
				self.led_len = (self.led_len[1], ceil(self.channel_len//buffer_int))
				self.updateLedGrid()
		except ValueError:
			pass
		group_size_entry.set_text(buffer)

	def updateLedGrid(self):
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
			for _ in range(self.group_size):
				colours.append(colour)
		return(colours)

	def onApply(self, top):
		if "super" not in top.mode:
			top.mode="super-fixed"
		top.setLed(*self.getColours())
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

		remove_colour.connect("clicked", self.onRemove)
		self.add_colour.connect("clicked", lambda btn: self.onAdd(btn, remove_colour))
		self.apply.connect("clicked", lambda _: self.onApply(top))
		self.marquee_rb.connect("clicked", lambda btn: self.onMarqueeSelected(top, btn))

		self.custom_colours.x, self.custom_colours.y, self.custom_colours.buttons = 0, 0, []

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
	def onRemove(self):
		self.add_colour.set_sensitive(1)
		if len(self.custom_colours.buttons)==0:
			btn.set_sensitive(0)

	def addColour(self):
		if self.custom_colours.x!=2:
			self.custom_colours.buttons.append(Gtk.ColorButton())
			self.custom_colours.attach(self.custom_colours.buttons[-1],self.custom_colours.x,self.custom_colours.y,1,1)
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

	def onMarqueeSelected(self, top, btn):
		length_scale = top.builder.get_object("length_scale")
		length_scale.set_visible(btn.get_active())
		top.builder.get_object("animations_directions").set_visible(btn.get_active())

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
		length = int(top.builder.get_object('length').get_value())
		colours, backwards = self.getColours(), 0
		for radio_button in top.builder.get_object("animations_mode_rb").get_group():
			if radio_button.get_active()==1:
				top.mode = radio_button.get_label().lower()
				break
		if top.mode=="marquee":
			backwards = top.builder.get_object("animations_direction_b").get_active()
			if len(self.custom_colours.buttons)<2:
				top.mode=f"marquee-{length}"
			else:
				top.mode=f"covering-marquee"
		top.setLed(*colours, backwards=backwards)
	def setColours(self, colours):
		if len(self.custom_colours.buttons)<len(colours):
			for _ in range(len(colours)-len(self.custom_colours.buttons)):
				self.addColour()
		for button, colour in zip(self.custom_colours.buttons, colours):
			colour_float=[]
			for channel in colour:
				colour_float.append(channel/255)
			button.set_rgba(Gdk.RGBA(*colour_float))

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
		self.remove_btn.connect("clicked", lambda _: self.remove())
		self.exit_btn.connect("clicked", lambda _: self.exit())
		self.dialog_save_entry.connect("changed", self.sanitizeEntry)

		self.refreshSaves()

	def refreshSaves(self):
		for child in self.lb.get_children():
			self.lb.remove(child)
		try:
			with open("saved_configurations.json", "r") as f:
				self.saves = json.load(f)
			for save_name in self.saves.keys():
				label = Gtk.Label()
				label.set_text(save_name)
				label.show()
				self.lb.add(label)
		except:
			self.saves={}
			pass

	def sanitizeEntry(self, entry):
		pass
#		for character in entry.get_text():
#			if character in "\"\'
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
		self.dialog_save.connect("clicked", lambda _: save())

	def load(self, top):
		for item in self.saves[self.lb.get_selected_row().get_child().get_text()].items():
				page, colours = item
				page = {"per_led":0,
				"animations":1}.get(page)
				top.pages[page].setColours(colours)
	def remove(self):
		row=self.lb.get_selected_row()
		del self.saves[row.get_child().get_text()]
		self.lb.remove(row)

	def exit(self):
		with open("saved_configurations.json", "w") as f:
			json.dump(self.saves, f)
		self.window.hide()
if __name__ == "__main__":
	main = Main()
	Gtk.main()
