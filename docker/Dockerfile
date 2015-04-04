# Produce & Publish Server (pypi.python.org/pypi/pp.server)
# with pre-installed 
# - PDFreactor 7 eval version
# - PrinceXML 9 eval version
# - Calibre
#
# Usage:
# docker run -p 8888:6543 zopyx/pp.server

FROM fedora:latest
MAINTAINER Andreas Jung <info@zopyx.com>
RUN yum install -y wget tar  unzip python3-virtualenv sudo
RUN yum update -y
Run yum upgrade -y

RUN mkdir -p /opt/pp
RUN cd /opt/pp
WORKDIR /opt/pp

RUN wget -nv -O p.zip http://download.speedata.de/publisher/stable/linux/speedata-publisher-linux-amd64-2.2.0.zip
RUN unzip p.zip
RUN rm p.zip

RUN wget -nv -O p.tgz "http://www.pdfreactor.com/download/get/?product=pdfreactor&type=unix-x64&jre=true" 
RUN tar xfz p.tgz
RUN rm p.tgz 

# WKHTMLTOPDF
#RUN wget -nv  -O wk.deb "http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.2.1/wkhtmltox-0.12.2.1_linux-wheezy-amd64.deb?r=http%3A%2F%2Fwkhtmltopdf.org%2Fdownloads.html&ts=1427822456&use_mirror=garr"
#RUN dpkg --install wk.deb
#RUN rm wk.deb

# PRINCEXML

RUN wget -nv -O prince.tgz http://www.princexml.com/download/prince-9.0r5-linux-amd64-static.tar.gz 
RUN mkdir prince
RUN tar xfz prince.tgz -C prince --strip-components=3 
RUN rm prince.tgz

# CALIBRE
RUN wget -nv -O- https://raw.githubusercontent.com/kovidgoyal/calibre/master/setup/linux-installer.py | sudo python -c "import sys; main=lambda x:sys.stderr.write('Download failed\n'); exec(sys.stdin.read()); main('/opt')"

RUN useradd ppserver
RUN pyvenv .  
RUN bin/python --version
RUN bin/pip install pp.server
ADD development.ini  /tmp/development.ini

RUN chown -R ppserver /opt/pp 
EXPOSE 6543
RUN ls -la /opt/pp
run pwd
USER ppserver
CMD PATH=$PATH:$PWD/prince/bin:$PWD/PDFreactor/bin:$PWD/speedata-publisher/bin; echo $PATH; bin/python --version; bin/pserve /tmp/development.ini
