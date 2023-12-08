test: test-deps
	coverage run --concurrency=eventlet --source nameko_sqlalchemy --branch -m \
		pytest test \
			--test-db-url="mysql+pymysql://test_user:password@$(shell docker port nameko_sqlalchemy_test_mysql 3306 | grep -v '::')/nameko_sqlalchemy_test" \
			--toxiproxy-api-url=$(shell docker port nameko_sqlalchemy_test_toxiproxy 8474 | grep -v '::') \
			--toxiproxy-db-url="mysql+pymysql://test_user:password@$(shell docker port nameko_sqlalchemy_test_toxiproxy 3307 | grep -v '::')/nameko_sqlalchemy_test"
	coverage report --show-missing --fail-under=100

test-deps: container-cleanup mysql-setup toxiproxy-setup

toxiproxy-container:
	docker run --rm -d -p 8474 -p 3307 --name=nameko_sqlalchemy_test_toxiproxy shopify/toxiproxy

mysql-container:
	docker run --rm -d -p 3306 -e MYSQL_ROOT_PASSWORD=password -eMYSQL_USER=test_user -e MYSQL_PASSWORD=password -eMYSQL_DATABASE=nameko_sqlalchemy_test --name=nameko_sqlalchemy_test_mysql mysql:5.6

toxiproxy-setup: toxiproxy-container
	@echo Setting up toxiproxy to mysql
	docker exec -it nameko_sqlalchemy_test_toxiproxy /go/bin/toxiproxy-cli \
		create nameko_sqlalchemy_test_mysql \
		--listen=0.0.0.0:3307 \
		--upstream=`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nameko_sqlalchemy_test_mysql`:3306

mysql-setup: mysql-container
	@echo Waiting for mysql to start...
	docker exec nameko_sqlalchemy_test_mysql \
		/bin/sh -c 'while ! mysqladmin ping -h127.0.0.1 -utest_user -ppassword --silent; do sleep 1; done'

container-cleanup:
	@echo Removing docker containers...
	docker rm -f nameko_sqlalchemy_test_mysql nameko_sqlalchemy_test_toxiproxy || true
