from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import tempfile

client=TestClient(app)

def test_pages_and_health():
    assert client.get('/').status_code==200
    sim=client.get('/simulator')
    assert sim.status_code==200 and 'Kendi trafik senaryonu oluştur' in sim.text
    r=client.get('/api/health')
    assert r.status_code==200 and 'sumo' in r.json()

def test_validation():
    body={'demand':2600,'weather':'dry','seed':314,'duration_minutes':30,'policies':['static']}
    r=client.post('/api/simulations',json=body)
    assert r.status_code==422
    body['policies']=['static','rule'];body['demand']=99999
    assert client.post('/api/simulations',json=body).status_code==422

def test_no_sumo_returns_clear_error():
    with patch('shutil.which',return_value=None):
        response=client.post('/api/simulations',json={
            'demand':2600,'weather':'dry','seed':314,'duration_minutes':30,'policies':['static','rule']})
        assert response.status_code==503 and 'SUMO' in response.text
