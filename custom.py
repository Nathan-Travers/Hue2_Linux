#!/usr/bin/env python
from copy import deepcopy
from math import ceil
from json import loads
from signal import signal, SIGINT

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
    def __init__(self, vertical_led_len, horizontal_led_len, sampling=False, sampling_step=2, sampling_weighted=False):
        from mss import mss
        from mss.exception import ScreenShotError
        import numpy as np
        self.np = np
        self.vertical_led_len = vertical_led_len
        self.horizontal_led_len = horizontal_led_len
        self._sampling = sampling
        self._sampling_step = sampling_step
        self._sampling_weighted = sampling_weighted
        self.mss_obj = mss()
        self.main_monitor = self.mss_obj.monitors[1]
        self.width, self.height = list(self.main_monitor.values())[2:]
        self._mss_ScreenShotError = ScreenShotError

    def _get_rgb(self, np_array): #To make it easy to change below slice, if format ever changes
        return list(np_array)[2::-1]

    def __next__(self):
        screen_np = []
        while type(screen_np) == list:
                try:
                        screen_np = self.np.array(self.mss_obj.grab(monitor=self.main_monitor)) #BGRA format !
                except self._mss_ScreenShotError: #when display sleeps, like after locking screen, XGetImage() fails
                        screen_np = []
                        input("Failed screen shot\nSleeping, press enter to restart\n")
                        self.mss_obj.get_error_details() #Unless error details are get, mss will continue to raise error despite it being past
                        print("Successfully continued")
        top_np = screen_np[0, :]
        bottom_np = screen_np[self.height-1, :]
        left_np = screen_np[:, 0]
        right_np = screen_np[:, self.width-1]
        top, bottom, left, right = [], [], [], []

        vertical_led_gap = self.height // self.vertical_led_len
        horizontal_led_gap = self.width // self.horizontal_led_len

        for led_pos in range(0, self.height, vertical_led_gap):
            if self._sampling == True:
                if self._sampling_weighted == False:
                    sampled_l = self.np.array([0,0,0])
                    sampled_r = self.np.array([0,0,0])
                    for led_pos_sampling in range(led_pos, led_pos + vertical_led_gap, self._sampling_step):
                        sampled_l += self._get_rgb(left_np[led_pos_sampling])
                        sampled_r += self._get_rgb(right_np[led_pos_sampling])
                    sampled_l = (sampled_l/vertical_led_gap).astype(int).tolist()
                    sampled_r = (sampled_r/vertical_led_gap).astype(int).tolist()
                    left.insert(0, sampled_l)
                    right.insert(0, sampled_r)
                else:
                    sampled_l = {}
                    sampled_r = {}
                    for led_pos_sampling in range(led_pos, led_pos + vertical_led_gap, self._sampling_step):
                        for (sampled_dict, led_arr) in zip((sampled_l, sampled_r), (left_np, right_np)):
                            pixel = str(self._get_rgb(led_arr[led_pos_sampling]))
                            if pixel in sampled_dict:
                                sampled_dict[pixel] += 1
                            else:
                                sampled_dict[pixel] = 0
                    for sampled_dict in (sampled_l, sampled_r):
                        most_freq_pixel_count = -1
                        most_freq_pixel = ""
                        for pixel in list(sampled_dict.keys()):
                            if sampled_dict[pixel] > most_freq_pixel_count:
                                most_freq_pixel_count = sampled_dict[pixel]
                                most_freq_pixel = pixel
                        sampled_dict["mf"] = loads(most_freq_pixel)
                    left.insert(0, sampled_l["mf"])
                    right.insert(0, sampled_r["mf"])
            else:
                left.insert(0, self._get_rgb(left_np[led_pos]))
                right.insert(0, self._get_rgb(right_np[led_pos]))

        for led_pos in range(0, self.width, horizontal_led_gap):
            if self._sampling == True:
                if self._sampling_weighted == False:
                    sampled_t = self.np.array([0,0,0])
                    sampled_b = self.np.array([0,0,0])
                    for led_pos_sampling in range(led_pos, led_pos + horizontal_led_gap, self._sampling_step):
                        sampled_t += self._get_rgb(top_np[led_pos_sampling])
                        sampled_b += self._get_rgb(bottom_np[led_pos_sampling])
                    sampled_t = (sampled_t/horizontal_led_gap).astype(int).tolist()
                    sampled_b = (sampled_b/horizontal_led_gap).astype(int).tolist()
                    top.append(sampled_t)
                    bottom.append(sampled_b)
                else:
                    sampled_t = {}
                    sampled_b = {}
                    for led_pos_sampling in range(led_pos, led_pos + horizontal_led_gap, self._sampling_step):
                        for sampled_dict, led_arr in zip((sampled_t, sampled_b), (top_np, bottom_np)):
                            pixel = str(self._get_rgb(led_arr[led_pos_sampling]))
                            if pixel in sampled_dict:
                                sampled_dict[pixel] += 1
                            else:
                                sampled_dict[pixel] = 0
                    for sampled_dict in (sampled_t, sampled_b):
                        most_freq_pixel_count = -1
                        most_freq_pixel = ""
                        for pixel in list(sampled_dict.keys()):
                            if sampled_dict[pixel] > most_freq_pixel_count:
                                most_freq_pixel_count = sampled_dict[pixel]
                                most_freq_pixel = pixel
                        sampled_dict["mf"] = loads(most_freq_pixel)
                    top.append(sampled_t["mf"])
                    bottom.append(sampled_b["mf"])
            else:
                top.append(self._get_rgb(top_np[led_pos]))
                bottom.append(self._get_rgb(bottom_np[led_pos]))

        left.extend(top)
        bottom.extend(right)

        return (left, bottom)

    def _sigint_handler(self, sig, frame):
        print("\nSIGINT received, exiting...")
        self.run = 0
        self.mss_obj.close() #still not sure this actually does anything
        exit()

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
            print(channel_colours)
        print(f"Running ambient mode")
        self._thread_run = Thread(target = run_)
        self._thread_run.start()
        signal(SIGINT, self._sigint_handler)
        self._thread_run.join()

class Gradient():
    def __init__(self, led_len, cross_channels=0):
        self._cross_channels = cross_channels
        if self._cross_channels == 0:
            self._led_len = led_len
        else:
            self._led_len = led_len*2

    def generate(self, colours, mode="normal", step=1, smooth=1, even_distribution=True, channel_size=3):
        if smooth == 1:
            colours.append(deepcopy(colours[0]))
        elif smooth == 2:
            colours.extend(deepcopy(colours[-2::-1]))

        gradient_colour_sets = []
        if mode == "wave":
            if step == 1:
                step = 10 #will mess with default wave step value later
            gradient_colour_sets.append([[0] * channel_size] * self._led_len)

        if even_distribution == True:
            diffs = {}
            diff_largest = 0
            for index, colour in enumerate(colours[:-1]):
                colour_next = colours[index + 1]
                colour_combo_name = str(colour) + str(colour_next)
                diffs[colour_combo_name] = {}
                for pos, channels in enumerate(zip(colour, colour_next)):
                    channel, channel_next = channels
                    diff = abs(channel - channel_next)
                    if diff > diff_largest:
                        diff_largest = diff
                    diffs[colour_combo_name][pos] = diff

        current_colour = colours[0]
        step_compensated = step
        for next_colour in colours[1:]:
            colour_combo_name = str(current_colour) + str(next_colour)
            diff_current = diffs[colour_combo_name]
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
                del current_colour[:channel_size]

                if mode == "normal":
                    gradient_colour_sets.append([deepcopy(current_colour)] * self._led_len)
                else: #wave is only other mode atm
#                    if reverse == True:
                    #gradient_colour_sets.append([*gradient_colour_sets[-1][:1], deepcopy(current_colour)])
                    gradient_colour_sets.append([deepcopy(current_colour), *gradient_colour_sets[-1][:-1]])


        if mode == "wave":
            #smoothing for continuous main loop
            last_colours = deepcopy(gradient_colour_sets[-1])
            first_colours = deepcopy(gradient_colour_sets[self._led_len]) #need to ensure gradient_colour_sets length >= led_len
            for ind, _ in enumerate(last_colours):
                #del last_colours[0]
                #last_colours.append(first_colours[index])
                del last_colours[-1]
                last_colours.insert(0, first_colours[-(ind+1)])
                gradient_colour_sets.append(deepcopy(last_colours))

            """if self._cross_channels == 1: #split gradient across channels
                true_led_len = self._led_len // 2
                for ind, colour_set in enumerate(gradient_colour_sets):
                    gradient_colour_sets[ind] = [colour_set[:true_led_len], colour_set[true_led_len:]]"""

            gradient_colour_sets = [gradient_colour_sets[:self._led_len], gradient_colour_sets[self._led_len:]] #split into beginning and main loop
        else:
            gradient_colour_sets = [gradient_colour_sets]

        self._gradient_colour_sets = gradient_colour_sets
        print(f"Gradient {' > '.join(str(colour) for colour in colours)} generated with mode: {mode}.")
        return (0, self._gradient_colour_sets)

    def run(self, device, delay=.03, channels=["led1", "led2"]):
        self.run = 1
        def set_colours(colours):
            sleep(delay)
            if self._cross_channels == 0:
                for channel in channels:
                    device.set_color(channel, "super-fixed", colours)
            else:
                device.set_color("led1", "super-fixed", colours[:self._led_len//2])
                device.set_color("led2", "super-fixed", colours[:self._led_len//2:-1])
                #for channel, channel_colours in zip(channels, colours):
                #    device.set_color(channel, "super-fixed", channel_colours[::1-(2*(channel=="led2"))])
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

class Gradient_CMYK(Gradient):
    def generate(self, colours, mode="normal", step=1, smooth=1, even_distribution=True):
        for colour in colours:
            for channel in colour:
                if channel > 100:    #These are taken as a percentage rather than /255 like RGB
                    print(f"No colour may have a channel with a value above 100.\nOffending colour: {colour}, ({channel})")
                    return (1,)

        super().generate(colours, mode=mode, step=step, smooth=smooth, even_distribution=even_distribution, channel_size=4)    #generate gradient using parent Gradient class in CMYK colour space
        gradient_colour_sets_rgb = []
        for set_cmyk in self._gradient_colour_sets:        #a set (of type array just a var name) contains each step in an animation
            set_rgb = []
            for step_cmyk in set_cmyk:                     #these steps are arrays of colours to be shown on leds
                step_rgb = []
                for colour_cmyk in step_cmyk:              #these colours are arrays of size 4 containing the channels for this colour space (C, M, Y, K)
                   colour_rgb = []                         #in each of these arrays I create a corresponding one for rgb values
                   channel_k = colour_cmyk[-1]
                   for channel_cmy in colour_cmyk[:-1]:
                       channel_rgb = ceil(255 * (1 - (channel_cmy / 100)) * (1 - (channel_k / 100)))    #CMYK to RGB calculation found on web
                       colour_rgb.append(channel_rgb)
                   step_rgb.append(colour_rgb)
                set_rgb.append(step_rgb)
            gradient_colour_sets_rgb.append(set_rgb)
        self._gradient_colour_sets = gradient_colour_sets_rgb    #replace original CMYK sets with RGB
        return (0, self._gradient_colour_sets)

if __name__=="__main__":
    from liquidctl import driver
    from time import sleep
    from threading import Thread
    devices=[]
    for device in driver.find_liquidctl_devices():
        device.connect()
        devices.append(device)
    def ambi():
        amb = Ambient(10,16, sampling=True, sampling_weighted=True)
        amb.run(devices[0])
#    all_colours = Marquee(26, 4, [0,0,125], [[255,0,0]], number_of_marquees=3, spacing=10)# .06
    def gradi():
        grad = Gradient_CMYK(26, cross_channels=1)
#        grad.generate([[255,0,50], [255,0,255], [50, 0, 255], [0, 200, 255]], mode="wave", step=int(input("Step: ")))
        result = grad.generate([[0,0,100,50], [100,0,100,50], [0,100,100,50]], mode="wave", step=int(input("Step: ")))
        return_code = result[0]
        if return_code == 0:
            grad.run(devices[0], delay = float(input("Delay: "))/1000)
        else:
            print("Failed")
            exit(return_code)
    if bool(input("enter anything for gradient, nothing for ambient"))==1:
        gradi()
    else:
        ambi()
