export USERID=$(id -u)
export GROUPID=$(id -g)
export LOCAL_IP=192.168.2.8
export PANO_WWW=/mnt/HD2/pano/www
export PANO_FTP=/mnt/HD2/pano/FTP
export PANO_DERIVED=/mnt/HD2/pano/derived
export PANO_LOG=/mnt/HD2/pano/logs

#
# pano-docker.json is bind-mounted read-only into the pano container, so it is
# not baked into the image. Fail early instead of letting Docker create a
# directory at the mount path.
#
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export PANO_CONFIG="${PANO_CONFIG:-${_SCRIPT_DIR}/pano/pano-docker.json}"
if [ ! -f "$PANO_CONFIG" ]; then
   echo "error: pano config not found: $PANO_CONFIG" >&2
   echo "set PANO_CONFIG to a valid pano-docker.json" >&2
   return 1 2>/dev/null # this will attempt to return
   exit 1 # exits if return didnt work
fi

#
# you first need to manually generate a passwd.digest file
# for mod_auth to work
cd "$_SCRIPT_DIR/lighttpd-docker"
DIGEST=passwd.digest
if [[ ! -f "$DIGEST" ]]; then
   echo you need to create "$DIGEST"
   echo see Dockerfile
   return 1 2>/dev/null # this will attempt to return
   exit 1 # exits if return didnt work
fi
cd "$_SCRIPT_DIR"

#
# Docker Compose command. Prefer the Compose v2 plugin binary directly: on
# chuyu the `docker compose` resolved by the Docker CLI is an old experimental
# compose-cli that drops build args, and v1 /usr/bin/docker-compose is EOL
# (and fails to recreate containers under Docker 28).
#
if [ -x /usr/libexec/docker/cli-plugins/docker-compose ]; then
    pano_compose() { /usr/libexec/docker/cli-plugins/docker-compose "$@"; }
elif docker compose version 2>/dev/null | grep -q 'v2'; then
    pano_compose() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
    pano_compose() { docker-compose "$@"; }
else
    echo "error: no Docker Compose (v2 plugin or v1) found" >&2
    return 1 2>/dev/null # this will attempt to return
    exit 1 # exits if return didnt work
fi
export -f pano_compose 2>/dev/null || true

export IMAGE_TAG=rel002
echo "Using IMAGE_TAG=$IMAGE_TAG"
echo "Using PANO_CONFIG=$PANO_CONFIG"
