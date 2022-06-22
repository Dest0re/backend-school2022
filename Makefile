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


clean:
	rm -fr *.egg-info dist

devenv: clean
	rm -rf env
	python3.10 -m venv env

	env/bin/pip install -U pip

	env/bin/pip install -Ue '.[dev]'


sdist: clean
	python3.10 setup.py sdist


docker: sdist
	docker build --target=api -t $(PROJECT_NAME):$(VERSION) .


upload: docker
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):$(VERSION)
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):latest
	docker push $(REGISTRY_IMAGE):$(VERSION)
	docker push $(REGISTRY_IMAGE):latest


