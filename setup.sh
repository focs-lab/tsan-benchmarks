#!/bin/bash

echo "[*] This script was tested on Ubuntu 22.04. It may not work on other systems or other versions of Ubuntu."

ROOT=$(pwd)
ROOT_BUILD=$(pwd)/build
ROOT_BIN=$(pwd)/bin

if [[ -z "${CUSTOM_LLVM_BUILD_PATH}" ]]; then
  echo '[!] Please set $CUSTOM_LLVM_BUILD_PATH to the directory of your custom LLVM build. E.g.'
  echo 'export CUSTOM_LLVM_BUILD_PATH=/home/daniel/llvm-project/build'
  exit 1
else
  LLVM_BUILD_PATH="${CUSTOM_LLVM_BUILD_PATH}"
  CC="${CUSTOM_LLVM_BUILD_PATH}/bin/clang"
  CXX="${CUSTOM_LLVM_BUILD_PATH}/bin/clang++"
  LIBOMP_INCLUDE_PATH=${CUSTOM_LLVM_BUILD_PATH}/runtimes/runtimes-bins/openmp/runtime/src
  LIBOMP_LIB_PATH=${CUSTOM_LLVM_BUILD_PATH}/runtimes/runtimes-bins/openmp/runtime/src
  LIBOMP_FLAGS="-fopenmp -I$LIBOMP_INCLUDE_PATH -L$LIBOMP_LIB_PATH"
fi

install_dependencies() {
    echo "[+] Install dependencies (requires sudo):"
    sudo apt update
    sudo apt install -y git bc
    sudo apt install -y libncurses5-dev libncursesw5-dev
    sudo apt install -y libreadline-dev
    sudo apt install -y libc6
    sudo apt install -y libdb++-dev
    sudo apt install -y libaio-dev
    sudo apt install -y libjemalloc-dev
    sudo apt install -y libnuma-dev
    sudo apt install -y unzip
    sudo apt install -y libboost-all-dev
    sudo apt install -y libmpich-dev
    sudo apt install -y zsh                 # used by runner.py
}

build_ompscr() {
    cd $ROOT_BUILD

    rm -rf OmpSCR_v2.0
    wget https://master.dl.sourceforge.net/project/ompscr/OmpSCR/OmpSCR%20Full%20Distribution%20v2.0/OmpSCR_v2.0.tar.gz
    tar -xzvf OmpSCR_v2.0.tar.gz
    rm OmpSCR_v2.0.tar.gz
    cd OmpSCR_v2.0
    cp config/templates/none.cf.mk config/templates/user.cf.mk

    ### Modify the config
    sed -i "s/OSCR_USE_C=n/OSCR_USE_C=y/g"     config/templates/user.cf.mk
    sed -i "s/OSCR_USE_CPP=n/OSCR_USE_CPP=y/g" config/templates/user.cf.mk

    sed -i "s*OSCR_CC=*OSCR_CC=$CC*g"      config/templates/user.cf.mk
    sed -i "s*OSCR_CPPC=*OSCR_CPPC=$CXX*g" config/templates/user.cf.mk

    sed -i "s*OSCR_C_OMPFLAG=*OSCR_C_OMPFLAG=$LIBOMP_FLAGS*g"     config/templates/user.cf.mk
    sed -i "s*OSCR_CPP_OMPFLAG=*OSCR_CPP_OMPFLAG=$LIBOMP_FLAGS*g" config/templates/user.cf.mk

    sed -i "s/OSCR_C_OTHERS=/OSCR_C_OTHERS=-fsanitize=thread/g" config/templates/user.cf.mk
    sed -i "s/OSCR_CPP_OTHERS=/OSCR_CPP_OTHERS=-fsanitize=thread/g" config/templates/user.cf.mk

    # need these line to prevent compilation error due to -W-implicit-function-declaration
    sed -i "s/#include <stdio.h>/#include <stdio.h>\n#include <stdlib.h>/g" applications/c_GraphSearch/AStack.c
    sed -i "s/#include <stdio.h>/#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>/g" applications/c_GraphSearch/tg.c
    sed -i "s/extern void \*OSCR_calloc(size_t nmemb, size_t size);/extern void *OSCR_calloc(size_t nmemb, size_t size);\nextern void *OSCR_malloc(size_t size);/g" include/OmpSCR.h
    sed -i "s/#include <omp.h>//g" applications/cpp_sortOpenMP/cpp_qsomp2.cpp

    ### Build
    gmake all

    ## Move the binaries out
    rm -rf $ROOT_BIN/OmpSCR
    mkdir $ROOT_BIN/OmpSCR
    mv bin/* $ROOT_BIN/OmpSCR

    cd $ROOT
}

build_dracc() {
    cd $ROOT_BUILD

    rm -rf DRACC
    git clone https://github.com/RWTH-HPC/DRACC

    cd DRACC/OpenMP
    git checkout ef76b1d7c48f79ad5f2d36f796de8c8c826382b3           # tested this script on this commit
    mkdir bin

    ## Remove testcases that perform offloading because they will fail to compile
    rm src/DRACC_OMP_021_Large_Data_Copy_no.c

    ## Build
    CC=$CC FLAGS="-fsanitize=thread" FLAGS_OPENMP="$LIBOMP_FLAGS" make all

    ## Move the binaries out
    rm -rf $ROOT_BIN/DRACC
    mkdir $ROOT_BIN/DRACC
    mv bin/* $ROOT_BIN/DRACC

    cd $ROOT
}

build_drb() {
    cd $ROOT_BUILD

    rm -rf dataracebench
    git clone https://github.com/LLNL/dataracebench.git

    cd dataracebench
    git checkout e1bffc57f35f2751afea6c9379b5863e0b2abfd9           # tested this script on this commit

    # small trick to make the test cases dont run
    # if we stick to the pinned commit version above, there will not be issues
    sed -i 's*compilereturn=$?;*continue*g' scripts/test-harness.sh
    sed -i "s*python3 scripts/metric.py*continue #*g" scripts/test-harness.sh

    CLANG="$CC $LIBOMP_FLAGS" CLANGXX="$CXX $LIBOMP_FLAGS" ./check-data-races.sh --tsan-clang c

    rm -rf $ROOT_BIN/DRB
    mkdir $ROOT_BIN/DRB
    mv results/exec/* $ROOT_BIN/DRB

    cd $ROOT
}

build_c11_silo() {
    pushd .

    cd silo
    ./compile.sh

    rm -rf $ROOT_BIN/silo
    mkdir $ROOT_BIN/silo
    cp out-perf.masstree/benchmarks/dbtest $ROOT_BIN/silo

    popd
}

build_c11_iris() {
    pushd .

    cd iris
    ./compile.sh

    rm -rf $ROOT_BIN/iris
    mkdir $ROOT_BIN/iris
    cp test_lfringbuffer $ROOT_BIN/iris
    cp test2 $ROOT_BIN/iris

    popd
}

build_c11_mabain() {
    pushd .

    cd mabain
    rm -rf build
    rm -rf install
    mkdir install

    sed -i "s*~/mabain*$(pwd)/install*g" compile.sh
    sed -i "s*mkdir ./tmp_dir**g" compile.sh
    sed -i "s*MABAIN_INSTALL_DIR) -lmabain*MABAIN_INSTALL_DIR)/lib -lmabain*g" examples/Makefile
    sed -i "s*Werror*Wno-error*g" examples/Makefile

    ./compile.sh

    rm -rf $ROOT_BIN/mabain
    mkdir $ROOT_BIN/mabain
    
    mv examples/mb_insert_test $ROOT_BIN/mabain
    mv examples/mb_iterator_test $ROOT_BIN/mabain
    mv examples/mb_longest_prefix_test $ROOT_BIN/mabain
    mv examples/mb_lookup_test $ROOT_BIN/mabain
    mv examples/mb_memory_only_test $ROOT_BIN/mabain
    mv examples/mb_multi_proc_test $ROOT_BIN/mabain
    mv examples/mb_multi_thread_insert_test $ROOT_BIN/mabain
    mv examples/mb_rc_test $ROOT_BIN/mabain
    mv examples/mb_remove_test $ROOT_BIN/mabain
    mv install $ROOT_BIN/mabain

    popd
}

build_c11_gdax() {
    pushd .

    cd gdax-orderbook-hpp
    cd demo

    # prepare the dependencies
    rm -rf dependencies
    mkdir dependencies
    cd dependencies

    ## libcds-2.3.2
    wget https://github.com/khizmax/libcds/archive/refs/tags/v2.3.2.zip
    unzip v2.3.2.zip
    rm v2.3.2.zip

    ## rapidjson-1.1.0
    wget https://github.com/Tencent/rapidjson/archive/refs/tags/v1.1.0.zip
    unzip v1.1.0.zip
    rm v1.1.0.zip

    ## websocketpp-0.8.2
    wget https://github.com/zaphoyd/websocketpp/archive/refs/tags/0.8.2.zip
    unzip 0.8.2.zip
    rm 0.8.2.zip

    cd ../..

    # fix errors
    sed -i 's*websocketpp-0.7.0*websocketpp-0.8.2*g' demo/Makefile
    sed -i 's*`pwd`/../..:$(PATH)*"$(shell pwd)/../..:$(PATH)"*g' demo/Makefile
    ./compile.sh

    rm -rf $ROOT_BIN/gdax
    mkdir $ROOT_BIN/gdax
    mv demo/dependencies $ROOT_BIN/gdax
    mv demo/demo $ROOT_BIN/gdax
    cp -R demo/*.txt $ROOT_BIN/gdax     # IMPT: without these text files the test case wont run (just hangs and waits)

    popd
}

build_c11_cdschecker() {
    pushd .

    cd cdschecker_modified_benchmarks

    # skip this one for now because it requires building and including c11tester
    # need their custom threads.h and libthreads.cc
    git checkout Makefile
    sed -i 's/ms-queue/ms-queue-tsan11/g' Makefile
    rm ms-queue-tsan11/*.o              # remove the .o files that came with the repo (want to build our own)

    make

    rm -rf $ROOT_BIN/cdschecker
    mkdir $ROOT_BIN/cdschecker
    mv barrier/barrier $ROOT_BIN/cdschecker
    mv chase-lev-deque/chase-lev-deque $ROOT_BIN/cdschecker
    mv dekker-fences/dekker-fences $ROOT_BIN/cdschecker
    mv linuxrwlocks/linuxrwlocks $ROOT_BIN/cdschecker
    mv mcs-lock/mcs-lock $ROOT_BIN/cdschecker
    mv mpmc-queue/mpmc-queue $ROOT_BIN/cdschecker
    mv ms-queue-tsan11/ms-queue $ROOT_BIN/cdschecker
    mv spsc-queue/spsc-queue $ROOT_BIN/cdschecker

    popd
}

build_c11_benchmarks() {
    cd $ROOT_BUILD

    rm -rf c11concurrency-benchmarks
    git clone https://github.com/dwslim/c11concurrency-benchmarks.git

    cd c11concurrency-benchmarks
    git checkout dc040d31d24e00df0c5e5a7206804fe6503798c1 > /dev/null           # tested this script on this commit

    echo -e "#/bin/bash\n$CC -fsanitize=thread \$@" > ./clang
    echo -e "#/bin/bash\n$CC -fsanitize=thread \$@" > ./gcc
    echo -e "#/bin/bash\n$CXX -fsanitize=thread -Wno-error=vla-cxx-extension -Wno-error=cast-align \$@" > ./clang++
    echo -e "#/bin/bash\n$CXX -fsanitize=thread \$@" > ./g++

    build_c11_silo
    build_c11_iris
    build_c11_mabain
    build_c11_gdax
    build_c11_cdschecker
    
    cd $ROOT
}

build_npb() {
    cd $ROOT_BUILD

    rm -rf NPB3.4.2
    wget https://www.nas.nasa.gov/assets/npb/NPB3.4.2.tar.gz
    tar -xzvf NPB3.4.2.tar.gz
    rm NPB3.4.2.tar.gz

    cd NPB3.4.2
    cd NPB3.4-OMP

    # choose the suite of programs to build
    echo -e "is\tS" > config/suite.def
    echo -e "is\tW" >> config/suite.def
    echo -e "is\tA" >> config/suite.def
    echo -e "is\tB" >> config/suite.def
    echo -e "is\tC" >> config/suite.def

    echo -e "dc\tS" >> config/suite.def
    echo -e "dc\tW" >> config/suite.def
    echo -e "dc\tA" >> config/suite.def
    echo -e "dc\tB" >> config/suite.def

    # config for make
    cp config/make.def.template config/make.def
    sed -i "s*gcc*$CC*g" config/make.def
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread*g" config/make.def
    make suite

    # copy the bins out
    rm -rf $ROOT_BIN/npb-omp
    mkdir $ROOT_BIN/npb-omp
    cp bin/* $ROOT_BIN/npb-omp

    cd $ROOT
}

build_miniFE() {
    cd $ROOT_BUILD

    rm -rf miniFE-2.2.0
    wget https://github.com/Mantevo/miniFE/archive/refs/tags/2.2.0.tar.gz
    tar -xzvf 2.2.0.tar.gz
    rm 2.2.0.tar.gz

    cd miniFE-2.2.0

    cd openmp/src
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread*g" Makefile
    sed -i "s*mpicxx*$CXX*g" Makefile
    sed -i "s*mpicc*$CC*g" Makefile
    sed -i "s*-DHAVE_MPI -DMPICH_IGNORE_CXX_SEEK**g" Makefile

    make

    rm -rf $ROOT_BIN/miniFE
    mkdir $ROOT_BIN/miniFE
    cp miniFE.x $ROOT_BIN/miniFE

    cd $ROOT
}

build_miniAMR() {
    cd $ROOT_BUILD

    rm -rf miniAMR-1.7.0
    wget https://github.com/Mantevo/miniAMR/archive/refs/tags/v1.7.0.tar.gz
    tar -xzvf v1.7.0.tar.gz
    rm v1.7.0.tar.gz

    cd miniAMR-1.7.0

    cd openmp
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread*g" Makefile
    sed -i "s*CC   = cc*CC   = mpicc*g" Makefile
    sed -i "s*LD   = cc*LD   = mpicc*g" Makefile
    sed -i "s*LDFLAGS =*LDFLAGS =\$(CFLAGS)*g" Makefile
    sed -i "s*lgomp*lomp*g" Makefile

    ## there is a "multiple definitions error" by the linker
    ## no idea how other people got it to compile
    sed -i "s*^double*static double*g" block.h comm.h timer.h
    sed -i "s*^int*static int*g" block.h comm.h timer.h
    sed -i "s*^long long*static long long*g" block.h comm.h timer.h
    sed -i "s*^num_sz*static num_sz*g" block.h comm.h timer.h
    sed -i "s*^par_comm*static par_comm*g" block.h comm.h timer.h
    sed -i "s*^MPI_Comm*static MPI_Comm*g" block.h comm.h timer.h
    sed -i "s*^MPI_Request*static MPI_Request*g" block.h comm.h timer.h
    sed -i "s*^dot*static dot*g" block.h comm.h timer.h
    sed -i "s*^block *static block *g" block.h comm.h timer.h
    sed -i "s*^object *static object *g" block.h comm.h timer.h
    sed -i "s*^sorted_block *static sorted_block *g" block.h comm.h timer.h
    sed -i "s*^parent *static parent *g" block.h comm.h timer.h

    sed -i "s*int num_cells;**g" stencil.c

    OMPI_CC=$CC make

    rm -rf $ROOT_BIN/miniAMR
    mkdir $ROOT_BIN/miniAMR
    cp ma.x $ROOT_BIN/miniAMR

    cd $ROOT
}

build_SimpleMOC() {
    cd $ROOT_BUILD

    rm -rf SimpleMOC-4
    wget https://github.com/ANL-CESAR/SimpleMOC/archive/refs/tags/v4.tar.gz
    tar -xzvf v4.tar.gz
    rm v4.tar.gz

    cd SimpleMOC-4/src

    sed -i "s*CC = gcc*CC = $CC*g" Makefile
    sed -i "s*-std=gnu99*-std=gnu99 -fsanitize=thread*g" Makefile
    sed -i "s*-fopenmp*$LIBOMP_FLAGS*g" Makefile

    make

    rm -rf $ROOT_BIN/SimpleMOC
    mkdir $ROOT_BIN/SimpleMOC
    cp SimpleMOC $ROOT_BIN/SimpleMOC
    cp default.in $ROOT_BIN/SimpleMOC

    cd $ROOT
}

build_HPCCG() {
    cd $ROOT_BUILD

    rm -rf HPCCG
    git clone https://github.com/Mantevo/HPCCG.git

    cd HPCCG
    git checkout 80dd2f12a4e8aa70c330a5686cdda3fd187c2545           # script was tested on this commit

    sed -i "s*CXX=/usr/local/bin/g++*CXX=$CXX -fsanitize=thread*g" Makefile
    sed -i "s*LINKER=/usr/local/bin/g++*LINKER=$CXX -fsanitize=thread*g" Makefile
    sed -i "s*USE_OMP =*USE_OMP = -DUSING_OMP*g" Makefile
    sed -i "s*#OMP_FLAGS = -fopenmp*OMP_FLAGS = $LIBOMP_FLAGS*g" Makefile
    sed -i "s*-ftree-vectorizer-verbose=2**g" Makefile
    make

    rm -rf $ROOT_BIN/HPCCG
    mkdir $ROOT_BIN/HPCCG
    mv test_HPCCG $ROOT_BIN/HPCCG

    cd $ROOT
}

build_kripke() {
    cd $ROOT_BUILD

    rm -rf Kripke
    git clone https://github.com/LLNL/Kripke

    cd Kripke

    git checkout v1.2.7     # script was tested on this version
    git submodule update --init --recursive

    mkdir build
    cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="$LIBOMP_FLAGS -fsanitize=thread" -DCMAKE_CXX_FLAGS="$LIBOMP_FLAGS -fsanitize=thread" -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DCMAKE_LINKER=$CC -DCMAKE_CXX_FLAGS_RELEASE="-O3 -ffast-math" -DENABLE_OPENMP=ON -DENABLE_MPI=OFF

    make -j12

    rm -rf $ROOT_BIN/kripke
    mkdir $ROOT_BIN/kripke
    cp kripke.exe $ROOT_BIN/kripke
    cp -R bin $ROOT_BIN/kripke

    cd $ROOT
}

build_lulesh() {
    cd $ROOT_BUILD

    rm -rf LULESH
    git clone https://github.com/LLNL/LULESH

    cd LULESH
    git checkout 3e01c40b3281aadb7f996525cdd4a3354f6d3801           # script was tested on this commit

    rm -rf build
    mkdir build
    cd build
    
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$CXX -DWITH_MPI=OFF -DWITH_OPENMP=ON -DOpenMP_CXX_FLAGS="$LIBOMP_FLAGS" -DOpenMP_CXX_LIB_NAMES="libomp" -DOpenMP_libomp_LIBRARY="$LLVM_BUILD_PATH/runtimes/runtimes-bins/openmp/runtime/src/libomp.so" -DCMAKE_CXX_FLAGS="-fsanitize=thread"

    make -j12

    rm -rf $ROOT_BIN/lulesh
    mkdir $ROOT_BIN/lulesh
    cp lulesh2.0 $ROOT_BIN/lulesh

    cd $ROOT
}

build_xsbench() {
    cd $ROOT_BUILD

    rm -rf XSBench-20
    wget https://github.com/ANL-CESAR/XSBench/archive/refs/tags/v20.tar.gz
    tar -xzvf v20.tar.gz
    rm v20.tar.gz

    cd XSBench-20

    cd openmp-threading

    sed -i "s*-fopenmp*$LIBOMP_FLAGS*g" Makefile
    sed -i "s*-Wall*-Wall -fsanitize=thread*g" Makefile

    CC=$CC CXX=$CXX make -j12

    rm -rf $ROOT_BIN/xsbench
    mkdir $ROOT_BIN/xsbench
    cp XSBench $ROOT_BIN/xsbench

    cd $ROOT
}

build_rsbench() {
    cd $ROOT_BUILD

    rm -rf RSBench-13
    wget https://github.com/ANL-CESAR/RSBench/archive/refs/tags/v13.tar.gz
    tar -xzvf v13.tar.gz
    rm v13.tar.gz

    cd RSBench-13

    cd openmp-threading

    sed -i "s*-fopenmp*$LIBOMP_FLAGS*g" Makefile
    sed -i "s*-Wall*-Wall -fsanitize=thread*g" Makefile

    CC=$CC CXX=$CXX make -j10

    rm -rf $ROOT_BIN/rsbench
    mkdir $ROOT_BIN/rsbench
    cp rsbench $ROOT_BIN/rsbench

    cd $ROOT
}

build_quicksilver() {
    cd $ROOT_BUILD

    rm -rf Quicksilver-1.0
    wget https://github.com/LLNL/Quicksilver/archive/refs/tags/V1.0.tar.gz
    tar -xzvf V1.0.tar.gz
    rm V1.0.tar.gz

    cd Quicksilver-1.0/src

    sed -i "s*CXX =*CXX = $CXX*" Makefile
    sed -i "s*CXXFLAGS =*CXXFLAGS = -fsanitize=thread $LIBOMP_FLAGS -DHAVE_OPENMP*" Makefile
    sed -i "s*CPPFLAGS =*CPPFLAGS = -fsanitize=thread $LIBOMP_FLAGS -DHAVE_OPENMP*" Makefile
    sed -i "s*LDFLAGS =*LDFLAGS = -fsanitize=thread $LIBOMP_FLAGS -DHAVE_OPENMP*" Makefile

    make -j12

    rm -rf $ROOT_BIN/quicksilver
    mkdir $ROOT_BIN/quicksilver
    cp qs $ROOT_BIN/quicksilver

    cd ..
    cp -R Examples $ROOT_BIN/quicksilver

    cd $ROOT
}

build_comd() {
    cd $ROOT_BUILD

    rm -rf CoMD-1.1
    wget https://github.com/ECP-copa/CoMD/archive/refs/tags/v1.1.tar.gz
    tar -xzvf v1.1.tar.gz
    rm v1.1.tar.gz

    cd CoMD-1.1

    cd src-openmp
    cp Makefile.vanilla Makefile

    sed -i "s*DO_MPI = ON*DO_MPI = OFF*g" Makefile
    sed -i "s*CC = mpicc*CC = $CC*g" Makefile
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread*g" Makefile

    make -j12

    rm -rf $ROOT_BIN/comd
    mkdir $ROOT_BIN/comd
    cp ../bin/CoMD-openmp $ROOT_BIN/comd

    cd $ROOT
}

build_amg() {
    cd $ROOT_BUILD

    rm -rf AMG-1.2
    wget https://github.com/LLNL/AMG/archive/refs/tags/1.2.tar.gz
    tar -xzvf 1.2.tar.gz
    rm 1.2.tar.gz

    cd AMG-1.2
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread -Wno-error=implicit-function-declaration*" Makefile.include

    OMPI_CC=$CC make -j12

    rm -rf $ROOT_BIN/AMG
    mkdir $ROOT_BIN/AMG
    cp test/amg $ROOT_BIN/AMG

    cd $ROOT
}

build_gromacs() {
    cd $ROOT_BUILD

    rm gromacs-2024.1
    wget https://github.com/gromacs/gromacs/archive/refs/tags/v2024.1.tar.gz
    tar -xzvf v2024.1.tar.gz
    rm v2024.1.tar.gz

    cd gromacs-2024.1

    rm -rf $ROOT_BIN/gromacs
    mkdir $ROOT_BIN/gromacs
    mkdir $ROOT_BIN/gromacs/build
    cmake -B $ROOT_BIN/gromacs/build . -DGMX_BUILD_OWN_FFTW=ON -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS=-fsanitize=thread -DCMAKE_CXX_FLAGS=-fsanitize=thread -DOpenMP_CXX_FLAGS=-I$LIBOMP_INCLUDE_PATH -DOpenMP_CXX_LIB_NAMES="libomp" -DOpenMP_libomp_LIBRARY="$LLVM_BUILD_PATH/runtimes/runtimes-bins/openmp/runtime/src/libomp.so" -DOpenMP_C_FLAGS=-I$LIBOMP_INCLUDE_PATH -DOpenMP_C_LIB_NAMES="libomp" -DBUILD_SHARED_LIBS=ON
    make -C $ROOT_BIN/gromacs/build -j12

    mkdir $ROOT_BIN/gromacs/testcases
    cd $ROOT_BIN/gromacs/testcases
    wget http://ftp.gromacs.org/pub/benchmarks/water_GMX50_bare.tar.gz
    tar -xzvf water_GMX50_bare.tar.gz
    rm water_GMX50_bare.tar.gz

    cd $ROOT
}

build_graph500() {
    cd $ROOT_BUILD

    rm -rf graph500-2.1.4
    wget https://github.com/graph500/graph500/archive/refs/tags/graph500-2.1.4.tar.gz
    tar -xzvf graph500-2.1.4.tar.gz
    rm -rf graph500-2.1.4.tar.gz

    mv graph500-graph500-2.1.4 graph500-2.1.4
    cd graph500-2.1.4

    cp make-incs/make.inc-gcc make.inc
    sed -i "s*CFLAGS = -g -std=c99*CFLAGS = -g -std=c99 -fsanitize=thread*g" make.inc
    sed -i "s*LDLIBS = -lm -lrt*LDLIBS = -lm -lrt -fsanitize=thread*g" make.inc
    sed -i "s*CPPFLAGS = -DUSE_MMAP_LARGE -DUSE_MMAP_LARGE_EXT*CPPFLAGS = -DUSE_MMAP_LARGE -DUSE_MMAP_LARGE_EXT -fsanitize=thread*g" make.inc
    sed -i "s*-fopenmp*$LIBOMP_FLAGS*g" make.inc

    sed -i "s*-DGRAPH_GENERATOR_OMP*-DGRAPH_GENERATOR_OMP -fsanitize=thread*g" generator/Makefile.omp
    sed -i "s*LDFLAGS = -O3*LDFLAGS = -O3 -fsanitize=thread*g" generator/Makefile.omp
    sed -i "s*-fopenmp*$LIBOMP_FLAGS*g" generator/Makefile.omp
    sed -i "s*gcc*$CC*g" generator/Makefile.omp

    make

    rm -rf $ROOT_BIN/graph500
    mkdir $ROOT_BIN/graph500
    cp omp-csr/omp-csr $ROOT_BIN/graph500

    cd $ROOT
}

build_graphchi() {
    cd $ROOT_BUILD

    rm -rf graphchi-cpp
    git clone https://github.com/GraphChi/graphchi-cpp
    git checkout 6461c89f217f63482e2468d776bb942067f8288c                   # script was tested on this commit

    cd graphchi-cpp
    sed -i "s*g++*$CXX*g" Makefile
    sed -i "s*-fopenmp*$LIBOMP_FLAGS -fsanitize=thread -Wno-error=register*g" Makefile
    sed -i "s*-lz*-lz -fsanitize=thread*g" Makefile

    make -j12

    rm -rf $ROOT_BIN/graphchi
    mkdir $ROOT_BIN/graphchi

    cp -R bin $ROOT_BIN/graphchi
    cp -R conf $ROOT_BIN/graphchi

    cd $ROOT_BIN/graphchi
    mkdir data
    cd data
    wget https://snap.stanford.edu/data/facebook_combined.txt.gz
    gunzip facebook_combined.txt.gz

    cd $ROOT
}

rm -rf $ROOT_BUILD
rm -rf $ROOT_BIN
mkdir $ROOT_BUILD
mkdir $ROOT_BIN

install_dependencies
build_ompscr
build_dracc
build_drb
build_c11_benchmarks
build_npb
build_miniFE
build_miniAMR
build_SimpleMOC
build_HPCCG
build_kripke
build_lulesh
build_xsbench
build_rsbench
build_quicksilver
build_comd
build_amg
build_gromacs
build_graph500
build_graphchi
