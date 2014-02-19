FROM ubuntu
MAINTAINER Zenoss

RUN apt-get -y install python python-pip
RUN pip install sphinx
WORKDIR /docs
