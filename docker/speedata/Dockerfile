FROM fedora:40
RUN dnf -y install unzip python3-devel gcc-c++ redhat-rpm-config wget && \
    dnf clean all

# Speedata Publisher
WORKDIR /
RUN wget -q https://download.speedata.de/dl/speedata-publisher-linux-amd64-4.0.4.zip && \
    unzip speedata-publisher-linux-amd64-4.0.4.zip && \
    rm speedata-publisher-linux-amd64-4.0.4.zip

RUN mkdir /pp-server && python3 -m venv /pp-server
WORKDIR /pp-server
RUN bin/pip install --no-cache pp.server hypercorn && \
    bin/pp-server-templates

RUN ln -sf /speedata-publisher/bin/sp /usr/bin/sp

VOLUME ["/pp-server/var"]
EXPOSE 8000
CMD ["bin/hypercorn", "pp.server.server:app", "--bind", "0.0.0.0:8000"]
