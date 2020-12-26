#!/usr/bin/env python
from copy import deepcopy
from math import ceil

class Marquee():
    def __init__(self, led_len, marquee_len, background_colour, marquee_colours, number_of_marquees=1, spacing=0):
        self.colour_iter = []
        if number_of_marquees!=1 and spacing==0:
            spacing=marquee_len
            
        if len(marquee_colours)<marquee_len:
            print(f"{len(marquee_colours)}/{marquee_len} marquee colours supplied, repeating pattern")
            for colour in marquee_colours:
                marquee_colours.append(colour)
                if len(marquee_colours)==marquee_len:
                    break
        elif len(marquee_colours)>marquee_len:
            print("Too many marquee colours supplied, truncating")
            marquee_colours = marquee_colours[:marquee_len]

        marquee_colours_array = [*marquee_colours*number_of_marquees]
        for marquee in range(number_of_marquees-1):
            for _ in range(spacing):
                marquee_colours_array.insert((marquee_len*(marquee+1))+(spacing*marquee),background_colour)

        colours = [background_colour]*led_len
        for colour in marquee_colours_array[::-1]:
            del colours[-1]
            colours.insert(0,colour)
            self.colour_iter.append(deepcopy(colours))
        for _ in range(len(colours)):
            del colours[-1]
            colours.insert(0,background_colour)
            self.colour_iter.append(deepcopy(colours))
    def __iter__(self):
        return(iter(self.colour_iter))

class Ambient():
    def __init__(self, vertical_led_len, horizontal_led_len):
        from mss import mss
        import numpy as np
        self.np = np
        self.vertical_led_len = vertical_led_len
        self.horizontal_led_len = horizontal_led_len
        self.mss_obj = mss()
        self.main_monitor = self.mss_obj.monitors[1]
        self.width, self.height = list(self.main_monitor.values())[2:]

    def _get_rgb(self, np_array): #To make it easy to change below slice, if format ever changes
        return list(np_array)[2::-1]

    def __next__(self):
        screen_np = self.np.array(self.mss_obj.grab(monitor=self.main_monitor)) #BGRA format !
        top_np = screen_np[0, :]
        bottom_np = screen_np[self.height-1, :]
        left_np = screen_np[:, 0]
        right_np = screen_np[:, self.width-1]
        top, bottom, left, right = [], [], [], []

        vertical_led_gap = self.height // self.vertical_led_len
        horizontal_led_gap = self.width // self.horizontal_led_len

        for led_pos in range(0, self.height, vertical_led_gap):
            left.insert(0, self._get_rgb(left_np[led_pos]))
            right.insert(0, self._get_rgb(right_np[led_pos]))

        for led_pos in range(0, self.width, horizontal_led_gap):
            top.append(self._get_rgb(top_np[led_pos]))
            bottom.append(self._get_rgb(bottom_np[led_pos]))

        left.extend(top)
        bottom.extend(right)

        return (left, bottom)

    def run(self, device, channels=["led1", "led2"]):
        self.run = 1
        def set_colours(channel_colours):
            for channel, colours in zip(channels, channel_colours):
                sleep(0.01)
                device.set_color(channel, "super-fixed", colours)
        def run_():
            while self.run == 1:
                sleep(0.01)
                channel_colours = next(self)
                set_colours(channel_colours)
        print(f"Running ambient mode")
        self._thread_run = Thread(target = run_)
        self._thread_run.start()
        input("Enter to stop")
        self.run = 0
        self.mss_obj.close()

class Gradient():
    def __init__(self, led_len, cross_channels=0):
        self._cross_channels = cross_channels
        if self._cross_channels == 0:
            self._led_len = led_len
        else:
            self._led_len = led_len*2

    def generate(self, colours, mode="normal", step=1, smooth=1, even_distribution=True):
        if smooth == 1:
            colours.append(deepcopy(colours[0]))
        elif smooth == 2:
            colours.extend(deepcopy(colours[-2::-1]))

        self._gradient_colour_sets = []
        if mode == "wave":
            if step == 1:
                step = 10 #will mess with default wave step value later
            self._gradient_colour_sets.append([[0,0,0]] * self._led_len)

        if even_distribution == True:
            diffs = {}
            diff_largest = 0
            for index, colour in enumerate(colours[:-1]):
                diffs[str(colour)] = {}
                for pos, channels in enumerate(zip(colour, colours[index + 1])):
                    channel, channel_next = channels
                    diff = channel - channel_next
                    if diff < 0:
                        diff = diff * -1
                    if diff > diff_largest:
                        diff_largest = diff
                    diffs[str(colour)][pos] = diff

        current_colour = colours[0]
        step_compensated = step
        for next_colour in colours:
            diff_current = diffs[str(current_colour)]
            while next_colour != current_colour:
                for index, channels in enumerate(zip(current_colour, next_colour)):
                    channel, channel_new = channels
                    if even_distribution == True:
                        diff = diff_current[index]
                        step_compensated = ceil((diff / diff_largest) * step)
                    if channel < channel_new:
                        channel += step_compensated #favour
                        #if no multiple of step is equal to the difference of current and next colour, current will never become equal
                        if channel > channel_new: #stepped over new value
                            channel = channel_new
                    elif channel > channel_new:
                        channel -= step_compensated
                        if channel < channel_new:
                            channel = channel_new
                    current_colour.append(channel)
                del current_colour[:3]

                if mode == "normal":
                    self._gradient_colour_sets.append([deepcopy(current_colour)] * self._led_len)
                else: #wave is only other mode atm
#                    if reverse == True:
                    #self._gradient_colour_sets.append([*self._gradient_colour_sets[-1][:1], deepcopy(current_colour)])
                    self._gradient_colour_sets.append([deepcopy(current_colour), *self._gradient_colour_sets[-1][:-1]])


        if mode == "wave":
            #smoothing for continuous main loop
            last_colours = deepcopy(self._gradient_colour_sets[-1])
            first_colours = deepcopy(self._gradient_colour_sets[self._led_len]) #need to ensure gradient_colour_sets length >= led_len
            for ind, _ in enumerate(last_colours):
                #del last_colours[0]
                #last_colours.append(first_colours[index])
                del last_colours[-1]
                last_colours.insert(0, first_colours[-(ind+1)])
                self._gradient_colour_sets.append(deepcopy(last_colours))

            if self._cross_channels == 1: #split gradient across channels
                true_led_len = self._led_len // 2
                for ind, colour_set in enumerate(self._gradient_colour_sets):
                    self._gradient_colour_sets[ind] = [colour_set[:true_led_len], colour_set[true_led_len:]]

            self._gradient_colour_sets = [self._gradient_colour_sets[:self._led_len], self._gradient_colour_sets[self._led_len:]] #split into beginning and main loop

        print(f"Gradient {' > '.join(str(colour) for colour in colours)} generated with mode: {mode}.")

    def run(self, device, delay=.03, channels=["led1", "led2"]):
        self.run = 1
        def set_colours(colours):
            sleep(delay)
            if self._cross_channels == 0:
                for channel in channels:
                    device.set_color(channel, "super-fixed", colours)
            else:
                for channel, channel_colours in zip(channels, colours):
                    device.set_color(channel, "super-fixed", channel_colours[::1-(2*(channel=="led2"))])
        def run_():
            if len(self._gradient_colour_sets) == 2: #beginning
                for colours in self._gradient_colour_sets[0]:
                    set_colours(colours)
            while 1: #main loop
                for colours in self._gradient_colour_sets[-1]: #access last index, will be main regardless of presence of beginning
                    if self.run == 0:
                        exit()
                    set_colours(colours)

        print(f"Running gradient with {delay * 1000}ms delay")
        self._thread_run = Thread(target = run_)
        self._thread_run.start()
        input("Enter to stop")
        self.run = 0

if __name__=="__main__":
    from liquidctl import driver
    from time import sleep
    from threading import Thread
    devices=[]
    for device in driver.find_liquidctl_devices():
        device.connect()
        devices.append(device)
    def ambi():
        amb = Ambient(10,16)
        amb.run(devices[0])
#    all_colours = Marquee(26, 4, [0,0,125], [[255,0,0]], number_of_marquees=3, spacing=10)# .06
    def gradi():
        grad = Gradient(26, cross_channels=0)
        grad.generate([[255,0,50], [255,0,255], [50, 0, 255], [0, 200, 255]], mode="wave", step=int(input("Step: ")))
        grad.run(devices[0], delay = float(input("Delay: "))/1000)
    if bool(input("enter nothing for gradient, anything for ambient"))==0:
        gradi()
    else:
        ambi()
