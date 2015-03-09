curl -s https://storage.googleapis.com/golang/go1.4.2.linux-amd64.tar.gz | tar -xzC /usr/local

# Set GOROOT and PATH appropriately
cat <<EOF | bash -c "cat > /etc/profile.d/golang.sh"
export GOROOT=/usr/local/go
export PATH=\$GOROOT/bin:\$PATH
EOF
