.PHONY: up down logs up-all down-all status

# Start infrastructure services (Keycloak, MinIO, Grafana, Prometheus, n8n)
up:
	docker-compose up -d keycloak minio grafana prometheus n8n

# Stop infrastructure services
down:
	docker-compose stop keycloak minio grafana prometheus n8n

# View logs of infrastructure services
logs:
	docker-compose logs -f keycloak minio grafana prometheus n8n

# Start ALL services (including backend, frontend, mongodb, redis)
up-all:
	docker-compose up -d

# Stop ALL services
down-all:
	docker-compose down

# Check status of running containers
status:
	docker-compose ps
