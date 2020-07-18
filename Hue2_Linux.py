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
		self.builder.add_from_file("LEDtig.glade")

		window = self.builder.get_object("window")
		window.connect("delete-event", Gtk.main_quit)
		window.show()

		device_list = self.builder.get_object("device_liststore")
		info = self.getHue2Info()
		for device, channels in info:
			device_list.append([device])

		led_grid = self.builder.get_object("led_grid")
		self.cl_button = Gtk.ColorButton()
		self.cl_button.set_size_request(50,0)
		self.cl_button1 = Gtk.ColorButton()
		led_grid.attach(self.cl_button,0,0,1,1)
		self.cl_button.show()
		led_grid.attach(self.cl_button1,0,1,1,1)
		self.cl_button1.show()

	def getHue2Info(self):
		response, channels, channel, devices, count = check_output("liquidctl initialize all", shell=1), [["", 0]], "", [], 0
		for line in response.decode("utf-8").split("\n"):
			if "N" in line:
				devices.append([line.split(" (")[0], []])
			try:
				channel = re.search("LED \d", line).group(0)
				if channel != channels[-1][0]:
					channels.append(["", 0])
					channels[-1][0] = channel
					devices[-1][1].append(channels[-1])

				length = int(re.search("\d{3}", line).group(0))
				if length == 300:
					count += 10
				elif length == 250:
					count += 8
				channels[-1][1] = channels[-1][1] + count
				count = 0
			except AttributeError:
				pass
		del channels		
		return(devices)

if __name__ == "__main__":
	main = Main()
	Gtk.main()

"""
true_modes = [
"off",
"fixed",
"super-fixed",
"fading",
"spectrum-wave",
"backwards-spectrum-wave",
"marquee-<length>",
"backwards-marquee-<length>",
"covering-marquee",
"covering-backwards-marquee",
"alternating-<length>",
"moving-alternating-<length>",
"backwards-moving-alternating-<length>",
"pulse",
"breathing",
"super-breathing",
"candle",
"starry-night",
"rainbow-flow",
"backwards-rainbow-flow",
"super-rainbow",
"backwards-super-rainbow",
"rainbow-pulse",
"backwards-rainbow-pulse",
"wings"]

modes = [
"off",
"fixed",
"super-fixed",
"fading",
"spectrum-wave",
"marquee",
"covering-marquee",
"alternating",
"moving-alternating",
"pulse",
"breathing",
"super-breathing",
"candle",
"starry-night",
"rainbow-flow",
"super-rainbow",
"rainbow-pulse",
"wings"]
"""
"Static, Marquee/Fading/Pulse/Breathing, Spectrum wave/Rainbow flow/Super rainbow/Rainbow pulse, Alternating"
