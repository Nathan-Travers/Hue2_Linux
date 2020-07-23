#!/bin/python
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from liquidctl import driver
from math import ceil
from json import dump, load
from copy import deepcopy

class Main:
	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("Hue2_Linux_GUI.glade")

		window = self.builder.get_object("window")
		refresh_button = self.builder.get_object("refresh")
		profiles = self.builder.get_object("profiles_btn")
		copy_channel_btn = self.builder.get_object("copy_channel")
		device_combo_box = self.builder.get_object("device")
		self.device_channel_combo_box = self.builder.get_object("device_channel")
		self.device_channel_entry = self.builder.get_object("device_channel_entry")
		self.device_list = self.builder.get_object("device_liststore")
		self.device_entry = self.builder.get_object("device_entry")
		self.speed = self.builder.get_object("speed")

		window.connect("delete-event", Gtk.main_quit)
		device_combo_box.connect("changed", self.on_device_change)
		refresh_button.connect("clicked", lambda _: self.refresh_devices())

		def _profiles_popup(_):
			self.save_device_state()
			self.pages["profiles"].show()
		def _copy_channel_popover(_):
			self.pages["copy_menu"].show(self)
		profiles.connect("clicked", _profiles_popup)
		copy_channel_btn.connect("clicked", _copy_channel_popover)

		self.device_channel_combo_box_handler_id = self.device_channel_combo_box.connect("changed", self.on_device_channel_change)
		self.pages={"per_led": PerLed(self),
			    "animations": Animations(self),
			    "presets":Presets(self),
			    "profiles":Profiles(self),
			    "copy_menu":CopyPopover(self)}
		self.buttons_to_disable = [self.pages["per_led"].grouping_cb, self.pages["per_led"].breathing_cb, self.pages["per_led"].apply, self.pages["animations"].apply, self.pages["presets"].apply]
		self.speeds, self.mode = ["slowest","slower","normal","faster","fastest"], "super-fixed"

		self.refresh_devices()
		window.show()
	def save_device_state(self):
		self.data[self.device][self.channel] = {"per_led": {
			"colours":self.pages["per_led"].get_colours(),
			"group_size":self.pages["per_led"].group_size,
			"speed":self.speed.get_value(),
			"breathing":(self.mode=="super-breathing")}}

		mode, length, backwards = self.pages["animations"].get_opts()
		self.data[self.device][self.channel]["animations"] = {
			"colours":self.pages["animations"].get_colours(),
			"mode":mode,
			"length":length,
			"backwards":backwards}
	def get_hue2_devices(self):
		self.devices, self.data={}, {}
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
			for channel in self.devices[device_name]["channels"]:
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

	def set_led(self, *colours, speed=2, backwards=0, sync=0):
		true_colours=[]
		for colour in colours:
			for _ in range(self.pages["per_led"].group_size):
				true_colours.append(colour)
		speed=self.speeds[int(self.speed.get_value())-1]
		if sync==0:
			self.devices[self.device]["device"].set_color(self.channel, self.mode, true_colours, speed=speed)
		else:
			for channel in self.channels:
				self.devices[self.device]["device"].set_color(channel, self.mode, true_colours, speed=speed)
	def refresh_devices(self):
		self.device_list.clear()
		self.device_entry.set_text("")
		self.device_channel_entry.set_text("")

		for button in self.buttons_to_disable:
			button.set_sensitive(0)
		for row in range(5):
			self.pages["per_led"].led_grid.remove_row(0)

		self.get_hue2_devices()
		for device in self.devices.keys():
			self.device_list.append([device])
		self.device=self.device_list[0][0]
		self.channel = list(self.devices[device]["channels"].keys())[0]
	def on_device_channel_change(self, combo_box):
		self.save_device_state()
		self.channel = combo_box.get_child().get_text()
		self.update_page()
	def update_page(self):
		per_led_page_data, animations_page_data = (list(item.values()) for item in self.data[self.device][self.channel].values())
		self.pages["animations"].set_opts(self, *animations_page_data)
		self.pages["per_led"].set_opts(self, *per_led_page_data)
	def on_device_change(self, combo_box):
		self.device_channel_combo_box.disconnect(self.device_channel_combo_box_handler_id)
		self.save_device_state()
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
			self.update_page()
		updateChannels()

		for btn in self.pages["per_led"].led_buttons:
			btn.set_rgba(Gdk.RGBA(1,1,1,1))
		for button in self.buttons_to_disable:
			button.set_sensitive(1)
		self.device_channel_combo_box_handler_id = self.device_channel_combo_box.connect("changed", self.on_device_channel_change)
		self.on_device_channel_change(self.device_channel_combo_box)


class Presets(Main):
	def __init__(self, top):
		self._menu = top.builder.get_object("presets_menu")
		self._backwards_btn = top.builder.get_object("presets_direction_b")
		self.apply = top.builder.get_object("presets_apply")

		self.apply.connect("clicked", lambda _: self._on_apply(top))

	def _on_apply(self, top):
		top.mode = self._menu.get_selected_row().get_children()[0].get_label().lower().replace(" ","-")
		top.mode = ("backwards-"*self._backwards_btn.get_active())+top.mode
		top.set_led([0,0,0]) #have to pass empty colours due to error in library coding

class PerLed(Main):
	def __init__(self, top):
		self.grouping_cb = top.builder.get_object("grouping_checkbox")
		self.breathing_cb = top.builder.get_object("breathing_checkbox")
		self.apply = top.builder.get_object("per_led_apply")
		self.led_grid = top.builder.get_object("led_grid")
		self.breathing_speed_scale = top.builder.get_object("breathing_speed_scale")
		self.group_size_entry = top.builder.get_object("group_size")

		self.grouping_cb.connect("clicked", lambda cb: self.on_grouping_cb_toggle(top, cb))
		self.breathing_cb.connect("clicked", lambda cb: self.on_breathing_cb_toggle(top, cb))
		self.apply.connect("clicked", lambda _: self.on_apply(top))

		self.group_size, self.led_len = 1, (0,0)
		self.x, self.y = -1, 0
		self.led_buttons = []
		self.name = "per_led"
	def on_breathing_cb_toggle(self, top, cb):
		if cb.get_active() == 1:
			top.mode = "super-breathing"
			self.breathing_speed_scale.set_visible(1)
		else:
			self.breathing_speed_scale.set_visible(0)
			top.mode = "super-fixed"
	def on_grouping_cb_toggle(self, top, cb):
		if cb.get_active()==0:
			self.group_size_entry.set_visible(0)
			self.group_size_entry.disconnect(self.group_size_handler_id)
			self.group_size=1
			self.update_led_grid()
		else:
			self.group_size_entry.set_visible(1)
			self.group_size_handler_id = self.group_size_entry.connect("changed", self.on_group_size_change)
			try:
				self.group_size = int(self.group_size_entry.get_text())
				self.update_led_grid()
			except ValueError:
				pass
	def on_group_size_change(self, group_size_entry):
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
				self.update_led_grid()
		except ValueError:
			pass
		group_size_entry.set_text(buffer)
	def update_led_grid(self):
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
	def get_colours(self):
		colours = []
		for button in self.led_buttons:
			colour = []
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour.append(rgb_channel)
			colours.append(colour)
		return(colours)
	def on_apply(self, top):
		if "super" not in top.mode:
			top.mode="super-fixed"
		top.set_led(*self.get_colours())
	def set_opts(self, top, colours, group_size, speed, breathing):
		for button, colour in zip(self.led_buttons, colours):
			colour_float=[]
			for channel in colour:
				colour_float.append(channel/255)
			button.set_rgba(Gdk.RGBA(*colour_float))
		self.channel_len = top.channels[top.channel]
		self.update_led_grid()
		self.group_size_entry.set_text(str(group_size))
		self.grouping_cb.set_active((group_size>1))
		self.breathing_cb.set_active(breathing)
		top.speed.set_value(speed)

class Animations(Main):
	def __init__(self, top):
		self.remove_colour_btn = top.builder.get_object("remove_colour")
		self.add_colour_btn = top.builder.get_object("add_colour")
		self.apply = top.builder.get_object("animations_apply")
		self.marquee_rb = top.builder.get_object("marquee_rb")
		self.custom_colours = top.builder.get_object("custom_colours")
		self.backwards_btn = top.builder.get_object("animations_direction_b")
		self.length_scale = top.builder.get_object("length_scale")

		self.remove_colour_btn.connect("clicked", self.on_remove)
		self.add_colour_btn.connect("clicked", lambda btn: self.on_add(btn, self.remove_colour))
		self.apply.connect("clicked", lambda _: self.on_apply(top))
		self.marquee_rb.connect("clicked", lambda btn: self.on_marquee_select(top, btn))

		self.custom_colours.x, self.custom_colours.y, self.custom_colours.buttons = 0, 0, []
		self.radio_buttons = top.builder.get_object("animations_mode_rb").get_group()[::-1]
		self.name = "animations"
	def remove_colour(self):
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
	def on_remove(self, btn):
		self.add_colour_btn.set_sensitive(1)
		self.remove_colour()
		if len(self.custom_colours.buttons)==0:
			btn.set_sensitive(0)
	def add_colour(self):
		if self.custom_colours.x!=2:
			self.custom_colours.buttons.append(Gtk.ColorButton())
			self.custom_colours.attach(self.custom_colours.buttons[-1],self.custom_colours.x,self.custom_colours.y,1,1)
			self.custom_colours.buttons[-1].set_rgba(Gdk.RGBA(1,1,1,1))
			self.custom_colours.buttons[-1].show()
			self.custom_colours.y+=1
			if self.custom_colours.y==4:
				self.custom_colours.y=0
				self.custom_colours.x+=1
	def on_add(self, btn_self, btn):
		btn.set_sensitive(1)
		if self.custom_colours.x==2:
			btn_self.set_sensitive(0)
		self.add_colour()
	def on_marquee_select(self, top, btn):
		self.length_scale.set_visible(btn.get_active())
		top.builder.get_object("animations_directions").set_visible(btn.get_active())
	def get_opts(self):
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
	def get_colours(self):
		colours = []
		for button in self.custom_colours.buttons:
			colour = []
			for ind, rgb_channel in enumerate(button.get_rgba()):
				if ind !=3:
					rgb_channel = int(rgb_channel*255)
					colour.append(rgb_channel)
			colours.append(colour)
		return(colours)
	def on_apply(self, top):
		top.mode = self.get_opts()[0]
		top.set_led(*self.get_colours())
	def set_opts(self, top, colours, mode, length, backwards):
		def setColours():
			buttons_len = len(self.custom_colours.buttons)
			colours_len = len(colours)
			if buttons_len<colours_len:
				for _ in range(colours_len-buttons_len):
					self.add_colour()
			elif buttons_len>colours_len:
				for _ in range(buttons_len-colours_len):
					self.remove_colour()
			buttons_len = len(self.custom_colours.buttons)
			if buttons_len<1:
				self.remove_colour_btn.set_sensitive(0)
			else:
				self.remove_colour_btn.set_sensitive(1)
			if buttons_len==8:
				self.add_colour_btn.set_sensitive(0)
			for button, colour in zip(self.custom_colours.buttons, colours):
				colour_float=[]
				for channel in colour:
					colour_float.append(channel/255)
					button.set_rgba(Gdk.RGBA(*colour_float))
		setColours()
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
		self.exit_btn.connect("clicked", lambda _: self.exit(top))

		self.refresh_saves()

	def refresh_saves(self):
		for child in self.lb.get_children():
			self.lb.remove(child)
		try:
			with open("saved_configurations.json", "r") as f:
				self.saves = load(f)
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
	def show(self):
		self.window.show()
	def save(self, top):
		top.builder.get_object("save_dialog").show()
		def save():
			name = self.dialog_save_entry.get_text()
			self.saves[name] = deepcopy(top.data)
			with open("saved_configurations.json", "w") as f:
				dump(self.saves, f)
			top.builder.get_object("save_dialog").hide()
			self.refresh_saves()
			self.dialog_save.disconnect(dialog_save_handler_id)
			self.remove_btn.set_sensitive(1)
			self.load_btn.set_sensitive(1)
		dialog_save_handler_id = self.dialog_save.connect("clicked", lambda _: save())
		row = self.lb.get_selected_row()
		if row !=None:
			self.dialog_save_entry.set_text(row.get_child().get_text())
			self.dialog_save_entry.select_region(0,-1)
	def load(self, top):
		save = self.saves[self.lb.get_selected_row().get_child().get_text()]
		top.data=deepcopy(save)
		top.update_page()
	def remove(self, btn):
		row=self.lb.get_selected_row()
		if row!=None:
			self.lb.remove(row)
			row = row.get_child().get_text()
			del self.saves[row]
		if len(self.saves)==0:
			btn.set_sensitive(0)
			self.load_btn.set_sensitive(0)
		else:
			self.lb.select_row(self.lb.get_children()[-1])
	def exit(self,top):
		with open("saved_configurations.json", "w") as f:
			dump(self.saves, f)
		self.window.hide()


class CopyPopover(Main):
	def __init__(self, top):
		self.popover = top.builder.get_object("copy_popover")
		self._lb = top.builder.get_object("copy_dialog_lb")
		self._lb.handler_id = self._lb.connect("row-selected", lambda _, row: self._on_select(top, row))
	def show(self, top):
		def addRow(text):
			label = Gtk.Label()
			label.set_text(text)
			label.show()
			self._lb.add(label)
		for child in self._lb.get_children():
			self._lb.remove(child)
		self.devices, pos = {}, -1
		for device in top.data:
			addRow(device)
			pos+=1
			self.devices[pos] = device
			for channel in list(top.data[device].keys()):
				addRow(channel)
				pos+=1
		self.devices[pos+1] = list(self.devices.values())[-1]
	def _on_select(self, top, row):
		if row!=None:
			if row.get_child().get_text() in list(top.devices.keys()): #lazy evaluation stops AttributeError
				self._lb.unselect_row(row)
			else:
				self._copy(top)
				self.popover.hide()
	def _copy(self, top):
		selected_row = self._lb.get_selected_row()
		for ind, pos in enumerate(self.devices.keys()):
			if selected_row.get_index() < pos:
				device = list(self.devices.values())[ind-1]
				top.data[top.device][top.channel] = top.data[device][selected_row.get_child().get_text()]
				break
		top.update_page()


if __name__ == "__main__":
	main = Main()
	Gtk.main()
