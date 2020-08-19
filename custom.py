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

class Gradient():
    def __init__(self, led_len, gradient, colours, smooth=1):
        if smooth==1:
            colours.append(colours[0])
        self.colours=[]
        colours_buffer = [colours[0]]*led_len
        r,g,b = colours[0]
        ind = 1
        counter = 0
        while 1:
            fin=1
            counter+=1
            n_colour = colours[ind]
            if r!=n_colour[0]:
                fin=0
                if r<n_colour[0]:
                    r+=1
                else:
                    r-=1
            if g!=n_colour[1]:
                fin=0
                if g<n_colour[1]:
                    g+=1
                else:
                    g-=1
            if b!=n_colour[2]:
                fin=0
                if b<n_colour[2]:
                    b+=1
                else:
                    b-=1

            if counter==gradient:
                colours_buffer.insert(0, [r,g,b])
                del colours_buffer[-1]
                counter=0
                if colours[0]!=colours_buffer[-1]:
                    self.colours.append(deepcopy(colours_buffer))
            if fin==1:
                ind+=1
                if ind==len(colours):
                    for colour in self.colours[0][::-1]:
                        colours_buffer.insert(0, colour)
                        del colours_buffer[-1]
                        self.colours.append(deepcopy(colours_buffer))
                    break
    def __iter__(self):
        return(iter(self.colours))

class Ambient():
    def __init__(self, vertical_led_len, horizontal_led_len):
        from PIL import ImageGrab
        self.vertical_led_len = vertical_led_len
        self.horizontal_led_len = horizontal_led_len
        self.width, self.height=ImageGrab.grab().size

    def __next__(self):
        from PIL import ImageGrab
        import numpy as np

        top = ImageGrab.grab(bbox=(0,0,self.width,1))
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

if __name__=="__main__":
    from liquidctl import driver
    from time import sleep
    devices=[]
    for device in driver.find_liquidctl_devices():
        device.connect()
        devices.append(device)
    a= Ambient(10,16)
    while a:
        sleep(0.01)
        c,c1=next(a)
        devices[0].set_color("led1","super-fixed",c)
        devices[0].set_color("led2","super-fixed",c1)
#    all_colours = Marquee(26, 4, [0,0,125], [[255,0,0]], number_of_marquees=3, spacing=10)# .06 speed
#    all_colours = Gradient(26, 12, [[255,0,0], [0,0,255]])# .01 speed
"""    while 1:
        for colours in all_colours:
            sleep(.03)
            devices[0].set_color("led1", "super-fixed", colours)
            sleep(.03)
            devices[0].set_color("led2", "super-fixed", colours)
"""
