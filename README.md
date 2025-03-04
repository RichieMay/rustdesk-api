# rustdesk-api
simple implementation of api

# create account
curl -H 'Content-Type: application/json' -d '{"account":"xxx", "password": "xxxxx"}' http://localhost/admin/api/accounts

# update account
curl -H 'Content-Type: application/json' -X PUT -d '{"password": "xxxx", "nickname": "xxxx", "status": 0/1}' http://localhost/admin/api/accounts?account=xxx

# delete account
curl -H 'Content-Type: application/json' -X DELETE http://localhost/admin/api/accounts?account=xxx

# build docker
docker build -t richiemay/alpine-rustdesk-api:latest .  
docker tag richiemay/alpine-rustdesk-api:latest richiemay/alpine-rustdesk-api:1.3.8
