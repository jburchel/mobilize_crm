import pytest
from mobilize_crm import create_app
from models import Base, engine, session_scope
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

def test_dashboard_access(client):
    response = client.get('/')
    assert response.status_code == 200

def test_task_creation(client, db):
    with session_scope() as session:
        response = client.post('/tasks/add_task', data={
            'title': 'Test Task',
            'description': 'Test Description',
            'status': 'Not Started',
            'priority': 'Medium'
        })
        assert response.status_code == 302  # Redirect after successful creation

def test_invalid_task_creation(client, db):
    response = client.post('/tasks/add_task', data={})
    assert response.status_code == 302
    # Should redirect back to tasks page with error