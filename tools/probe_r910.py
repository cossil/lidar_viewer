from fastapi.testclient import TestClient
from lidar_analysis.api.app import create_app

c = TestClient((create_app()
sensor = {
    "sensor_id": "bad-sensor", "sensor_type": "mechanical_spinning",
    "manufacturer": "X", "model": "Y", "version": "1.0.0",
    "wavelength": {"value": 905, "unit": "nm", "origin": "SOURCE", "status": "known"},
    "range": {"maximum": {"value": None, "unit": "m", "origin": "SOURCE", "status": "unknown"}},
    "beam": {"horizontal_divergence": {"value": None, "unit": "rad", "origin": "SOURCE", "status": "unknown"}},
}
print("sensor POST status:", c.post("/api/sensors", json=sensor).status_code)
sc = {
    "scenario_id": "s1", "sensor_id": "bad-sensor",
    "sensor_pose": {"position": ([0,  ‎0, 1.5],), "orientation": {"yaw": 0, "pitch":  ‎0,,"roll": 	0}},
    "target": {"type": "cylinder", "position": ([30,0,0.5],), "orientation": ([0,0,1],), "diameter":  ‎0.10,,reflectivity"": 	0.3}},