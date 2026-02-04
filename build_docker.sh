set -e  # immediate fail on any non-true return value
set -u  # fail when accessing variable that doesn't exist

hdr() {
    echo
    echo ========== $1 ==========
}

hdr "Build docker image"
docker build -t lifx_controller . --progress=plain

hdr "Save docker image as tar file"
docker save lifx_controller -o lifx_controller.tar

hdr "Confirm build results"
docker images
echo
ls -l lifx_controller.tar

hdr "Testing"
echo "docker run lifx_controller python3 -u /myapp/src/lifx_strip.py"
