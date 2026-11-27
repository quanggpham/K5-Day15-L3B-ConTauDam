import json
import httpx
import pytest
from fastapi.testclient import TestClient
from codebase.backend.main import app
from codebase.backend.security import auth
from codebase.backend.security.auth import require_coach


def _lesson(lid, prev, rate, delta, responses=20, incorrect=4):
    kcs = [{'kc_code': 'K1', 'status': 'ok', 'graded_count': responses, 'incorrect_rate': rate},
           {'kc_code': 'K2', 'status': 'insufficient_sample', 'graded_count': 3, 'incorrect_rate': 1.0}]
    return {'lesson_id': lid, 'status': 'ok',
            'sample': {'responses': responses, 'learners': 15, 'ungraded': 2, 'incorrect': incorrect},
            'incorrect_rate': rate, 'previous_lesson_id': prev, 'delta_vs_previous_pp': delta,
            'kcs': kcs, 'priority': [{**kcs[0], 'rank': 1}]}


SNAP = {'version': 2, 'generated_at': 't', 'min_sample': 10,
        'catalog': [{'lesson_id': 'L1', 'status': 'ok', 'kc_count': 2}, {'lesson_id': 'L2', 'status': 'ok', 'kc_count': 2}],
        'lessons': {'L1': _lesson('L1', None, 0.5, None, incorrect=10), 'L2': _lesson('L2', 'L1', 0.2, -30.0)}}


@pytest.fixture
def snap_path(tmp_path, monkeypatch):
    path = tmp_path / 'agg.v2.json'
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


@pytest.fixture
def client():
    app.dependency_overrides[require_coach] = lambda: {'id': 'u', 'email': 'c@example.com'}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_requires_auth_401():
    assert TestClient(app).get('/api/dashboard').status_code == 401


def test_not_allowlisted_403_and_expired_401(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public')
    state = {'authenticated': True}
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': 'u'}) if state['authenticated'] else httpx.Response(401)
        return httpx.Response(200, json=False)
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    c, h = TestClient(app), {'Authorization': 'Bearer x'}
    assert c.get('/api/dashboard', headers=h).status_code == 403
    state['authenticated'] = False
    assert c.get('/api/dashboard', headers=h).status_code == 401


def test_selected_lesson_metrics(client, snap_path):
    snap_path.write_text(json.dumps(SNAP), encoding='utf-8')
    body = client.get('/api/dashboard', params={'lesson_id': 'L1'}).json()
    assert body['status'] == 'ok' and body['selected_lesson_id'] == 'L1'
    assert [c['lesson_id'] for c in body['catalog']] == ['L1', 'L2']
    lesson = body['lesson']
    assert lesson['incorrect_rate'] == 0.5 and lesson['first_attempt_accuracy'] == 0.5
    assert lesson['sample']['responses'] == 20 and lesson['sample']['learners'] == 15
    assert lesson['sufficient_kc_count'] == 1 and lesson['kc_count'] == 2
    assert lesson['distribution'] == {'correct': 10, 'incorrect': 10, 'ungraded': 2}
    assert lesson['delta_vs_previous_pp'] is None and lesson['priority'][0]['kc_code'] == 'K1'
    assert 'lượt' in body['units']['responses'] and 'người' in body['units']['learners']


def test_default_is_latest_lesson(client, snap_path):
    snap_path.write_text(json.dumps(SNAP), encoding='utf-8')
    body = client.get('/api/dashboard').json()
    assert body['selected_lesson_id'] == 'L2'
    assert body['lesson']['delta_vs_previous_pp'] == -30.0 and body['lesson']['previous_lesson_id'] == 'L1'


def test_unknown_lesson_404(client, snap_path):
    snap_path.write_text(json.dumps(SNAP), encoding='utf-8')
    assert client.get('/api/dashboard', params={'lesson_id': 'NOPE'}).status_code == 404


def test_missing_snapshot_is_no_data(client, snap_path):
    assert client.get('/api/dashboard').json() == {'status': 'no_data'}


def test_empty_catalog_is_no_data(client, snap_path):
    snap_path.write_text(json.dumps({'version': 2, 'catalog': [], 'lessons': {}}), encoding='utf-8')
    assert client.get('/api/dashboard').json() == {'status': 'no_data'}


def test_no_graded_lesson_keeps_null_not_zero(client, snap_path):
    snap = {'version': 2, 'catalog': [{'lesson_id': 'L1'}], 'lessons': {'L1': {
        'lesson_id': 'L1', 'status': 'no_graded', 'sample': {'responses': 0, 'learners': 0, 'ungraded': 2, 'incorrect': 0},
        'incorrect_rate': None, 'delta_vs_previous_pp': None, 'kcs': [], 'priority': []}}}
    snap_path.write_text(json.dumps(snap), encoding='utf-8')
    lesson = client.get('/api/dashboard').json()['lesson']
    assert lesson['incorrect_rate'] is None and lesson['first_attempt_accuracy'] is None


def test_corrupt_snapshot_503(client, snap_path):
    snap_path.write_text('{bad', encoding='utf-8')
    assert client.get('/api/dashboard').status_code == 503
