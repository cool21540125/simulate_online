s1:
	docker-compose up

s2:
	venv/bin/python simulate_production.py

s3:
	venv/bin/python simulate_event_trigger.py

clear:
	docker-compose down -v
	docker rmi demo_production:1.0

.PHONY: s1 s2 s3 clear