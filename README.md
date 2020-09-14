heranow


### building the intial docker image
execute `docker build -f dockerfiles/docker_conda -t conda_base:latest .`
The main app docker and helper containers can then be build with docker-compose `docker-compose build`.
To deploy bring the docker-compose stack up `docker-compose up -d`.

Two shell scripts have been provided to make the building simpler:

 - build.sh: invokes the docker build and docker-compose build steps.
 - deploy.sh: invokes the docker-compose up -d step
