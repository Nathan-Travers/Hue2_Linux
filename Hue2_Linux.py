#!/bin/python
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from liquidctl import driver
from math import ceil
from json import dump, load
from copy import deepcopy
from subprocess import check_output
from os.path import join

class Main:
	def __init__(self, file_):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(file_)

		window = self.builder.get_object("window")
		refresh_btn = self.builder.get_object("refresh")
		profiles_btn = self.builder.get_object("profiles_btn")
		copy_channel_btn = self.builder.get_object("copy_channel")
		device_combo_box = self.builder.get_object("device")
		mode_page_selector = self.builder.get_object("mode_page_selector")
		su_error = self.builder.get_object("su_error")
		su_error_exit_btn = self.builder.get_object("su_error_exit")
		self._device_channel_combo_box = self.builder.get_object("device_channel")
		self._device_entry = self.builder.get_object("device_entry")
		self._device_channel_entry = self.builder.get_object("device_channel_entry")
		self._device_list = self.builder.get_object("device_liststore")
		self._device_channel_list = self.builder.get_object("device_channel_liststore")
		self.speed = self.builder.get_object("speed")

		def profiles_popup(_):
			self._save_device_state()
			self.pages["profiles"].show()
		def copy_channel_popover(_):
			self.pages["copy_menu"].show(self)
		def on_mode_page_select(scrl_wndw):
			if scrl_wndw == None:
				return
			viewport = scrl_wndw.get_child()
			lb_row = viewport.get_child().get_focus_child()
			if lb_row.get_child().get_text()=="Preset animations":
				copy_channel_btn.set_visible(0)
			else:
				copy_channel_btn.set_visible(1)

		window.connect("delete-event", Gtk.main_quit)
		refresh_btn.connect("clicked", lambda _: self._refresh_devices())
		profiles_btn.connect("clicked", profiles_popup)
		copy_channel_btn.connect("clicked", copy_channel_popover)
		device_combo_box.connect("changed", self._on_device_change)
		mode_page_selector.connect("set-focus-child", lambda _, scrl_wndw: on_mode_page_select(scrl_wndw))
		su_error_exit_btn.connect("clicked", Gtk.main_quit)
		self._device_channel_combo_box_handler_id = self._device_channel_combo_box.connect("changed", self._on_device_channel_change)

		self.pages={"per_led": PerLed(self),
			    "animations": Animations(self),
			    "presets":Presets(self),
			    "profiles":Profiles(self),
			    "copy_menu":CopyPopover(self)}
		self._btns_to_disable = [self.pages["per_led"].grouping_cb, self.pages["per_led"].breathing_cb, self.pages["per_led"].apply, self.pages["animations"].apply, self.pages["presets"].apply]
		self._speeds = ["slowest","slower","normal","faster","fastest"]
		self.mode = "super-fixed"

		if check_output("whoami")==b"root\n":
			self._refresh_devices()
		else:
			su_error.show()
		window.show()
	def _get_devices(self):
		for device in driver.find_liquidctl_devices():
			device.connect()
			device_info = device.initialize()
			device_name = device.description.replace(" (experimental)", "")
			self.devices[device_name] = {"device": device,
 						     "version": device_info[0][1],
						     "channels": {}}
			self.data[device_name] = {}
			device_channels = self.devices[device_name]["channels"]
			for line in device_info[1:]:
				channel = line[0][:5].lower().replace(" ","")
				if channel not in device_channels:
					device_channels[channel] = []
					self.data[device_name][channel] = {
						"per_led": {
							"colours":[[255]*3]*40,
							"group_size":1,
							"speed":3.0,
							"breathing":0},
						"animations": {
							"colours":[],
							"mode":"fading",
							"length":3.0,
							"backwards":0}}
				length = int(line[1][-6:-3])
				if length == 300:
					device_channels[channel].append(10)
				elif length == 250:
					device_channels[channel].append(8)
			for ind in range(len(device_channels)):
				prev = list(device_channels.keys())[ind]
				while len(device_channels[prev])!=4:
					device_channels[prev].append(0)

	def _refresh_devices(self):
		self.devices = {}
		self.data = {}
		self._device_list.clear()
		self._device_entry.set_text("")
		self._device_channel_entry.set_text("")
		for row in range(5):
			self.pages["per_led"].led_grid.remove_row(0)

		for btn in self._btns_to_disable:
			btn.set_sensitive(0)

		self._get_devices()
		for device in self.devices.keys():
			self._device_list.append([device])
		self.device=self._device_list[0][0]
		self.channel = list(self.devices[device]["channels"].keys())[0]
	def _save_device_state(self):
		mode, length, backwards = self.pages["animations"].get_opts()
		self.data[self.device][self.channel] = {"per_led": {
			"colours":self.pages["per_led"].get_colours(),
			"group_size":self.pages["per_led"].group_size,
			"speed":self.speed.get_value(),
			"breathing":(self.mode=="super-breathing")},
							"animations": {
			"colours":self.pages["animations"].get_colours(),
			"mode":mode,
			"length":length,
			"backwards":backwards}}
	def _on_device_change(self, combo_box):
		self._device_channel_combo_box.disconnect(self._device_channel_combo_box_handler_id)
		self._save_device_state()
		def updateChannels():
			self._device_channel_list.clear()
			device = combo_box.get_child().get_text()
			if device!="": #edgecase on refresh
				self.channels = self.devices[device]["channels"]
				channel_names = list(self.channels.keys())
				for channel in channel_names:
					self._device_channel_list.append([channel])
				self.channel=channel_names[0]
				self._device_channel_entry.set_text(self.channel)
				self.device = device
		updateChannels()
		self.update_page()

		for button in self._btns_to_disable:
			button.set_sensitive(1)
		self._device_channel_combo_box_handler_id = self._device_channel_combo_box.connect("changed", self._on_device_channel_change)
	def _on_device_channel_change(self, combo_box):
		self._save_device_state()
		self.channel = combo_box.get_child().get_text()
		self.update_page()
	def update_page(self):
		per_led_page_data, animations_page_data = (list(item.values()) for item in self.data[self.device][self.channel].values())
		self.pages["animations"].set_opts(*animations_page_data)
		self.pages["per_led"].set_opts(self, *per_led_page_data)
	def set_led(self, *colours, speed=2, backwards=0, sync=0):
		speed=self._speeds[int(self.speed.get_value())-1]
		if sync==0:
			self.devices[self.device]["device"].set_color(self.channel, self.mode, colours, speed=speed)
		else:
			for channel in self.channels:
				self.devices[self.device]["device"].set_color(channel, self.mode, colours, speed=speed)

class Presets(Main):
	def __init__(self, top):
		self._menu = top.builder.get_object("presets_menu")
		self._backwards_btn = top.builder.get_object("presets_direction_b")
		self.apply = top.builder.get_object("presets_apply")

		self.apply.connect("clicked", lambda _: self._on_apply(top))

	def _on_apply(self, top):
		top.mode = self._menu.get_selected_row().get_child().get_label().lower().replace(" ","-")
		top.mode = ("backwards-"*self._backwards_btn.get_active())+top.mode
		top.set_led([0,0,0]) #have to pass empty colours due to error in library coding

class PerLed(Main):
	def __init__(self, top):
		self.grouping_cb = top.builder.get_object("grouping_checkbox")
		self.breathing_cb = top.builder.get_object("breathing_checkbox")
		self.apply = top.builder.get_object("per_led_apply")
		self.led_grid = top.builder.get_object("led_grid")
		self._speed_scale = top.builder.get_object("breathing_speed_scale")
		self._group_size_entry = top.builder.get_object("group_size")

		self.grouping_cb.connect("clicked", lambda cb: self._on_grouping_cb_toggle(top, cb))
		self.breathing_cb.connect("clicked", lambda cb: self._on_breathing_cb_toggle(top, cb))
		self.apply.connect("clicked", lambda _: self._on_apply(top))

		self.name = "per_led"
		self.group_size = 1
		self.led_strip_lens = []
		self._led_grid_rows = [[],[],[],[]]
	def _update_led_grid(self):
		row = -1
		for led_strip_len in self.led_strip_lens:
			row+=1
			row_len=len(self._led_grid_rows[row])
			new_row_len=ceil(led_strip_len/self.group_size)
			if new_row_len!=row_len: #check equal first for fewer comparisons
				if new_row_len>row_len:
					for led_count, led in enumerate(range(new_row_len-row_len)):
						btn = Gtk.ColorButton()
						self._led_grid_rows[row].append(btn)
						btn.set_rgba(Gdk.RGBA(1,1,1,1))
						self.led_grid.attach(btn,(row_len+led_count),row,1,1)
						btn.show()
				else:
					for btn in self._led_grid_rows[row][:new_row_len:-1]:
						btn.destroy()
						del self._led_grid_rows[row][-1]
					self._led_grid_rows[row][-1].destroy()
					del self._led_grid_rows[row][-1]
	def _on_breathing_cb_toggle(self, top, cb):
		if cb.get_active() == 1:
			top.mode = "super-breathing"
			self._speed_scale.set_visible(1)
		else:
			self._speed_scale.set_visible(0)
			top.mode = "super-fixed"
	def _on_grouping_cb_toggle(self, top, cb):
		if cb.get_active()==0:
			self._group_size_entry.set_visible(0)
			self._group_size_entry.disconnect(self._group_size_handler_id)
			self.group_size=1
			self._update_led_grid()
		else:
			self._group_size_entry.set_visible(1)
			self._group_size_handler_id = self._group_size_entry.connect("changed", self._on_group_size_change)
			try:
				self.group_size = int(self._group_size_entry.get_text())
				self._update_led_grid()
			except ValueError:
				pass
	def _on_group_size_change(self, _group_size_entry):
		group_size = _group_size_entry.get_text()
		buffer = ""
		for letter in group_size:
			if letter in "0123456789":
				buffer += letter
		try:
			buffer_int = int(buffer)
			if buffer_int > 10:
				buffer = "10"
			elif len(buffer)>2:
				buffer = buffer[:2]
			elif buffer_int!=0:
				self.group_size = buffer_int
				self._update_led_grid()
		except ValueError:
			pass
		_group_size_entry.set_text(buffer)
	def _on_apply(self, top):
		if "super" not in top.mode:
			top.mode="super-fixed"
		top.set_led(*self.get_colours())
	def get_colours(self):
		colours = []
		for button in [led for row in self._led_grid_rows for led in row]:
			colour = []
			for rgb_channel in list(button.get_rgba())[:3]:
				rgb_channel = int(rgb_channel*255)
				colour.append(rgb_channel)
			for _ in range(self.group_size):
				colours.append(colour)
		return(colours)
	def set_opts(self, top, colours, group_size, speed, breathing):
		self.led_strip_lens = top.channels[top.channel]
		self._update_led_grid()
		for button, colour in zip([led for row in self._led_grid_rows for led in row], colours):
			colour_float=[]
			for channel in colour:
				colour_float.append(channel/255)
			button.set_rgba(Gdk.RGBA(*colour_float))
		self._group_size_entry.set_text(str(group_size))
		self.grouping_cb.set_active((group_size>1))
		self.breathing_cb.set_active(breathing)
		top.speed.set_value(speed)

class Animations(Main):
	def __init__(self, top):
		self._remove_colour_btn = top.builder.get_object("remove_colour")
		self._add_colour_btn = top.builder.get_object("add_colour")
		self.apply = top.builder.get_object("animations_apply")
		self.marquee_rb = top.builder.get_object("marquee_rb")
		self.custom_colours = top.builder.get_object("custom_colours")
		self.backwards_btn = top.builder.get_object("animations_direction_b")
		self.length_scale = top.builder.get_object("length_scale")
		self._length = top.builder.get_object("length")


		self._remove_colour_btn.connect("clicked", self._on_remove)
		self._add_colour_btn.connect("clicked", lambda btn: self._on_add(btn, self._remove_colour_btn))
		self.apply.connect("clicked", lambda _: self._on_apply(top))
		self.marquee_rb.connect("clicked", lambda btn: self._on_marquee_select(top, btn))

		self.custom_colours.x, self.custom_colours.y, self.custom_colours.buttons = 0, 0, []
		self.radio_buttons = top.builder.get_object("animations_mode_rb").get_group()[::-1]
		self.name = "animations"
	def _remove_colour(self):
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
	def _add_colour(self):
		if self.custom_colours.x!=2:
			self.custom_colours.buttons.append(Gtk.ColorButton())
			self.custom_colours.attach(self.custom_colours.buttons[-1],self.custom_colours.x,self.custom_colours.y,1,1)
			self.custom_colours.buttons[-1].set_rgba(Gdk.RGBA(1,1,1,1))
			self.custom_colours.buttons[-1].show()
			self.custom_colours.y+=1
			if self.custom_colours.y==4:
				self.custom_colours.y=0
				self.custom_colours.x+=1
	def _on_remove(self, btn):
		self._add_colour_btn.set_sensitive(1)
		self._remove_colour()
		if len(self.custom_colours.buttons)==0:
			btn.set_sensitive(0)
	def _on_add(self, btn_self, btn):
		btn.set_sensitive(1)
		if self.custom_colours.x==2:
			btn_self.set_sensitive(0)
		self._add_colour()
	def _on_marquee_select(self, top, btn):
		self.length_scale.set_visible(btn.get_active())
		top.builder.get_object("animations_directions").set_visible(btn.get_active())
	def _on_apply(self, top):
		top.mode = self.get_opts()[0]
		top.set_led(*self.get_colours())
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
	def set_opts(self, colours, mode, length, backwards):
		def setColours():
			buttons_len = len(self.custom_colours.buttons)
			colours_len = len(colours)
			if buttons_len<colours_len:
				for _ in range(colours_len-buttons_len):
					self._add_colour()
			elif buttons_len>colours_len:
				for _ in range(buttons_len-colours_len):
					self._remove_colour()
			buttons_len = len(self.custom_colours.buttons)
			if buttons_len<1:
				self._remove_colour_btn.set_sensitive(0)
			else:
				self._remove_colour_btn.set_sensitive(1)
			if buttons_len==8:
				self._add_colour_btn.set_sensitive(0)
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
		self._length.set_value(length)
		self.backwards_btn.set_active(backwards)

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
		self.save_dialog = top.builder.get_object("save_dialog")
		cancel_dialog = top.builder.get_object("dialog_cancel")

		cancel_dialog.connect("clicked", lambda _: top.builder.get_object("save_dialog").hide())

		self.save_btn.connect("clicked", lambda _: self._save(top))
		self.load_btn.connect("clicked", lambda _: self._load(top))
		self.remove_btn.connect("clicked", self._remove)
		self.exit_btn.connect("clicked", lambda _: self._exit(top))

		self._refresh_saves()

	def _refresh_saves(self):
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
	def _save(self, top):
		self.save_dialog.show()
		def save():
			name = self.dialog_save_entry.get_text()
			self.saves[name] = deepcopy(top.data)
			with open("saved_configurations.json", "w") as f:
				dump(self.saves, f)
				self.save_dialog.hide()
			self._refresh_saves()
			self.dialog_save.disconnect(dialog_save_handler_id)
			self.remove_btn.set_sensitive(1)
			self.load_btn.set_sensitive(1)
		dialog_save_handler_id = self.dialog_save.connect("clicked", lambda _: save())
		row = self.lb.get_selected_row()
		if row !=None:
			self.dialog_save_entry.set_text(row.get_child().get_text())
			self.dialog_save_entry.select_region(0,-1)
	def _load(self, top):
		save = self.saves[self.lb.get_selected_row().get_child().get_text()]
		top.data=deepcopy(save)
		top.update_page()
	def _remove(self, btn):
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
	def _exit(self,top):
		with open("saved_configurations.json", "w") as f:
			dump(self.saves, f)
		self.window.hide()
	def show(self):
		self.window.show()
class CopyPopover(Main):
	def __init__(self, top):
		self._lb = top.builder.get_object("copy_dialog_lb")
		self._lb.handler_id = self._lb.connect("row-selected", lambda _, row: self._on_select(top, row))
		self.popover = top.builder.get_object("copy_popover")
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


if __name__ == "__main__":
	file_ = "Hue2_Linux_GUI.glade"
	try: #for pyinstaller compiled exe
		from sys import _MEIPASS
		file_ = (join(_MEIPASS, "glade/Hue2_Linux_GUI.glade"))
	except ImportError:
		pass
	main = Main(file_)
	Gtk.main()
