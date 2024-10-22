# -*- coding: utf-8 -*-

import csv
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

sys.path.insert(0, '/Users/katherineliang/Desktop/Power America/Python_Script')
from malachi_plotting_functions_coss import *

data_folder = 'Data/'  # folder that the data is in
datafile = 'refcap_50v_0426'  # raw file to pull data from
extension = '.csv'
scope = 'rigol'  # could be 'agilent_4G' or 'rigol'

cross_value = 0  # vout_plus trigger t=0 point: 0 for trap, smallish val for sine
freq = 5e6  # switching freq in Hz

# cdiv ratios and channel indices (-1 to remember dumb python zero-indexing)
# vout_plus_cap_ratio = 8.51
vout_plus_cap_ratio = 1
vout_plus_channel = 1 - 1
# vout_minus_cap_ratio = 9.31
vout_minus_cap_ratio = 1
vout_minus_channel = 2 - 1
vref_cap_ratio = 8.18222685
vref_channel = 4 - 1
vgate_channel = 3 - 1  # note this can be anything for agilent scope: just ignore it
t_channel = 5 - 1

vref_scaling = 1.6  # make it match amplitude of vout channels
plotting_period_fraction = 0.15  # fraction of period to plot edges over for alignment assistance

"""
Skew Optimization

Algorithm:
1. Keep Vout_plus constant, calculate the mean squared error between Vout_minus and Vout_plus, and the mean squared error between Vref and Vout_plus as we iterate over a range of skew values
2. Use min() to find minimum MSE value for each of Vout_minus and Vref
3. Use argmin() to find the two skew values that correspond to minimum MSE values
"""

eval = []
MSE_Vout_minus = []
MSE_Vref = []

for i in range(-5000, 0, 1):  # iterate over a range of skew values
    vout_minus_shift = i * 1e-12
    vref_shift = i * 1e-12

    """
    Data Import and Processing:
    """
    datafile_raw = data_folder + datafile + extension
    if scope == 'rigol':  # if we have to deal with the rigol data import
        datafile_cleaned = data_folder + datafile + '_cleaned' + extension
        # clean data if necessary, otherwise this function just internally skips itself
        rigol_scope_csv_convert_t0_tInc_to_normal_csv(datafile_raw, datafile_cleaned)
        data = scope_csv_import(datafile_cleaned, 1)
    elif scope == 'agilent_4G':
        data = scope_csv_import(datafile_raw, 0)  # agilent has no title row

    # shift vout_minus and vref by desired skew using interpolation
    data = data_array_time_shift_one_signal(data, t_channel, vout_minus_channel, vout_minus_shift)
    data = data_array_time_shift_one_signal(data, t_channel, vref_channel, vref_shift)
    data = data_array_set_t0_at_value_crossing(data, t_channel, vout_plus_channel,
                                               cross_value, True, 3)
    # sets t=0 at rising zero-crossing of vout_plus_ac
    t = data[:, t_channel]

    # get plotting start and stop indices
    tstart1 = -plotting_period_fraction / 2 * 1 / freq
    tstop1 = plotting_period_fraction / 2 * 1 / freq
    tstart2 = tstart1 + 1 / 2 / freq
    tstop2 = tstop1 + 1 / 2 / freq

    istart1 = np.argmax(t >= tstart1)
    istop1 = np.argmax(t >= tstop1) + 1
    istart2 = np.argmax(t >= tstart2)
    istop2 = np.argmax(t >= tstop2) + 1

    # get signals to rougly overlay, can still be AC no problem
    vout_plus = data[:, vout_plus_channel] * vout_plus_cap_ratio
    vout_minus = data[:, vout_minus_channel] * -1 * vout_minus_cap_ratio  # invert to match vout_plus
    vref = data[:, vref_channel] * -1 * vref_scaling * vref_cap_ratio  # invert to match vout_plus

    # beginning of MSE optimization
    a1 = 0
    b1 = 0
    a2 = 0
    b2 = 0
    i = istart1  # rising waveform
    while i <= (istop1):
        a1 += pow((vout_minus[i] - vout_plus[i]),
                  2)  # finding accummulated squared error between each datapoint of Vout_plus (ch.1) and Vout_minus (ch.2)
        b1 += pow((vref[i] - vout_plus[i]),
                  2)  # finding accummulated squared error between each datapoint of Vout_plus (ch.1) and Vref (ch.4)
        i += 1
    i = istart2  # falling waveform
    while i <= (istop2):
        a2 += pow((vout_minus[i] - vout_plus[i]), 2)
        b2 += pow((vref[i] - vout_plus[i]), 2)
        i += 1
    eval.append([vout_minus_shift])
    a1 = a1 / (istop1 - istart1)  # finding mean square error between Vout_plus and Vout_minus for rising waveform
    b1 = b1 / (istop1 - istart1)  # finding mean square error between Vout_plus and Vref for rising waveform
    a2 = a2 / (istop2 - istart2)  # finding mean square error between Vout_plus and Vout_minus for falling waveform
    b2 = b2 / (istop2 - istart2)  # finding mean square error between Vout_plus and Vref for falling waveform
    MSE_Vout_minus.append(a1 + a2)  # sum up total error from both rising and falling waveform
    MSE_Vref.append(b1 + b2)  # sum up total error from both rising and falling waveform
Vout_minus_skew_for_min_MSE = np.argmin(
    MSE_Vout_minus)  # index corresponding to minimum MSE between Vout_plus and Vout_minus
Vout_ref_skew_for_min_MSE = np.argmin(MSE_Vref)  # index corresponding to minimum MSE between Vout_plus and Vref

print("vout_minus_shift=", eval[Vout_minus_skew_for_min_MSE])
print("vout_minus_shift MSE optimized val=", min(MSE_Vout_minus))
print("vref_shift=", eval[Vout_ref_skew_for_min_MSE])
print("vref_shift MSE optimized val=", min(MSE_Vref))

"""

        # plotting:
        fig1, ax1 = plt.subplots(2)
        ax1[0].plot(t[istart1:istop1]*1e9, vout_plus[istart1:istop1], '-', linewidth=2,
                    color = su_color_list_contrast4[0],
                    label='$V_{out+}$')
        ax1[0].plot(t[istart1:istop1]*1e9, vout_minus[istart1:istop1], '-', linewidth=2,
                    color = su_color_list_contrast4[1],
                    label='$V_{out-}$')
        ax1[0].plot(t[istart1:istop1]*1e9, vref[istart1:istop1], '-', linewidth=2,
                    color = su_color_list_contrast4[2],
                    label='$V_{ref}$')
        ax1[0].set(title = 'Skew calibration: ' + datafile)
        ax1[0].legend(loc='upper left')
        ax1[0].grid()

        ax1[1].plot(t[istart2:istop2]*1e9, vout_plus[istart2:istop2], '-', linewidth=2,
                    color = su_color_list_contrast4[0],
                    label='$V_{out+}$')
        ax1[1].plot(t[istart2:istop2]*1e9, vout_minus[istart2:istop2], '-', linewidth=2,
                    color = su_color_list_contrast4[1],
                    label='$V_{out-}$')
        ax1[1].plot(t[istart2:istop2]*1e9, vref[istart2:istop2], '-', linewidth=2,
                    color = su_color_list_contrast4[2],
                    label='$V_{ref}$')
        ax1[1].set(xlabel='time [ns]')
        ax1[1].legend(loc='upper right')
        ax1[1].grid()

        #plt.savefig('figs/skew', dpi = 150)
        #plt.show()
        """