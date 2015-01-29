# Produce & Publish Server (pypi.python.org/pypi/pp.server)
# with pre-installed 
# - PDFreactor 7 eval version
# - PrinceXML 9 eval version
# - WKHTMLTOPDF 
# - Calibre
#
# Usage:
# docker run -p 8888:6543 zopyx/pp.server

FROM dockerfile/java:oracle-java7

MAINTAINER Andreas Jung <info@zopyx.com>

RUN apt-get update
RUN apt-get install -y \
    curl \
    build-essential \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libbz2-dev \
    zlib1g-dev \
    python3-setuptools \
    python3-dev \
    libjpeg62-dev \
    libreadline-gplv2-dev \
    python-imaging \
    python-dev \
    libxml2-dev \
    libxslt1-dev \
    wget \
    fontconfig  \
    libfontconfig1  \
    libxrender1  \
    libgif4 \
    xfonts-base \
    xfonts-75dpi


RUN wget -nv -O p.zip http://download.speedata.de/publisher/stable/linux/speedata-publisher-linux-amd64-2.2.0.zip
RUN unzip p.zip
RUN rm p.zip

# PDFREACTOR
RUN wget -nv -O p.tgz "http://www.pdfreactor.com/download/get/?product=pdfreactor&type=unix&jre=false"
RUN tar xfvz p.tgz
RUN rm p.tgz 

# WKHTMLTOPDF
RUN wget -nv  -O wk.deb "http://garr.dl.sourceforge.net/project/wkhtmltopdf/0.12.2.1/wkhtmltox-0.12.2.1_linux-trusty-amd64.deb"
RUN dpkg --install wk.deb
RUN rm wk.deb

# PRINCEXML
RUN wget -nv -O prince.deb http://www.princexml.com/download/prince_9.0-5_ubuntu14.04_amd64.deb
RUN dpkg --install prince.deb
RUN rm prince.deb

# CALIBRE
RUN wget -nv -O- https://raw.githubusercontent.com/kovidgoyal/calibre/master/setup/linux-installer.py | sudo python -c "import sys; main=lambda x:sys.stderr.write('Download failed\n'); exec(sys.stdin.read()); main('/opt')"

RUN useradd ppserver

# INSTALL PRODUCE & PUBLISH SERVER
RUN easy_install-3.4 virtualenv
RUN virtualenv .
RUN bin/python --version
RUN bin/pip install pp.server
ADD development.ini  /tmp/development.ini
RUN mkdir /data/var
RUN chown -R ppserver *

EXPOSE 6543
RUN ls -la /data
WORKDIR .
USER ppserver
CMD PATH=$PATH:$PWD/PDFreactor/bin:$PWD/speedata-publisher/bin; echo $PATH; bin/python --version; bin/pserve /tmp/development.ini
