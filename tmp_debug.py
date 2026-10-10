import os
os.environ['DATABASE_URL'] = 'sqlite:///./tmp_debug.db'
os.environ['CERTIFICATES_DIR'] = './tmp_debug_certs'
os.environ['PROCESSING_MODE'] = 'sync'

from app.config import settings
print(settings.PROCESSING_MODE)
from app.database import create_db_and_tables, SessionLocal
from app.models import Job, Certificate
from app.schemas import JobCreateRequest
from app.services.job_service import create_job

create_db_and_tables()
payload = JobCreateRequest(event_name='Event', issuer_name='Issuer', recipients=[{'name':'Alice','email':'alice@example.com'},{'name':'Bob','email':'bob@example.com'}])
db = SessionLocal()
result = create_job(db, payload)
print('response', result)
print('jobs', db.query(Job).all())
print('certs', [(c.recipient_name, c.status.value, c.error_message, c.file_path) for c in db.query(Certificate).all()])
db.close()
