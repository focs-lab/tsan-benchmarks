#!/bin/bash

echo "[*] This script was tested on Ubuntu 22.04. It may not work on other systems or other versions of Ubuntu."
echo "[*] Please ensure that you have ran setup.sh once to set up all the project files first."

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
    cd OmpSCR_v2.0

    ### Build
    gmake clean
    gmake all

    ## Move the binaries out
    rm -rf $ROOT_BIN/OmpSCR
    mkdir $ROOT_BIN/OmpSCR
    mv bin/* $ROOT_BIN/OmpSCR

    cd $ROOT
}

build_dracc() {
    cd $ROOT_BUILD
    cd DRACC/OpenMP

    ## Build
    make clean
    CC=$CC FLAGS="-fsanitize=thread" FLAGS_OPENMP="$LIBOMP_FLAGS" make all

    ## Move the binaries out
    rm -rf $ROOT_BIN/DRACC
    mkdir $ROOT_BIN/DRACC
    mv bin/* $ROOT_BIN/DRACC

    cd $ROOT
}

build_drb() {
    cd $ROOT_BUILD

    cd dataracebench
    git checkout e1bffc57f35f2751afea6c9379b5863e0b2abfd9           # tested this script on this commit

    rm -rf results/exec
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

    cd c11concurrency-benchmarks
    # they have their custom build script compile.sh so I prefer not to call make clean
    # in case I miss out anything
    # better to just use git clean to remove all untracked files and git-ignored files
    git clean -fdx

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

    cd NPB3.4.2
    cd NPB3.4-OMP

    make clean
    make suite

    # copy the bins out
    rm -rf $ROOT_BIN/npb-omp
    mkdir $ROOT_BIN/npb-omp
    mv bin/* $ROOT_BIN/npb-omp

    cd $ROOT
}

build_miniFE() {
    cd $ROOT_BUILD

    cd miniFE-2.2.0

    cd openmp/src

    make clean
    make

    rm -rf $ROOT_BIN/miniFE
    mkdir $ROOT_BIN/miniFE
    mv miniFE.x $ROOT_BIN/miniFE

    cd $ROOT
}

build_miniAMR() {
    cd $ROOT_BUILD

    cd miniAMR-1.7.0

    cd openmp

    make clean
    OMPI_CC=$CC make

    rm -rf $ROOT_BIN/miniAMR
    mkdir $ROOT_BIN/miniAMR
    mv ma.x $ROOT_BIN/miniAMR

    cd $ROOT
}

build_SimpleMOC() {
    cd $ROOT_BUILD

    cd SimpleMOC-4/src

    make clean
    make

    rm -rf $ROOT_BIN/SimpleMOC
    mkdir $ROOT_BIN/SimpleMOC
    mv SimpleMOC $ROOT_BIN/SimpleMOC
    mv default.in $ROOT_BIN/SimpleMOC

    cd $ROOT
}

build_HPCCG() {
    cd $ROOT_BUILD

    cd HPCCG
    
    make clean
    make

    rm -rf $ROOT_BIN/HPCCG
    mkdir $ROOT_BIN/HPCCG
    mv test_HPCCG $ROOT_BIN/HPCCG

    cd $ROOT
}

build_kripke() {
    cd $ROOT_BUILD

    cd Kripke

    rm -rf build
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

    cd LULESH

    rm -rf build
    mkdir build
    cd build
    
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$CXX -DWITH_MPI=OFF -DWITH_OPENMP=ON -DOpenMP_CXX_FLAGS="$LIBOMP_FLAGS" -DOpenMP_CXX_LIB_NAMES="libomp" -DOpenMP_libomp_LIBRARY="$LLVM_BUILD_PATH/runtimes/runtimes-bins/openmp/runtime/src/libomp.so" -DCMAKE_CXX_FLAGS="-fsanitize=thread"
    make -j12

    rm -rf $ROOT_BIN/lulesh
    mkdir $ROOT_BIN/lulesh
    mv lulesh2.0 $ROOT_BIN/lulesh

    cd $ROOT
}

build_xsbench() {
    cd $ROOT_BUILD

    cd XSBench-20

    cd openmp-threading

    make clean
    CC=$CC CXX=$CXX make -j12

    rm -rf $ROOT_BIN/xsbench
    mkdir $ROOT_BIN/xsbench
    mv XSBench $ROOT_BIN/xsbench

    cd $ROOT
}

build_rsbench() {
    cd $ROOT_BUILD

    cd RSBench-13
    cd openmp-threading

    make clean
    CC=$CC CXX=$CXX make -j10

    rm -rf $ROOT_BIN/rsbench
    mkdir $ROOT_BIN/rsbench
    mv rsbench $ROOT_BIN/rsbench

    cd $ROOT
}

build_quicksilver() {
    cd $ROOT_BUILD

    cd Quicksilver-1.0/src

    make clean
    make -j12

    rm -rf $ROOT_BIN/quicksilver
    mkdir $ROOT_BIN/quicksilver
    mv qs $ROOT_BIN/quicksilver

    cd ..
    cp -R Examples $ROOT_BIN/quicksilver

    cd $ROOT
}

build_comd() {
    cd $ROOT_BUILD

    cd CoMD-1.1
    cd src-openmp
    
    make clean
    make -j12

    rm -rf $ROOT_BIN/comd
    mkdir $ROOT_BIN/comd
    mv ../bin/CoMD-openmp $ROOT_BIN/comd

    cd $ROOT
}

build_amg() {
    cd $ROOT_BUILD

    cd AMG-1.2

    make clean
    OMPI_CC=$CC make -j12

    rm -rf $ROOT_BIN/AMG
    mkdir $ROOT_BIN/AMG
    mv test/amg $ROOT_BIN/AMG

    cd $ROOT
}

build_gromacs() {
    cd $ROOT_BUILD

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
    cd graph500-2.1.4

    make clean
    make

    rm -rf $ROOT_BIN/graph500
    mkdir $ROOT_BIN/graph500
    mv omp-csr/omp-csr $ROOT_BIN/graph500

    cd $ROOT
}

build_graphchi() {
    cd $ROOT_BUILD

    cd graphchi-cpp
    
    make clean
    make -j12

    rm -rf $ROOT_BIN/graphchi/bin
    cp -R bin $ROOT_BIN/graphchi

    cd $ROOT
}

rm -rf $ROOT_BIN
mkdir $ROOT_BIN

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
