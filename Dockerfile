FROM ubuntu
MAINTAINER Zenoss

RUN apt-get update && apt-get -y install python wget make
RUN wget --no-check-certificate -qO- https://bootstrap.pypa.io/get-pip.py | python
RUN pip install sphinx
WORKDIR /docs
