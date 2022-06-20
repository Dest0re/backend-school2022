PROJECT_NAME ?= megamarket
VERSION = $(shell python3 setup.py --version | tr '+' '-')
PROJECT_NAMESPACE ?= dest0re
REGISTRY_IMAGE ?= $(PROJECT_NAMESPACE)/$(PROJECT_NAME)

postgres:
	docker stop $(PROJECT_NAME)-postgres || true
	docker run -d --rm --name=$(PROJECT_NAME)-postgres \
		--env POSTGRES_USER=user \
		--env POSTGRES_PASSWORD=strngpsswrd \
		--env POSTGRES_DB=megamarket \
		--publish 5432:5432 postgres
