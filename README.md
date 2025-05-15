
## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop on Mac and Windows)

### Starting the services

To start both services in the foreground (showing logs in the terminal):

```bash
docker compose up -d
```

### If container already exist

#### 1. Start existing containers (if they're stopped):

```bash
docker start company-lens-db company-lens-redis
```


#### 2. Restart running containers:

```bash
docker restart company-lens-db company-lens-redis
```

#### 3. Stop the containers:

```bash
docker stop company-lens-db company-lens-redis
```
