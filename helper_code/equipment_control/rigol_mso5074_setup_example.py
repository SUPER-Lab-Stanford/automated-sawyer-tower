# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 10:24:54 2024

@author: hornb
"""

import pyvisa
import time
import serial
import matplotlib.pyplot as plt
from Equipment_Control_Malachi import MSO5000

scopeUSB = 'USB0::0x1AB1::0x0515::MS5A243807653::INSTR'
scope = MSO5000(visa_name = scopeUSB) # initializes object of MSO5000 class

ch1 = scope.readChannel(channel_index = 2)
# returns np.ndarray with current time and data vectors for channel 1

# Plot Channel 1
fig1, ax1 = plt.subplots()
ax1.plot(ch1[:,0], ch1[:,1], linewidth=2)
ax1.set(title = 'Channel 1 Current Data',
        ylabel = 'Channel 1 Voltage [V]',
        xlabel = 'Time [s]')
ax1.grid()




all_data = scope.readAllChannels()
# returns np.ndarray with time and data vectors for all channels

# Plot all channels
fig2, ax2 = plt.subplots()
ax2.plot(all_data[:,0], all_data[:,1], linewidth=2, label = 'Ch1')
ax2.plot(all_data[:,0], all_data[:,2], linewidth=2, label = 'Ch2')
ax2.plot(all_data[:,0], all_data[:,3], linewidth=2, label = 'Ch3')
ax2.plot(all_data[:,0], all_data[:,4], linewidth=2, label = 'Ch4')
ax2.set(title = 'All Channels Current Data',
        ylabel = 'Voltage [V]',
        xlabel = 'Time [s]')
ax2.grid()
ax2.legend()



