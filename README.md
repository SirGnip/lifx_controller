Controller for LIFX lightstrip zone lines.

Generates some basic effects.


# Installation

    py -3.11 -m venv venv
    source venv/Scripts/activate
    pip install -r requirements.txt
    python src/lifx_strip.py


# Packaging

    # Build docker image
    docker build -t lifx_controller . --progress=plain
    
    # Run with default startup command
    docker run lifx_controller

    # Run with custom startup command
    docker run lifx_controller python3 -u /myapp/src/lifx_strip.py --discover

    # Save to .tar file for upload to container manager
    docker save lifx_controller -o lifx_controller.tar
