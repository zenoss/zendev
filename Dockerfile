FROM ubuntu
MAINTAINER Zenoss

RUN apt-get -y install python
RUN apt-get -y install wget
RUN wget -qO- https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
RUN pip install sphinx
WORKDIR /docs
