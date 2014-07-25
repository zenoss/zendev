FROM ubuntu
MAINTAINER Zenoss

RUN apt-get update && apt-get -y install python wget make
RUN wget --no-check-certificate -qO- https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
RUN pip install sphinx
WORKDIR /docs
