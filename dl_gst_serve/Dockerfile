FROM ubuntu:18.04

# Install gstreamer and opencv dependencies
RUN \ 
    apt-get update && apt-get upgrade -y && \
    apt-get install -y libgstreamer1.0-0 \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-plugins-ugly \
            gstreamer1.0-libav \
            gstreamer1.0-doc \
            gstreamer1.0-tools \
            libgstreamer1.0-dev \
            libgstreamer-plugins-base1.0-dev && \

    apt-get install -y \
        wget \
        unzip \
        libtbb2 \
        libtbb-dev

RUN apt-get install -y software-properties-common && \
    apt-get update

RUN add-apt-repository "deb http://security.ubuntu.com/ubuntu xenial-security main" && \
    apt update && \
    apt install libjasper1 libjasper-dev
RUN apt-get install -y \
        build-essential \
        cmake \
        git \
        pkg-config \
        libjpeg8-dev \
        libtiff5-dev \
        libpng-dev \
        libgtk2.0-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libatlas-base-dev \
        gfortran \
        libhdf5-dev \
        python3.6 \
        python3.6-dev

RUN \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py && \
    pip install numpy && \
    apt-get autoclean && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Download OpenCV 3.2.0 and install
RUN \
    cd ~ && \
    wget https://github.com/Itseez/opencv/archive/4.1.0.zip && \
    unzip 4.1.0.zip && \
    mv ~/opencv-4.1.0/ ~/opencv/ && \
    rm -rf ~/4.1.0.zip && \

    cd /root/opencv && \
    mkdir build && \
    cd build && \
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
        -D CMAKE_INSTALL_PREFIX=/usr/local \
        -D INSTALL_C_EXAMPLES=OFF \
        -D INSTALL_PYTHON_EXAMPLES=ON \
        -D BUILD_EXAMPLES=ON .. && \

    cd ~/opencv/build && \
    make -j $(nproc) && \
    make install && \
    ldconfig


# Copying the content in the app directory. Ignoring the content in .dockerignore
COPY . /app

# Changing Working directory
WORKDIR /app 

RUN python3 -m pip install -r requirements.txt

# Environment variables for flask app
ENV PYTHONDONTWRITEBYTECODE 1
ENV FLASK_APP "app.py"
ENV FLASK_ENV "development"
ENV FLASK_DEBUG False

# Exposing ports
EXPOSE 5000
ENV LC_ALL=C.UTF-8 
ENV  LANG=C.UTF-8

# Entry level command to execute
CMD flask run --host=0.0.0.0
