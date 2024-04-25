#!/bin/sh

#SBATCH --time=30
#SBATCH --partition=standard
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun ~/perf/perf stat -d ../bin/HPCCG/test_HPCCG 64 64 64
