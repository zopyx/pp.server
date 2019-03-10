FROM fedora
RUN dnf -y install unzip python3-devel gcc-c++ redhat-rpm-config wget 
WORKDIR /
RUN wget -q https://download.speedata.de/dl/speedata-publisher-linux-amd64-3.6.1.zip; \
    unzip speedata-publisher-linux-amd64-3.6.1.zip

RUN echo
RUN mkdir /pp-server; python3 -m venv /pp-server
WORKDIR /pp-server
RUN echo
RUN bin/pip install --no-cache pp.server; \
    bin/pp-server-templates

RUN ln -sf /speedata-publisher/bin/sp /usr/bin/sp
VOLUME ["/pp-server/var"]
CMD bin/circusd circusd.ini
