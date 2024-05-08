#!/bin/sh

#SBATCH -C xcne
#SBATCH --time=0-32
#SBATCH --partition=long
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32

# export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun python3 runner-perf.py medium 10
