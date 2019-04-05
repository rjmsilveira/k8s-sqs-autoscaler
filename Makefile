ORG=rjmsilveira
PROJ=openshift-sqs-autoscale
VERSION=1.0.6

.PHONY=release
release:
	docker build -t ${ORG}/${PROJ} -f Dockerfile .
	git tag $(VERSION)
	git push origin $(VERSION)
	docker login
	docker tag ${ORG}/${PROJ}:latest ${ORG}/${PROJ}:${VERSION}
	docker push ${ORG}/${PROJ}:${VERSION}
