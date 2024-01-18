FROM fedora
RUN dnf -y install unzip python3-devel gcc-c++ redhat-rpm-config wget curl cabextract xorg-x11-font-utils fontconfig
RUN dnf install -y https://downloads.sourceforge.net/project/mscorefonts2/rpms/msttcore-fonts-installer-2.6-1.noarch.rpm

RUN mkdir /pp-server; python3 -m venv /pp-server
WORKDIR /pp-server
RUN echo
RUN bin/pip install --no-cache pp.server weasyprint circus gunicorn uvicorn; \
    bin/pp-server-templates

RUN ln -sf /speedata-publisher/bin/sp /usr/bin/sp
RUN ln -sf $PWD/bin/weasyprint /usr/bin/weasyprint

VOLUME ["/pp-server/var"]
CMD bin/circusd circusd.ini
