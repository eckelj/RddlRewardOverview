# RDDL Reward Overview

Application to display Planetmint addresses, devices IPs, and balances of the different tokens.


## Execution
To run the application, run the following command:

```uvicorn main:app --reload```

The application will be available at http://localhost:8000.

Or run it as docker container with docker-compose:

```
docker-compose up -d      # start the application
docker-compose down       # stop the application
docker-compose down -v    # remove the volumes
```

## Migration

In order to migrate to the newer DB version execute

```poetry run alembic upgrade head```
