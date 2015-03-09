#!/bin/bash -eux

export GOPATH=/opt/go

mkdir -p /opt/go/{bin,pkg,src}
export PATH="$PATH:/usr/local/go/bin"

# golint for style checking
go get github.com/golang/lint/golint
ln -s /opt/go/bin/golint /usr/local/bin/golint

# godef to find out where stuff is defined
go get -v code.google.com/p/rog-go/exp/cmd/godef
go install -v code.google.com/p/rog-go/exp/cmd/godef
ln -s /opt/go/bin/godef /usr/local/bin/godef

# gocode for less typing
go get -u github.com/nsf/gocode
ln -s /opt/go/bin/gocode /usr/local/bin/gocode

# goimports so you can think about important stuff
go get code.google.com/p/go.tools/cmd/goimports
ln -s /opt/go/bin/goimports /usr/local/bin/goimports
