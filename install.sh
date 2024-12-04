#!/bin/bash

echo "disabling seLINUX"
setenforce 0
sed -i 's/enforcing/disabled/g' /etc/selinux/config


echo "add nameserver to 8.8.8.8..."
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

echo "Cleaning Yum cache..."
yum clean all

echo "Removing existing Yum repositories..."
rm -f /etc/yum.repos.d/*

echo "Downloading CentOS Base repository file..."
curl -o /etc/yum.repos.d/CentOS-Base.repo https://el7.repo.almalinux.org/centos/CentOS-Base.repo

echo "Updating system packages..."
yum update -y

echo "Installing necessary packages: httpd, php, postgresql, postgresql-server, postgresql-python, git, perl, firewalld..."
yum install httpd php postgresql postgresql-server postgresql-python git perl firewalld -y

echo "Initializing PostgreSQL database..."
postgresql-setup initdb
systemctl start postgresql

echo "Creating PostgreSQL database 'IBSng' and user 'ibs'..."
su postgres -c "createdb IBSng"
su postgres -c "createuser ibs"
su postgres -c "createlang plpgsql IBSng"

echo "Cloning IBSng repository from GitHub..."
git clone https://github.com/imafaz/IBSng.git /usr/local/IBSng
echo "Enabling and starting the firewall service..."
systemctl enable firewalld
systemctl start firewalld

echo "Allowing necessary ports in the firewall: 80, 1812, 1813..."
firewall-cmd --add-port=80/tcp --permanent
firewall-cmd --add-port=1812/udp --permanent
firewall-cmd --add-port=1813/udp --permanent
firewall-cmd --reload

echo "Running initialization script..."
/./usr/local/IBSng/scripts/init.py



echo "Installation and configuration completed successfully."

