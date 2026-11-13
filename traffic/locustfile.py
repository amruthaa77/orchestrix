"""
Locust load test traffic generator for stateless web service.
Usage:
    locust -f locustfile.py --host http://localhost:8080
    locust -f locustfile.py --headless -u 25 -r 5 --run-time 1m --host http://localhost:8080
"""

import logging
from locust import HttpUser, task, between, events

class StatelessWebServiceUser(HttpUser):
    # Simulated wait time between tasks per user: 100ms - 500ms
    wait_time = between(0.1, 0.5)

    @task(5)
    def index_page(self):
        """Simulate primary traffic to root endpoint."""
        with self.client.get("/", name="GET / (Index)", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def health_check(self):
        """Simulate periodic health check queries."""
        with self.client.get("/", name="GET / (HealthCheck)", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with code: {response.status_code}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("Starting traffic generator against target: %s", environment.host)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logging.info("Traffic generation test completed.")
