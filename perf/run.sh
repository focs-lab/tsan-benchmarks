#!/bin/sh

~/perf/perf stat -d /tmp/danilws/c_fft.par 8&
pidof c_fft.par > /tmp/danilws/pid
sleep 8
cat /proc/$(pidof c_fft.par)/status
wait
