FROM fedora:40
RUN dnf -y install unzip python3-devel gcc-c++ redhat-rpm-config wget curl cabextract \
    xorg-x11-font-utils fontconfig \
    pango cairo gdk-pixbuf2 libffi-devel && \
    dnf clean all

RUN mkdir /pp-server && python3 -m venv /pp-server
WORKDIR /pp-server
RUN bin/pip install --no-cache pp.server weasyprint hypercorn && \
    bin/pp-server-templates

VOLUME ["/pp-server/var"]
EXPOSE 8000
CMD ["bin/hypercorn", "pp.server.server:app", "--bind", "0.0.0.0:8000"]
