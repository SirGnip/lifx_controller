FROM python:3.11-alpine
RUN echo "Starting build of container"

RUN echo "Installing code"
RUN mkdir -p /myapp
COPY . /myapp/

# Doing Python installation AFTER source code so that any code change invalidates the image cache, meaning that
# the Python environment will be rebuilt.
RUN echo "Doing Python installation"
RUN pip install lifxlan
RUN pip list

# Startup command
CMD python3 -u /myapp/src/lifx_strip.py
