from app import app

def test_health():
    assert app.test_client().get('/health').json == {'status':'ok'}
def test_home():
    r=app.test_client().get('/')
    assert r.status_code==200 and b'<title>' in r.data
def test_csrf():
    assert app.test_client().post('/api/run',json={}).status_code==403
def test_json_type():
    assert app.test_client().post('/api/run',json=[],headers={'X-Portfolio-Request':'1'}).status_code==400
