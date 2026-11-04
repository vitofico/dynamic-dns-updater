.PHONY: lint test build smoke
IMAGE ?= ghcr.io/vitofico/dynamic-dns-updater/updater
TAG ?= dev
lint:
	shellcheck update_dns.sh tests/smoke-image.sh
	sh -n update_dns.sh

test:
	python3 -m unittest discover -s tests -v

build:
	docker build -t $(IMAGE):$(TAG) .

smoke:
	tests/smoke-image.sh $(IMAGE):$(TAG)
