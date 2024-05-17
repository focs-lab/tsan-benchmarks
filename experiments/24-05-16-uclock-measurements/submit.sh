#!/bin/sh

qsub job-base.pbs
qsub job-base-sampling.pbs
qsub job-uclock.pbs
qsub job-uclock-sampling.pbs
qsub job-base-sse.pbs
qsub job-base-sse-sampling.pbs
qsub job-base-slots.pbs
qsub job-base-slots-sse.pbs
