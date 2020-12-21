#!/usr/bin/env python
from copy import deepcopy

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

	#bbox=(from_x,from_y,to_x,to_y) aka (x,y) to (x1,y1)
"""        top = ImageGrab.grab(bbox=(0,0,self.width,1))
        bottom = ImageGrab.grab(bbox=(0,self.height-1,self.width,self.height))
        left = ImageGrab.grab(bbox=(0,0,1,self.height))
        right = ImageGrab.grab(bbox=(self.width-1,0,self.width,self.height))
        top_np = np.array(top)
        left_np = np.array(left)
        bottom_np = np.array(bottom)
        right_np = np.array(right)

        left,right,top,bottom=[],[],[],[]
        sampling=10
        vertical_led_gap = self.height//self.vertical_led_len
        horizontal_led_gap = self.width//self.horizontal_led_len

        for led_pos in range(0,self.height,vertical_led_gap):
            l_r, l_g, l_b = 0,0,0
            r_r, r_g, r_b = 0,0,0
            for _ in range(led_pos,led_pos+vertical_led_gap,vertical_led_gap//sampling)[:-1]:
                l_pixel=list(left_np[led_pos,0])
                r_pixel=list(right_np[led_pos,0])
                l_r+=l_pixel[0]
                l_g+=l_pixel[1]
                l_b+=l_pixel[2]
                r_r+=r_pixel[0]
                r_g+=r_pixel[1]
                r_b+=r_pixel[2]
            left.insert(0, [l_r//sampling,l_g//sampling,l_b//sampling])
            right.insert(0, [r_r//sampling,r_g//sampling,r_b//sampling])

        for led_pos in range(0,self.width,horizontal_led_gap):
            t_r, t_g, t_b = 0,0,0
            b_r, b_g, b_b = 0,0,0
            for _ in range(led_pos,led_pos+horizontal_led_gap,horizontal_led_gap//sampling)[:-1]:
                t_pixel=list(top_np[0,led_pos])
                b_pixel=list(bottom_np[0,led_pos])
                t_r+=t_pixel[0]
                t_g+=t_pixel[1]
                t_b+=t_pixel[2]
                b_r+=b_pixel[0]
                b_g+=b_pixel[1]
                b_b+=b_pixel[2]
            top.append([t_r//sampling,t_g//sampling,t_b//sampling])
            bottom.append([b_r//sampling,b_g//sampling,b_b//sampling])
        left.extend(top)
        bottom.extend(right)
        return((left,bottom))
"""

class Gradient():
    def __init__(self, led_len):
        self._led_len = led_len

    def generate(self, colours, mode="normal", step=1, smooth=1):
        if smooth == 1:
            colours.append(deepcopy(colours[0]))
        elif smooth == 2:
            colours.extend(deepcopy(colours[-2::-1]))

        self._gradient_colours = []
        if mode == "wave":
            step = 10 #will mess with default wave step value later
            self._gradient_colours.append([[0,0,0]] * self._led_len)

        current_colour = colours[0]
        for next_colour in colours:
            while next_colour != current_colour:
                for channel, channel_new in zip(current_colour, next_colour):
                    if channel < channel_new:
                        channel += step
                        #if no multiple of step is equal to the difference of current and next colour, current will never become equal
                        if channel > channel_new: #stepped over new value
                            channel = channel_new
                    elif channel > channel_new:
                        channel -= step
                        if channel < channel_new:
                            channel = channel_new
                    current_colour.append(channel)
                del current_colour[:3]

                if mode == "normal":
                    self._gradient_colours.append([deepcopy(current_colour)] * self._led_len)
                else: #wave is only other mode atm
                    self._gradient_colours.append([*self._gradient_colours[-1][1:], deepcopy(current_colour)])

        if mode == "wave":
            self._gradient_colours = [self._gradient_colours[:self._led_len], self._gradient_colours[self._led_len:]] #split into beginning and main loop

            #smoothing for continuous main loop
            last_colours = deepcopy(self._gradient_colours[1][-1])
            for index, _ in enumerate(last_colours):
                del last_colours[0]
                last_colours.append(deepcopy(self._gradient_colours[1][0][index]))
                self._gradient_colours[1].append(deepcopy(last_colours))
            
        print(f"Gradient {' > '.join(str(colour) for colour in colours)} generated with mode: {mode}.")

    def run(self, device, delay=.03, channels=["led1", "led2"]):
        self.run = 1
        def set_colours(colours):
            for channel in channels:
                sleep(delay)
                device.set_color(channel, "super-fixed", colours)
        def run_():
            if len(self._gradient_colours) == 2: #beginning
                for colours in self._gradient_colours[0]:
                    set_colours(colours)
            while 1: #main loop
                for colours in self._gradient_colours[-1]:
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
    amb = Ambient(10,16)
    amb.run(devices[0])
#    all_colours = Marquee(26, 4, [0,0,125], [[255,0,0]], number_of_marquees=3, spacing=10)# .06 speed
"""    grad = Gradient(26)
    grad.generate([[255,0,0], [0,255,0], [0,0,255]], mode="wave")
    grad.run(devices[0], delay = float(input("Delay: "))/1000)"""
