#!/usr/bin/python
import curses
import sys
import os
import stat
import re
from core.lib import password_lib

apache_conf_dir="/etc/httpd/conf.d"
apache_username="apache"
logrotate_conf_dir="/etc/logrotate.d"
pg_hba_conf = "/var/lib/pgsql/data/pg_hba.conf"
httpd_conf = "/etc/httpd/conf/httpd.conf"
selinux_config_file = "/etc/selinux/config"


def getDBConnection():
    from core import db_conf
    reload(db_conf)
    import pg
    con=pg.connect("IBSng",db_conf.DB_HOST,db_conf.DB_PORT,None,None,db_conf.DB_USERNAME,db_conf.DB_PASSWORD)
    return con

def doSqlFile(con,file_name):
    content=open(file_name).read(1024*100)
    con.query(content)

def callAndGetLines(command):
    fd=os.popen("%s 2>&1"%command,"r")
    lines=fd.readlines()
    fd.close()
    return lines


def replaceInFile(filename, search_exp, replace_exp):
    try:
        with open(filename, 'r') as file:
            content = file.read()

        # Replace the search expression with the replacement
        new_content = re.sub(search_exp, replace_exp, content)

        # Write the new content back to the file
        with open(filename, 'w') as file:
            file.write(new_content)

    except IOError:
        sys.exit(f"ERROR: Couldn't open or modify {filename}")



def addToFile(filename, content, position='first'):
    try:
        with open(filename, 'r+') as f:
            lines = f.readlines()
            if position == 'first':
                lines.insert(0, content + '\n')
            elif position == 'last':
                lines.append(content + '\n')
            else:
                raise ValueError("Invalid position. Use 'first' or 'last'.")
            f.seek(0)
            f.writelines(lines)
    except IOError:
        sys.exit(f"ERROR: Couldn't open or modify {filename}")



# checking root
if os.getuid()!=0:
    sys.exit("ERROR: Install should be runned as root")



# checking pg module
try:
     import pg
except ImportError:
        sys.exit("ERROR: Install should be runned as root\n \
                  1-Install postgresql-python rpm on distribution CDs(redhat/fedora on last CD)\n \
                  2-Download and install it from http://www.pygresql.org/")


# checking db connection
try:
    con=getDBConnection()
    con.close()
except:
    exctype, exc_value = sys.exc_info()[:2]
    if exc_value==None:
        exc_value=str(exctype)
    sys.exit("Error occured: ") + exc_value



# compile defs
ret=os.system("/usr/local/IBSng/core/defs_lib/defs2sql.py -i /usr/local/IBSng/core/defs_lib/defs_defaults.py /usr/local/IBSng/db/defs.sql 1>/dev/null 2>/dev/null")
if ret!=0:
    sys.exit("ERROR: File didn't compile successfully\nRecheck config file and try again")


# insert table
con=None
try:
    con=getDBConnection()
    doSqlFile(con,"/usr/local/IBSng/db/tables.sql")
    doSqlFile(con,"/usr/local/IBSng/db/functions.sql")
    doSqlFile(con,"/usr/local/IBSng/db/initial.sql")
    doSqlFile(con,"/usr/local/IBSng/db/defs.sql")

    con.close()
except:
    if con:
        con.close()
    exctype, exc_value = sys.exc_info()[:2]
    if exc_value==None:            
        exc_value=str(exctype)
    sys.exit("Error occured: ") + exc_value


# change system password
password="system"
passwd_obj=password_lib.Password(password)
try:
    con=getDBConnection()
    con.query("update admins set password='%s' where username='system'"%passwd_obj.getMd5Crypt())
    con.close()
except:
    if con:
        con.close()
    exctype, exc_value = sys.exc_info()[:2]
    if exc_value==None:            
        exc_value=str(exctype)
    sys.exit("Error occured: ") + exc_value

# create log dir
lines=callAndGetLines("mkdir /var/log/IBSng")
if lines:
    sys.exit("ERROR: Counldn't make log dir." + " ".join(lines).strip())
lines=callAndGetLines("chmod 770 /var/log/IBSng")
if lines:
    sys.exit("ERROR: Counldn't chown log dir." + " ".join(lines).strip())

# setup httpd
lines=callAndGetLines("cp -f /usr/local/IBSng/addons/apache/ibs.conf %s"%apache_conf_dir)
if lines:
     sys.exit("ERROR: Couldn't copy ibs.conf to " + apache_conf_dir + " ".join(lines).strip())
lines=callAndGetLines("chown root:%s /var/log/IBSng"%apache_username)
if lines:
    sys.exit("ERROR: Couldn't change owner of /var/log/IBSng to " + apache_username + " ".join(lines).strip())
lines=callAndGetLines("chown %s /usr/local/IBSng/interface/smarty/templates_c"%apache_username)
if lines:
    sys.exit("ERROR: Couldn't change owner of /usr/local/IBSng/interface/smarty/templates_c to " + apache_username + " ".join(lines).strip())


# copy log rotate
lines=callAndGetLines("cp -f /usr/local/IBSng/addons/logrotate/IBSng %s"%logrotate_conf_dir)
if lines:
    sys.exit("ERROR: Couldn't copy IBSng logrotate conf to " + logrotate_conf_dir + " ".join(lines).strip())

# create ibsng service
lines=callAndGetLines("cp -f /usr/local/IBSng/init.d/IBSng.init.redhat /etc/init.d/IBSng")
if lines:
    sys.exit("ERROR: Couldn't copy init file." + " ".join(lines).strip())

# trust ibsng pg pg_hba.conf
pg_hba_content = "local  IBSng   ibs            trust"
addToFile(pg_hba_conf, pg_hba_content)


# setup ibsng httpd.conf
httpd_conf_content = """ServerName 127.0.0.1
<Directory "/usr/local/IBSng/interface/IBSng">
    AllowOverride None
    Options None
    Require all granted
</Directory>"""
addToFile(httpd_conf, httpd_conf_content)

# disable selinux
ret = os.system("setenforce 0")
if ret != 0:
    sys.exit("ERROR: Failed to run 'setenforce 0'")
replaceInFile(selinux_config_file, r'^SELINUX=.*', 'SELINUX=disabled')


# end
print("\nInitial setup successful. You can log in with this information:")
print(f"Admin panel: http://ip/IBSng/admin")
print("Username: system")
print("Password: system\n")