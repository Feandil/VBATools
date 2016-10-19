FROM gitlab-registry.cern.ch/linuxsupport/cc7-base
#FROM centos:latest
MAINTAINER "CERN Computer Security Team <computer.security@cern.ch>"

# Install dependencies
RUN yum install -y java-1.8.0-openjdk-headless epel-release && \
    yum install -y python-pip && \
    pip install oletools && \
    yum -y erase python-pip && \
    yum -y autoremove && \
    yum clean all

# Copy source code
COPY . /malware

# Build parser
RUN yum -y install make wget java-1.8.0-openjdk-devel && \
    make -C /malware/parser && \
    yum -y erase make wget java-1.8.0-openjdk-devel && \
    yum -y autoremove && \
    yum clean all

# Start in the right folder
WORKDIR /malware
