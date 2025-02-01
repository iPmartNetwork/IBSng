#!/bin/bash

# Check if the script is running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root."
  exit 1
fi

# Check if the OS is CentOS 7
if ! grep -q "CentOS Linux release 7" /etc/centos-release; then
  echo "IBSng can only be installed on CentOS 7."
  exit 1
fi

# Check if SELinux is enabled and prompt the user to disable it
if [ "$(getenforce)" != "Permissive" ]; then
  echo "SELinux is enabled. Please run the following commands to disable it and then rerun this script:"
  echo "setenforce 0"
  echo "sed -i 's/enforcing/disabled/g' /etc/selinux/config"
  exit 1
fi

# Add nameserver 8.8.8.8 to the beginning of /etc/resolv.conf if it doesn't already exist
if ! grep -q "nameserver 8.8.8.8" /etc/resolv.conf; then
  sed -i '1inameserver 8.8.8.8' /etc/resolv.conf
fi

# Fix CentOS 7 repository
bash <(curl -s https://raw.githubusercontent.com/imafaz/awesome-scripts/main/fix-centos7-repository/main.sh)

# Update system packages
echo "Updating system packages..."
yum update -y

# Install necessary packages
echo "Installing necessary packages: httpd, php, postgresql, postgresql-server, postgresql-python, git, perl, firewalld..."
yum install httpd php postgresql postgresql-server postgresql-python git perl firewalld -y

# Initialize PostgreSQL database
echo "Initializing PostgreSQL database..."
postgresql-setup initdb
systemctl start postgresql

# Create PostgreSQL database and user
echo "Creating PostgreSQL database 'IBSng' and user 'ibs'..."
su postgres -c "createdb IBSng"
su postgres -c "createuser ibs"
su postgres -c "createlang plpgsql IBSng"

# Clone IBSng repository
echo "Cloning IBSng repository from GitHub..."
git clone https://github.com/imafaz/IBSng.git /usr/local/IBSng

echo "Copying backup and restore scripts to /usr/bin..."
cp /usr/local/IBSng/backup_ibs /usr/bin/
cp /usr/local/IBSng/restore_ibs /usr/bin/

# Set permissions for the scripts
echo "Setting permissions for backup and restore scripts..."
chmod 777 /usr/bin/backup_ibs
chmod 777 /usr/bin/restore_ibs

echo "Backup and restore scripts have been installed successfully."


# Enable and start firewalld
echo "Enabling and starting firewalld..."
systemctl enable firewalld
systemctl start firewalld

# Allow necessary ports in firewalld
echo "Allowing necessary ports in firewalld: 80, 1812, 1813..."
firewall-cmd --add-port=80/tcp --permanent
firewall-cmd --add-port=1812/udp --permanent
firewall-cmd --add-port=1813/udp --permanent
firewall-cmd --reload

# Run initialization script
echo "Running initialization script..."
/usr/local/IBSng/scripts/init.py

echo "Installation and configuration completed successfully."