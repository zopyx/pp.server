FROM fedora:40
RUN dnf -y install unzip python3-devel gcc-c++ redhat-rpm-config wget curl cabextract \
    xorg-x11-font-utils fontconfig && \
    dnf clean all

# Speedata Publisher
WORKDIR /
RUN wget -q https://download.speedata.de/dl/speedata-publisher-linux-amd64-4.0.4.zip && \
    unzip speedata-publisher-linux-amd64-4.0.4.zip && \
    rm speedata-publisher-linux-amd64-4.0.4.zip

# PrinceXML
RUN wget -q https://www.princexml.com/download/prince-16.2-1.fc40.x86_64.rpm && \
    dnf install -y prince-16.2-1.fc40.x86_64.rpm && \
    rm prince-16.2-1.fc40.x86_64.rpm

RUN mkdir /pp-server && python3 -m venv /pp-server
WORKDIR /pp-server
RUN bin/pip install --no-cache pp.server weasyprint hypercorn && \
    bin/pp-server-templates

RUN ln -sf /speedata-publisher/bin/sp /usr/bin/sp
RUN ln -sf "$PWD/bin/weasyprint" /usr/bin/weasyprint

VOLUME ["/pp-server/var"]
EXPOSE 8000
CMD ["bin/hypercorn", "pp.server.server:app", "--bind", "0.0.0.0:8000"]
