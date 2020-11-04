step1:
	docker-compose up

step2:
	venv/bin/python simulate_production.py

step3:
	venv/bin/python simulate_event_trigger.py

clear:
	docker-compose down -v

.PHONY: step1 step2 step3 clear