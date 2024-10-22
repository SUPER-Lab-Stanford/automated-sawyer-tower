# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 11:29:07 2024

@author: hornb
"""

"""
This is intended to be a more in-depth analysis than what's done automatically
in user_run_file.py. This idea is that you may run this file multiple times on
a single dataset to see how different variables affect the result, ultimately
fine-tuning the parameters for the Ediss measurement to be as accurate as
possible on a case-by-case basis

This is a little more involved on the user side than og_loss_analysis_code
files, but a bit easier to use in my opinion because you just tune things to
make the calculation work instead of relying on niche variables that may break
the code and it's hard to remember what they do.
"""

import matplotlib.pyplot as plt
import numpy as np
import sys
from scipy.ndimage import gaussian_filter1d
from scipy import integrate

from helper_code.helper_functions import *
from helper_code.su_colors import *

"""
START USER-EDITED VARIABLES:
"""

# file organization variables
run_doc_root_dir = 'run_documentation_files/'
run_doc_dir = '0729_gs66504b_sine_5mhz/' # the name of your run folder
dut_dir = 'manual_runs/' # shouldn't need to change
operating_point = '225v' # the point of interest in sweep. no txt or csv extension

# optional gaussian smoothing variables NOW LOW PASS FILTER TO TEST IT
show_smoothing_plot = False # whether to show plot to help determine smoothing stdev's
smoothing = True # whether to do any smoothing at all
cutoff = 25 * 1e6
order = 3

# zeroing window fine-tuning
show_zeroing_window_plot = False # whether to show plot for tuning zeroing window
use_custom_zeroing_windows = True # whether to use custom zeroing windows
if use_custom_zeroing_windows:
    # vout_plus
    z_window_vout_plus_left = 0.2 # fraction of quarter period vout_plus zeroing window should extend to the left
    z_window_vout_plus_right = 0.2 # fraction of quarter period vout_plus zeroing window should extend to the right
    # vout_minus
    z_window_vout_minus_left = 0.2 # vout_minus to the left
    z_window_vout_minus_right = 0.2 # vout_minus to the right
    # vref
    z_window_vref_left = 0.0 # vref to the left
    z_window_vref_right = 0.1 # vref to the right
else:
    [z_window_vout_plus_left, z_window_vout_plus_right, z_window_vout_minus_left, z_window_vout_minus_right, z_window_vref_left, z_window_vref_right] = \
        [0.2, 0.2, 0.2, 0.2, 0.05, 0.05]

# integration window fine-tuning
show_integration_window_plot = False # whether to show plot for tuning window
use_custom_integration_windows = True # whether to use custom integration window
if use_custom_integration_windows:
    int_window_point_shift_1 = 4 # number of points to the right to shift start of "up integration window"
    int_window_point_shift_2 = 4 # number of points to the right to shift end of "up integration window"
else:
    [int_window_point_shift_1, int_window_point_shift_2] = [-1, 1]

# optional manual deskewing
show_deskewing_plot = True # whether to show plot for manual deskewing
use_custom_deskewing = True
vout_plus_custom_deskew = 0.5 * 1e-9 # [seconds] to right
vout_minus_custom_deskew = 1.2 * 1e-9 # [seconds] to right

# plots to enable or disable
plot_input_traces = True # shows plot of scope data after cdiv scaling has happened
plot_sine_dvdt = False # shows plot of DUT voltage with calculated dv/dt over integration window
if plot_sine_dvdt:
    dvdt_buffer = 0.1 # fraction of quarter period to use for dvdt calculation
    rise_adjust = 20 # individual points to right to adjust rise center
    fall_adjust = -25 # individual points to right to adjust fall center
plot_Eoss_cum = False # shows plot of cumulative Eoss over time (end - start = Ediss)
plot_QV = True # shows plot of Q vs V along with Ediss calculated by integration

"""
END USER-EDITED VARIABLES:
"""

"""
Load in data and parameters
"""

# determine run parameters, load in scope data
summary_file = run_doc_root_dir + run_doc_dir + dut_dir + operating_point + '.txt'
summary_file_vars = read_colon_file(summary_file)
# [l1_pos, l2_pos, duty_vref, ch1_deskew, ch2_deskew, Ediss_og, freq, trap_dvdt, cref]
Ediss_og = float(summary_file_vars[5]) # [Joules]
freq = float(summary_file_vars[6])*1e6 # [Hz when multiplied by 1e6]
trap_dvdt = float(summary_file_vars[7]) # fraction of a quarter wavelength
cref = float(summary_file_vars[8])*1e-12 # [F when multiplied by 1e-12]

data_file = run_doc_root_dir + run_doc_dir + dut_dir + operating_point + '.csv'
scope_data = np.loadtxt(data_file, delimiter=',', skiprows=0)
scope_data_og = scope_data.copy() # to save an original copy for later plotting
t_res = scope_data[1,0] - scope_data[0,0]
period = 1/freq
period_points_float = period / t_res # not rounded for better math

"""
Determine t=0 point using a smoothed version of vout+
"""

scope_smooth = scope_data.copy() # to leave scope data alone
scope_smooth[:,1] = gaussian_average_specifying_stdev_time(
    sig = scope_smooth[:,1], t_res = t_res,
    t_stdev = 1e-9) # smooth channel 1 for t0 search: using 1 ns stdev
scope_smooth = data_array_set_t0_at_value_crossing(
    scope_smooth, 0, 1, 0, True, 6) # find middle of first rising slope
scope_data[:,0] = scope_smooth[:,0] # set t0 in the actual data
t = scope_data[:,0]
t0_index = np.argmax(t >= 0) # index of t=0 point in dataset

"""
Perform optional smoothing: should add a plot option here to see comparison to rough
"""

if smoothing:
    t_res = scope_data[3,0] - scope_data[2,0]
    scope_rough = scope_data.copy() # for later plotting
    scope_data[:,1] = vector_butterworth_lpf(scope_data[:,1], t_res, order, cutoff) # smooth channel 1 = vout+
    scope_data[:,2] = vector_butterworth_lpf(scope_data[:,2], t_res, order, cutoff) # smooth channel 2 = vout-
    scope_data[:,4] = vector_butterworth_lpf(scope_data[:,4], t_res, order, cutoff) # smooth channel 4 = vref
    scope_smoothed = scope_data.copy() # for later plotting
    
"""
Perform optional deskewing of vout+ and vout- using user-defined variables
"""

if use_custom_deskewing:
    scope_data = data_array_time_shift_one_signal(scope_data, 0, 1, vout_plus_custom_deskew)
    scope_data = data_array_time_shift_one_signal(scope_data, 0, 2, vout_minus_custom_deskew)

"""
Perform zeroing of signals using the user-defined zeroing window
"""

# determine zeroing start and stop times
vout_plus_zeroing_start = period * (1 - 5/16 - (1/4)*z_window_vout_plus_left)
vout_plus_zeroing_stop = period * (1 - 5/16 + (1/4)*z_window_vout_plus_right)
vout_minus_zeroing_start = period * (1/2 - 5/16 - (1/4)*z_window_vout_minus_left)
vout_minus_zeroing_stop = period * (1/2 - 5/16 + (1/4)*z_window_vout_minus_right)
vref_zeroing_start = period * (3/4 - 1/16 - (1/4)*z_window_vref_left)
vref_zeroing_stop = period * (3/4 - 1/16 + (1/4)*z_window_vref_right)

# zero vout+, vout-, and vref
vout_plus = vector_zero_ac_sig_to_trange_avg(
    t = t, sig = scope_data[:,1],
    tstart = vout_plus_zeroing_start, # adjust to encompass minimum of waveform
    tend = vout_plus_zeroing_stop) # adjust to encompass minimum of waveform
vout_minus = vector_zero_ac_sig_to_trange_avg(
    t = scope_data[:,0], sig = scope_data[:,2],
    tstart = vout_minus_zeroing_start,
    tend = vout_minus_zeroing_stop)
vref = vector_zero_ac_sig_to_trange_avg(
    t = scope_data[:,0], sig = scope_data[:,4],
    tstart = vref_zeroing_start,
    tend = vref_zeroing_stop)

"""
Determine the integration window using the user-defined integration variables
"""

# determine integration indices
istart1 = t0_index + round(period_points_float*(1/2 + 3/16)) + int_window_point_shift_1
istop1 = istart1 - int_window_point_shift_1 + round(period_points_float) + int_window_point_shift_2

"""
Calculate relevant parameters and use integration window to find Ediss
"""

vst = vout_plus - vout_minus
vdut = vout_plus - vref
vcref = vref - vout_minus
qoss = vcref*cref
qoss = qoss - min(qoss) # zero so it's referenced to DUT not Cref

# perform integration
vdut_int = vdut[istart1:istop1]
qoss_int = qoss[istart1:istop1]
t_int = t[istart1:istop1]

Ediss = np.trapz(y=vdut_int, x=qoss_int)
Ediss_cum = integrate.cumtrapz(y=vdut_int, x=qoss_int)

"""
Make some plots (or not depending on user inputs)
"""

# plot smoothed signals with original signals as background
if show_smoothing_plot:
    fig_smooth, ax_smooth = plt.subplots()
    istart = t0_index
    istop = t0_index + round(period_points_float)
    ax_smooth.set(title = 'Smoothed data overlaid onto raw data')
    
    ax_smooth.plot(t[istart:istop], scope_rough[:,1][istart:istop], linewidth=4,
            color = su_color_dict.get('cardinal_red_light') + '77',
            label = 'vout+')
    ax_smooth.plot(t[istart:istop], scope_smoothed[:,1][istart:istop], linewidth=1,
            color = su_color_dict.get('black_100'))
    
    ax_smooth.plot(t[istart:istop], scope_rough[:,2][istart:istop], linewidth=4,
            color = su_color_dict.get('palo_alto_light') + '77',
            label = 'vout-')
    ax_smooth.plot(t[istart:istop], scope_smoothed[:,2][istart:istop], linewidth=1,
            color = su_color_dict.get('black_100'))
    
    ax_smooth.plot(t[istart:istop], scope_rough[:,4][istart:istop], linewidth=4,
            color = su_color_dict.get('plum_light') + '77',
            label = 'vref')
    ax_smooth.plot(t[istart:istop], scope_smoothed[:,4][istart:istop], linewidth=1,
            color = su_color_dict.get('black_100'))
    ax_smooth.legend(loc = 'lower right')
    
    fig_smooth1, ax_smooth1 = plt.subplots(2)
    ax_smooth1[0].set(title = 'Raw data (top) vs Smoothed (bottom)')
    
    ax_smooth1[0].plot(t[istart:istop], scope_rough[:,1][istart:istop], linewidth=1,
            color = su_color_dict.get('cardinal_red'))
    ax_smooth1[1].plot(t[istart:istop], scope_smoothed[:,1][istart:istop], linewidth=1,
            color = su_color_dict.get('cardinal_red'))
    
    ax_smooth1[0].plot(t[istart:istop], scope_rough[:,2][istart:istop], linewidth=1,
            color = su_color_dict.get('palo_alto'))
    ax_smooth1[1].plot(t[istart:istop], scope_smoothed[:,2][istart:istop], linewidth=1,
            color = su_color_dict.get('palo_alto'))
    
    ax_smooth1[0].plot(t[istart:istop], scope_rough[:,4][istart:istop], linewidth=1,
            color = su_color_dict.get('plum'))
    ax_smooth1[1].plot(t[istart:istop], scope_smoothed[:,4][istart:istop], linewidth=1,
            color = su_color_dict.get('plum'))

# plot zeroing window
if show_zeroing_window_plot:
    fig_zeroing, ax_zeroing = plt.subplots()
    istart = t0_index
    istop = istart + round(period_points_float)
    
    ax_zeroing.plot(t[istart:istop]*1e9, vout_plus[istart:istop], linewidth=2,
                    color = su_color_list_contrast4[0],
                    label = 'Vout+')
    ax_zeroing.plot(np.array([1,1])*vout_plus_zeroing_start*1e9,
                    np.array([-np.average(vout_plus)/2, np.average(vout_plus)/2]),
                    '--', color = su_color_list_contrast4[0])
    ax_zeroing.plot(np.array([1,1])*vout_plus_zeroing_stop*1e9,
                    np.array([-np.average(vout_plus)/2, np.average(vout_plus)/2]),
                    '--', color = su_color_list_contrast4[0])
    
    ax_zeroing.plot(t[istart:istop]*1e9, vout_minus[istart:istop], linewidth=2,
                    color = su_color_list_contrast4[1],
                    label = 'Vout-')
    ax_zeroing.plot(np.array([1,1])*vout_minus_zeroing_start*1e9,
                    np.array([-np.average(vout_minus)/2, np.average(vout_minus)/2]),
                    '--', color = su_color_list_contrast4[1])
    ax_zeroing.plot(np.array([1,1])*vout_minus_zeroing_stop*1e9,
                    np.array([-np.average(vout_minus)/2, np.average(vout_minus)/2]),
                    '--', color = su_color_list_contrast4[1])
    
    ax_zeroing.plot(t[istart:istop]*1e9, vref[istart:istop], linewidth=2,
                    color = su_color_list_contrast4[3],
                    label = 'Vref')
    ax_zeroing.plot(np.array([1,1])*vref_zeroing_start*1e9,
                    np.array([-np.average(vref)/2, np.average(vref)/2]),
                    '--', linewidth=2,
                    color = su_color_list_contrast4[3])
    ax_zeroing.plot(np.array([1,1])*vref_zeroing_stop*1e9,
                    np.array([-np.average(vref)/2, np.average(vref)/2]),
                    '--', linewidth=2,
                    color = su_color_list_contrast4[3])
    
    ax_zeroing.legend(loc='lower left')
    ax_zeroing.set(xlabel = 'Time [ns]',
                   ylabel = 'Voltage [V]',
                   title = 'Zeroing Window Adjustment')
    ax_zeroing.grid()

# plot integration window
if show_integration_window_plot:
    fig_int, ax_int = plt.subplots(1,2)
    buffer_points = round(period * 0.1 / t_res)
    
    ax_int[0].plot(t[istart1-buffer_points:istart1+buffer_points],
                   vout_plus[istart1-buffer_points:istart1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[0])
    ax_int[0].plot(t[istart1-buffer_points:istart1+buffer_points],
                   vout_minus[istart1-buffer_points:istart1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[1])
    ax_int[0].plot(t[istart1-buffer_points:istart1+buffer_points],
                   vref[istart1-buffer_points:istart1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[3])
    ax_int[0].plot(t[istart1-buffer_points:istart1+buffer_points],
                   vdut[istart1-buffer_points:istart1+buffer_points],
                   linewidth=4, color = su_color_list_contrast4[2])
    
    ax_int[0].plot(np.array([1,1])*t[istart1],
                   np.array([1.1*max(np.concatenate([vout_plus, vout_minus, vref])),
                             1.1*min(vdut-10)]),
                   '--k')
    
    ax_int[1].plot(t[istop1-buffer_points:istop1+buffer_points],
                   vout_plus[istop1-buffer_points:istop1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[0],
                   label = 'vout+')
    ax_int[1].plot(t[istop1-buffer_points:istop1+buffer_points],
                   vout_minus[istop1-buffer_points:istop1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[1],
                   label = 'vout-')
    ax_int[1].plot(t[istop1-buffer_points:istop1+buffer_points],
                   vref[istop1-buffer_points:istop1+buffer_points],
                   linewidth=2, color = su_color_list_contrast4[3],
                   label = 'vref')
    ax_int[1].plot(t[istop1-buffer_points:istop1+buffer_points],
                   vdut[istop1-buffer_points:istop1+buffer_points],
                   linewidth=4, color = su_color_list_contrast4[2],
                   label = 'vdut')
    
    ax_int[1].plot(np.array([1,1])*t[istop1],
                   np.array([1.1*max(np.concatenate([vout_plus, vout_minus, vref])),
                             1.1*min(vdut-10)]),
                   '--k')
    ax_int[1].legend(loc='upper right')
    
# deskewing plot
if show_deskewing_plot:
    fig_deskew, ax_deskew = plt.subplots()
    #fig_deskew.set_figheight(8)
    istart = t0_index
    istop = istart + round(period_points_float)
    
    ax_deskew.plot(t[istart:istop], vout_plus[istart:istop], linewidth=2,
                      color = su_color_list_contrast4[0],
                      label = 'vout+')
    ax_deskew.plot(t[istart:istop], vout_minus[istart:istop], linewidth=2,
                      color = su_color_list_contrast4[1],
                      label = 'vout-')
    ax_deskew.plot(t[istart:istop], vref[istart:istop], linewidth=2,
                      color = su_color_list_contrast4[3],
                      label = 'vref')
    ax_deskew.legend()
    ax_deskew.grid()
    
# input traces plot
if plot_input_traces:
    fig_in, ax_in = plt.subplots()
    ax_gate = ax_in.twinx()
    ax_in.plot(scope_data_og[:,0]*1e9, scope_data_og[:,1], linewidth=2,
               color = su_color_list_contrast4[0],
               label = 'vout+')
    ax_in.plot(scope_data_og[:,0]*1e9, scope_data_og[:,2], linewidth=2,
               color = su_color_list_contrast4[1],
               label = 'vout-')
    ax_gate.plot(scope_data_og[:,0]*1e9, scope_data_og[:,3], linewidth=2,
               color = su_color_list_contrast4[2],
               label = 'vgate')
    ax_gate.set_ylim(-3, 12)
    ax_in.plot(scope_data_og[:,0]*1e9, scope_data_og[:,4], linewidth=2,
               color = su_color_list_contrast4[3],
               label = 'vref')
    ax_in.set(title = 'Input scope traces',
              ylabel = 'Trace voltages [V]',
              xlabel = 'Time [ns]')
    
# dv/dt plot (slew rate of DUT voltage)
if plot_sine_dvdt:
    fig_dvdt, ax_dvdt = plt.subplots()
    rise_index = istart1 + round(period_points_float/4) + rise_adjust
    fall_index = istart1 + round(period_points_float*3/4) + fall_adjust
    buffer_points = round(period / t_res * 1/4 * dvdt_buffer)
    max_vdut = max(vdut)
    min_vdut = min(vdut)
    
    dvdt1 = rise_index - buffer_points
    dvdt2 = rise_index + buffer_points
    dvdt3 = fall_index - buffer_points
    dvdt4 = fall_index + buffer_points
    
    up_m, up_b = np.polyfit(t[dvdt1:dvdt2], vdut[dvdt1:dvdt2], 1)
    rise_tmin = (min_vdut - up_b) / up_m
    rise_tmax = (max_vdut - up_b) / up_m
    
    ax_dvdt.plot(t[istart1:istop1]*1e9,
                 vdut[istart1:istop1],
                 linewidth=2, 
                 color = su_color_dict.get('cardinal_red'))
    ax_dvdt.plot(np.array([rise_tmin, rise_tmax])*1e9,
                 np.array([rise_tmin, rise_tmax])*up_m + up_b,
                 '--', linewidth=2, color = su_color_dict.get('palo_alto') + '77')
    plt.text(t[dvdt2]*1e9,
             -0, 'dvdt = ' + str(round(up_m/1e6)) + ' MV/s', fontsize=8)
    
    down_m, down_b = np.polyfit(t[dvdt3:dvdt4], vdut[dvdt3:dvdt4], 1)
    fall_tmin = (max_vdut - down_b) / down_m
    fall_tmax = (min_vdut - down_b) / down_m
    
    ax_dvdt.plot(np.array([fall_tmin, fall_tmax])*1e9,
                 np.array([fall_tmin, fall_tmax])*down_m + down_b,
                 '--', linewidth=2, color = su_color_dict.get('palo_alto') + '77')
    plt.text(t[dvdt3]*1e9,
             -0, 'dvdt = ' + str(round(down_m/1e6)) + ' MV/s', fontsize=8)
    
    
    ax_dvdt.plot(np.array([1, 1])*t[dvdt1]*1e9, 
                    np.array([min_vdut, max_vdut]), '--',
                    color = su_color_dict.get('poppy') + '77')
    ax_dvdt.plot(np.array([1, 1])*t[dvdt2]*1e9, 
                    np.array([min_vdut, max_vdut]), '--',
                    color = su_color_dict.get('poppy') + '77')
    ax_dvdt.plot(np.array([1, 1])*t[dvdt3]*1e9, 
                    np.array([min_vdut, max_vdut]), '--',
                    color = su_color_dict.get('poppy') + '77')
    ax_dvdt.plot(np.array([1, 1])*t[dvdt4]*1e9, 
                    np.array([min_vdut, max_vdut]), '--',
                    color = su_color_dict.get('poppy') + '77')
    
    dvdt_avg = (abs(up_m) + abs(down_m)) / 2
    fig_dvdt.suptitle('DUT slew: ' + str(round(dvdt_avg/1e6)) + 'MV/s' + \
                      ', DUT Vpp: ' + str(round(max_vdut)) + 'V')
    
# Eoss cumulative plot
if plot_Eoss_cum:
    fig_Eoss, ax_Eoss = plt.subplots()
    ax_Eoss.plot(t_int[1:]*1e9, Ediss_cum*1e6)
    ax_Eoss.set(title = 'Cumulative Eoss over integration time',
                xlabel = 'Time [ns]',
                ylabel = 'Eoss [$\mu$J]')
    ax_Eoss.grid()

# QV plot
if plot_QV:
    fig_QV, ax_QV = plt.subplots()
    ax_QV.plot(qoss_int[:round(len(qoss_int)/2)], vdut_int[:round(len(qoss_int)/2)], '-*', linewidth=2,
             color = su_color_dict.get('palo_alto'),
    label = 'Charge Up')
    ax_QV.plot(qoss_int[round(len(qoss_int)/2):], vdut_int[round(len(qoss_int)/2):], '-*', linewidth=2,
             color = su_color_dict.get('cardinal_red'),
             label = 'Charge Down')
    ax_QV.legend(loc = 'lower right')
    ax_QV.grid()
    ax_QV.set(title = 'QV Plot: ' + summary_file[24:-4],
              xlabel = 'Charge [nC]',
              ylabel = 'Voss [V]')
    plt.text(0.05*max(qoss_int), 0.75*max(vdut_int), 'Ediss = ' + str(Ediss), fontsize=8)
    
















