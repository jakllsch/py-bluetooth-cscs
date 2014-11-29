#!/usr/bin/env python

# works with a Scosche BLESCAD

# some ideas borrowed from https://github.com/msaunby/ble-sensor-pi/blob/5024d6c8d2aafb2b5d12ecd5d0f74b1b5c57ceb2/sensortag/sensortag.py

import sys
import pexpect
import struct
import binascii
import curses

old_spd_count = 0
old_spd_time = 0
circ = 2122.0 # 2130.0
old_cad_count = 0
old_cad_time = 0

first_rev = -1

total_time = 0.0;
total_work = 0.0;

rootwin = None

class CSCS:
    def __init__( self, bluetooth_adr ):
        #print 'gatttool -t random -b ' + bluetooth_adr + ' --char-write-req -a 0x19 -n 0100 --listen'
        self.con = pexpect.spawn('gatttool -t random -b ' + bluetooth_adr + ' --char-write-req -a 0x19 -n 0100 --listen')
        self.con.expect('Characteristic value was written successfully')
        self.cb = {}
        return

    def notification_loop( self ):
        while True:
            try:
                pnum = self.con.expect('Notification handle = .*? \r', timeout=4)
            except pexpect.TIMEOUT:
                print "TIMEOUT exception!"
                break
            if pnum==0:
                after = self.con.after
                hxstr = after.split()[3:]
                handle = int(hxstr[0], 16)
                if True:
                    self.cb[handle](binascii.a2b_hex(''.join(hxstr[2:])))
                pass
            else:
                print "TIMEOUT!!"
        pass
        return

    def register_cb( self, handle, fn ):
        self.cb[handle]=fn
        return

def kph(new_count, new_time):
    global rootwin
    global old_spd_count
    global old_spd_time
    global circ
    global first_rev
    global total_time
    global total_work
    if new_count == old_spd_count:
        return
    if new_time == old_spd_time:
        return
    delta_v = new_count - old_spd_count
    delta_t = new_time - old_spd_time
    if delta_v < 0:
        delta_v += 0x10000000
    if delta_t < 0:
        delta_t += 0x10000
    #print "spd delta", delta_v, delta_t
    #print "KPH", (delta_v * circ * 1024.0 / delta_t) * .0036
    kph = (delta_v * circ * 1024.0 / delta_t) * .0036
    power = 5.244820 * (kph / 1.609344) + 0.019168 * (kph / 1.609344)**3 # https://kurtkinetic.com/technical-information/kinetic-power-tech/
    if first_rev == -1:
        first_rev = new_count
    else:
        total_time += delta_t/1024.0
        total_work += power * delta_t/1024.0
    #print "dist", (new_count - first_rev) * circ / 1000000.0
    dist = (new_count - first_rev) * circ / 1000000.0
    rootwin.addstr(1, 0, 'speed:      {:8.2f} km/h {:8.2f} mi/h      '.format(kph, kph / 1.609344))
    rootwin.addstr(2, 0, 'power:      {:8.2f} W    {:8.2f} kJ        '.format(power, total_work/1000.0))
    rootwin.addstr(3, 0, 'distance:   {:9.3f} km  {:9.3f} mi         '.format(dist, dist / 1.609344))
    rootwin.addstr(4, 0, 'time:       {:8.2f} s           '.format(total_time))
    old_spd_count = new_count
    old_spd_time = new_time

def rpm(new_count, new_time):
    global rootwin
    global old_cad_count
    global old_cad_time
    if new_count == old_cad_count:
        return
    if new_time == old_cad_time:
        return
    delta_v = new_count - old_cad_count
    delta_t = new_time - old_cad_time
    if delta_v < 0:
        delta_v += 0x10000
    if delta_t < 0:
        delta_t += 0x10000
    #print "cad delta", delta_v, delta_t
    #print "RPM", (delta_v * 1024.0 / delta_t) * 60
    rpm = (delta_v * 1024.0 / delta_t) * 60.0
    rootwin.addstr(0, 0, 'cadence:    {:8.2f} RPM         '.format(rpm))
    old_cad_count = new_count
    old_cad_time = new_time

def callback(rawdata):
    global rootwin
    flags, wheel_rev, wheel_time, crank_rev, crank_time = struct.unpack('<BIHHH', rawdata)
    #print flags, wheel_rev, wheel_time, crank_rev,crank_time
    kph(wheel_rev,wheel_time)
    rpm(crank_rev,crank_time)
    rootwin.refresh()

def main(stdscr):
    global rootwin
    rootwin = stdscr
    rootwin.clear()
    rootwin.refresh()
    bluetooth_adr = sys.argv[1]
    cscs = CSCS(bluetooth_adr)
    cscs.register_cb(0x18, callback)
    cscs.notification_loop()

if __name__ == "__main__":
    curses.wrapper(main)

