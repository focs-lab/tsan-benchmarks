#!/bin/sh

qsub job-uclock.pbs
qsub job-uclock-sampling.pbs
qsub job-uclock-measurements.pbs
qsub job-uclock-measurements-sampling.pbs
