from locust import HttpUser, task, between

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MzQ3NTEwMywianRpIjoiZmQ2OGFiM2UtYTAwYi00YTNjLWJhODAtMzkzN2Y1YmI3MGU1IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjIiLCJuYmYiOjE3NjM0NzUxMDMsImNzcmYiOiIwY2YwOTc0Yi1lMjNlLTQ2YTQtYTEyNS1jMDVmN2U0ZDVkMWYiLCJleHAiOjE3NjQwNzk5MDMsInJvbGUiOiJmYXJtZXIifQ.NvfT-S4dZlUdbZcCTkB8OXG76xr6oyQIevN2_BpOQmY"

class MASUser(HttpUser):
    host = "http://127.0.0.1:5000"   
    wait_time = between(1, 2)

    @task
    def test_fertilizer_plan(self):
        self.client.get("/api/farm/fertilizer-plan", headers={
            "Authorization": f"Bearer {TOKEN}"
        })

    @task
    def test_water_plan(self):
        self.client.get("/api/farm/water-plan", headers={
            "Authorization": f"Bearer {TOKEN}"
        })

    @task
    def test_treatment_plan(self):
        self.client.get("/api/treatment/treatment-plan", headers={
            "Authorization": f"Bearer {TOKEN}"
        })
        
    @task
    def test_treatment_plan(self):
        self.client.get("/api/farm/ask", headers={
            "Authorization": f"Bearer {TOKEN}"
        })
