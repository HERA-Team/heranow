heranow

This repository defines the dashboard website used for HERA.
It is built on django and Dash to create multiple interactive apps for users to access real time data from the HERA correlator.

[django environ](https://github.com/joke2k/django-environ) is used to handle and store sensitive environment secrets. This relies on a file `.env` on machines to define secrets used in the django settings file.

### building the initial docker image
execute `docker build -f dockerfiles/docker_conda -t conda_base:latest .`
The main app docker and helper containers can then be build with docker-compose `docker-compose build`.
To deploy bring the docker-compose stack up `docker-compose up -d`.

Two shell scripts have been provided to make the building simpler:

 - `build.sh`: invokes the docker build and docker-compose build steps.
 - `deploy.sh`: invokes the docker-compose up -d step

### Stopping the docker images
Docker images can be stopped by executing `docker-compose down` or restarted with `docker-compose restart`.

### Updating M&C Schema
When the M&C schema changes on site, a forced rebuild of the base docker
conatiner is necessary. This can be accomplished with the command
`docker build -f dockerfiles/docker_conda -t conda_base:latest . --no-cache`

After rebuilding the base docker image, `build.sh` and `deploy.sh` as usual.

### Initialize the database
Database initialization can happen at the time of deployment by setting the key `INITIALIZE` in the `.env` on the deploying machine. This does take an extended period of time.


### Dash applications
We use multiple dash apps to create the index landing page for heranow.
The custom app injector can be found in [here](dashboard/templatetags/plotly_custom.py).
This custom injector allows us to filter the apps based on their name and have more than one on a page.
