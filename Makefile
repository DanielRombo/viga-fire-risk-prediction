# Desenvolvimento
dev:
	docker compose up -d

dev-build:
	docker compose up --build -d

dev-logs:
	docker compose logs -f

dev-down:
	docker compose down

# Produção
prod:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

prod-build:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-down:
	docker compose -f docker-compose.prod.yml down

# Utilitários
ps:
	docker compose ps

clean:
	docker system prune -f