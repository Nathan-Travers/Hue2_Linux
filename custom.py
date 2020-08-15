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
 #       bottom = ImageGrab.grab(bbox=(height-1,0,width,1))
#        right = ImageGrab.grab(bbox=(width-1,0,1,height))
#        bottom_np = np.array(bottom)
#        right_np = np.array(right)
#        for y in range(0,width,int(width/horizontal_led_len)):
 #           print(bottom_np[0,y])
  #      for x in range(0,height,int(height/vertical_led_len)):
   #         print(right_np[x])
    def __next__(self):
        from PIL import ImageGrab
        import numpy as np
        top = ImageGrab.grab(bbox=(0,0,self.width,1))
        left = ImageGrab.grab(bbox=(0,0,1,self.height))
        top_np = np.array(top)
        left_np = np.array(left)
        colours=[]
        led_gap = self.height//self.vertical_led_len
        for led_pos in range(0,self.height,led_gap):
            r,g,b=0,0,0
            for _ in range(led_pos,led_pos+led_gap,led_gap//10)[:-1]:
                pixel=list(left_np[led_pos,0])
                r+=pixel[0]
                g+=pixel[1]
                b+=pixel[2]
            colours.insert(0, [r//10,g//10,b//10])
        for y in range(0,self.width,int(self.width/self.horizontal_led_len)):
            colours.append(list(top_np[0,y]))
        return(colours)

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
        devices[0].set_color("led1","super-fixed",next(a))
#    all_colours = Marquee(26, 4, [0,0,0], [[255,0,0]], number_of_marquees=3, spacing=10)# .06 speed
#    all_colours = Gradient(26, 12, [[255,0,0], [0,0,255], [0,255,0]])# .01 speed
#    while 1:
#        for colours in all_colours:
#            sleep(.01)
#            devices[0].set_color("led1", "super-fixed", colours)
