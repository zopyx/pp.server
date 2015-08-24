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
RUN yum install -y wget tar  unzip python3-virtualenv sudo java-1.8.0-openjdk-headless.x86_64
RUN yum update -y
Run yum upgrade -y

RUN mkdir -p /opt/pp
RUN cd /opt/pp
WORKDIR /opt/pp

RUN wget -nv -O p.tgz https://github.com/dita-ot/dita-ot/releases/download/2.1/dita-ot-2.1.0.tar.gz 
RUN tar xfvz p.tgz 
RUN rm p.tgz

RUN wget -nv -O p.zip http://www.xmlmind.com/ditac/_download/ditac-2_5_6.zip 
RUN unzip p.zip
RUN rm p.zip

RUN wget -nv -O p.zip http://download.speedata.de/publisher/stable/linux/speedata-publisher-linux-amd64-2.2.0.zip
RUN unzip p.zip
RUN rm p.zip

RUN wget -nv -O p.tgz "http://www.pdfreactor.com/download/get/?product=pdfreactor&type=unix-x64&jre=true" 
RUN tar xfz p.tgz
RUN rm p.tgz 

# WKHTMLTOPDF
RUN echo
RUN wget -nv  -O wk.rpm https://kojipkgs.fedoraproject.org//packages/wkhtmltopdf/0.12.2.1/1.fc21/x86_64/wkhtmltopdf-0.12.2.1-1.fc21.x86_64.rpm 
RUN yum install -y wk.rpm 
RUn rm wk.rpm

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
CMD PATH=$PATH:$PWD/dita-ot-2.1.0/bin:$PWD/ditac-2_5_6/bin:$PWD/prince/bin:$PWD/PDFreactor/bin:$PWD/speedata-publisher/bin; echo $PATH; bin/python --version; bin/pserve /tmp/development.ini 
