# Docker cheatsheet (from Project Panopticon Log)

Reference notes copied from the **text** of `~/pano-log.pdf`. Fundamentals only; not
pano-specific.

## Concepts

- **image** = a static file; the customization layers.
- **container** = the runtime executable (instantiated from an image).

## Common commands

```
docker run hello-world                    # download hello-world image and run it
docker run -it -d --name debiancontainer mydebian
    -i  = interactive (connect to stdin)
    -t  = allocate a tty
    -d  = detach
    --name = container name
    -p hostport:containerport
    -v hostdir:containervolume

docker exec debiancontainer ls            # execute "ls" in debiancontainer
docker exec -it debiancontainer -u root bash

docker start|stop angry_poincare          # start/stop container "angry_poincare"

docker rmi hello-world                    # delete image (--force to force)
docker rmi $(docker images -a -q)         # delete all images
docker images -a                          # list images

docker build -t myimage .                 # build image "myimage" from ./Dockerfile
docker ps -a                              # list all containers (running+stopped)

docker system prune                       # delete dangling resources (-a = also stopped)
docker rm mycontainer                     # delete a stopped container
docker container prune                    # delete all stopped containers
docker image prune                        # delete dangling images (-a = all images)

docker cp src/. mycontainer:/target       # copy host src dir into container
docker cp mycontainer:/src/. target       # copy from container (ID from docker ps)

docker commit container_name new_image    # snapshot a modified container to an image
```

## Basics walkthrough (from the doc)

```
docker search ubuntu
docker run hello-world
docker create ubuntu:18.04
docker run -i -t ubuntu:18.04 /bin/bash
root@...:/# cat /proc/version
root@...:/# cat /etc/os-release

docker build -t mydebian .     # build image "mydebian" from Dockerfile in "."
docker run -d -p 8000:80 httpd # -d=detach; -p maps host 8000 -> container 80
rm hello-world                 # (as written) remove image
```

## Compose notes (2021-2023)

- `docker-compose` replaced `supervisord` for pano; come from `docker-compose.yml`.
- Pinning images: when `docker compose build` runs, it uses the `image:` name:tag
  from the service definition; if that tag already exists it moves the tag to the new
  build.
- Pull instead of build: set `image: robyu/pano-docker_<svc>:rel001` and run
  `docker compose pull <svc>`.
- Docker Hub: `docker login`, then `docker tag <hash> robyu/pano-docker_<svc>:rel001`,
  then `docker push robyu/pano-docker_<svc>:rel001`.
- Alpine package pinning breaks rebuilds over time (old packages are removed from the
  repo) — update the pinned versions when a build fails.
