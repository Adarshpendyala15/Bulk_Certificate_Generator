const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { randomUUID } = require('crypto');
const PDFDocument = require('pdfkit');
const Database = require('better-sqlite3');
const AdmZip = require('adm-zip');

const app = express();
const port = process.env.PORT || 8000;
const rootDir = __dirname;
const certDir = path.join(rootDir, 'node_certificates');
const dbPath = path.join(rootDir, 'node-certificates.db');

fs.mkdirSync(certDir, { recursive: true });

if (fs.existsSync(dbPath)) {
  const probe = new Database(dbPath);
  const jobColumns = probe.prepare('PRAGMA table_info(jobs)').all();
  const hasJobIdColumn = jobColumns.some((column) => column.name === 'job_id');
  probe.close();

  if (!hasJobIdColumn) {
    fs.rmSync(dbPath, { force: true });
  }
}

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    issuer_name TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    status TEXT NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    succeeded_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS certificates (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    course_or_role TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    file_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
  );
`);

app.use(cors());
app.use(express.json({ limit: '10mb' }));

function normalizeRecipient(recipient = {}) {
  return {
    name: String(recipient.name || '').trim(),
    email: String(recipient.email || '').trim(),
    course_or_role: recipient.course_or_role ? String(recipient.course_or_role).trim() : null,
  };
}

function sanitizeDate(dateValue) {
  if (!dateValue) return new Date().toISOString().slice(0, 10);
  const asDate = new Date(dateValue);
  if (Number.isNaN(asDate.getTime())) {
    return new Date().toISOString().slice(0, 10);
  }
  return asDate.toISOString().slice(0, 10);
}

function formatJob(jobRow, certRows = []) {
  const totalCount = Number(jobRow.total_count || 0);
  const succeededCount = Number(jobRow.succeeded_count || 0);
  const failedCount = Number(jobRow.failed_count || 0);
  const pendingCount = Math.max(totalCount - succeededCount - failedCount, 0);
  const progress = totalCount ? ((succeededCount + failedCount) / totalCount) * 100 : 0;

  return {
    job_id: jobRow.job_id,
    event_name: jobRow.event_name,
    issuer_name: jobRow.issuer_name,
    issue_date: jobRow.issue_date,
    status: jobRow.status,
    total_count: totalCount,
    succeeded_count: succeededCount,
    failed_count: failedCount,
    pending_count: pendingCount,
    progress_percentage: Number(progress.toFixed(1)),
    created_at: jobRow.created_at,
    updated_at: jobRow.updated_at,
    certificates: certRows.map((certificate) => ({
      id: certificate.id,
      recipient_name: certificate.recipient_name,
      recipient_email: certificate.recipient_email,
      status: certificate.status,
      error_message: certificate.error_message || null,
      download_url: `/api/v1/jobs/${jobRow.job_id}/certificates/${certificate.id}/download`,
    })),
  };
}

function getJobWithCertificates(jobId) {
  const jobRow = db.prepare('SELECT * FROM jobs WHERE job_id = ?').get(jobId);
  if (!jobRow) return null;

  const certRows = db.prepare(
    'SELECT * FROM certificates WHERE job_id = ? ORDER BY created_at ASC'
  ).all(jobId);

  return formatJob(jobRow, certRows);
}

function finalizeJob(jobId) {
  const jobRow = db.prepare('SELECT * FROM jobs WHERE job_id = ?').get(jobId);
  if (!jobRow) return;

  const succeededCount = Number(jobRow.succeeded_count || 0);
  const failedCount = Number(jobRow.failed_count || 0);
  const totalCount = Number(jobRow.total_count || 0);
  const pendingCount = Math.max(totalCount - succeededCount - failedCount, 0);

  let status = 'PROCESSING';
  if (pendingCount === 0) {
    status = failedCount > 0 ? 'COMPLETED_WITH_ERRORS' : 'COMPLETED';
    if (succeededCount === 0 && failedCount > 0) {
      status = 'FAILED';
    }
  }

  db.prepare('UPDATE jobs SET status = ?, pending_count = ?, updated_at = ? WHERE job_id = ?').run(
    status,
    pendingCount,
    new Date().toISOString(),
    jobId,
  );
}

async function generateCertificatePdf({ jobId, certificateId, recipient, eventName, issuerName, issueDate }) {
  const jobDir = path.join(certDir, jobId);
  fs.mkdirSync(jobDir, { recursive: true });
  const filePath = path.join(jobDir, `${certificateId}.pdf`);

  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ size: 'A4', layout: 'landscape', margin: 50 });
    const stream = fs.createWriteStream(filePath);

    doc.on('error', (error) => {
      reject(error);
    });

    stream.on('error', (error) => {
      reject(error);
    });

    stream.on('finish', () => resolve(filePath));

    doc.pipe(stream);
    doc.fontSize(28).text(eventName || 'Certificate of Completion', { align: 'center' });
    doc.moveDown(2);
    doc.fontSize(18).text('This certifies that', { align: 'center' });
    doc.moveDown(1);
    doc.fontSize(32).text(recipient.name || 'Recipient', { align: 'center' });
    doc.moveDown(1.5);
    if (recipient.course_or_role) {
      doc.fontSize(18).text(recipient.course_or_role, { align: 'center' });
      doc.moveDown(1.5);
    }
    doc.fontSize(16).text('has successfully completed the program or event.', { align: 'center' });
    doc.moveDown(2);
    doc.fontSize(14).text(`Issued by: ${issuerName || 'Organization'}`, { align: 'center' });
    doc.text(`Date: ${issueDate || new Date().toISOString().slice(0, 10)}`, { align: 'center' });
    doc.end();
  });
}

async function processJob(jobId) {
  const jobRow = db.prepare('SELECT * FROM jobs WHERE job_id = ?').get(jobId);
  if (!jobRow) return;

  const rows = db.prepare('SELECT * FROM certificates WHERE job_id = ? ORDER BY created_at ASC').all(jobId);

  for (const certificate of rows) {
    if (certificate.status === 'FAILED') continue;

    const recipient = normalizeRecipient({
      name: certificate.recipient_name,
      email: certificate.recipient_email,
      course_or_role: certificate.course_or_role,
    });

    try {
      if (!recipient.name || !recipient.email) {
        throw new Error('Recipient name and email are required.');
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient.email)) {
        throw new Error('Invalid email address.');
      }

      const filePath = await generateCertificatePdf({
        jobId,
        certificateId: certificate.id,
        recipient,
        eventName: jobRow.event_name,
        issuerName: jobRow.issuer_name,
        issueDate: jobRow.issue_date,
      });

      db.prepare(
        'UPDATE certificates SET status = ?, file_path = ?, error_message = NULL, updated_at = ? WHERE id = ?'
      ).run('COMPLETED', filePath, new Date().toISOString(), certificate.id);

      db.prepare(
        'UPDATE jobs SET succeeded_count = succeeded_count + 1, pending_count = pending_count - 1, updated_at = ? WHERE job_id = ?'
      ).run(new Date().toISOString(), jobId);
    } catch (error) {
      db.prepare(
        'UPDATE certificates SET status = ?, error_message = ?, updated_at = ? WHERE id = ?'
      ).run('FAILED', error.message, new Date().toISOString(), certificate.id);

      db.prepare(
        'UPDATE jobs SET failed_count = failed_count + 1, pending_count = pending_count - 1, updated_at = ? WHERE job_id = ?'
      ).run(new Date().toISOString(), jobId);
    }
  }

  finalizeJob(jobId);
}

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.post('/api/v1/jobs', (req, res) => {
  const eventName = String(req.body?.event_name || '').trim();
  const issuerName = String(req.body?.issuer_name || '').trim();
  const issueDate = sanitizeDate(req.body?.issue_date);
  const recipients = Array.isArray(req.body?.recipients) ? req.body.recipients : [];

  if (!eventName || !issuerName) {
    return res.status(400).json({ detail: 'event_name and issuer_name are required.' });
  }

  if (recipients.length === 0) {
    return res.status(400).json({ detail: 'At least one recipient is required.' });
  }

  const jobId = randomUUID();
  const now = new Date().toISOString();

  db.prepare(
    'INSERT INTO jobs (job_id, event_name, issuer_name, issue_date, status, total_count, succeeded_count, failed_count, pending_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)'
  ).run(jobId, eventName, issuerName, issueDate, 'PROCESSING', recipients.length, recipients.length, now, now);

  for (const rawRecipient of recipients) {
    const recipient = normalizeRecipient(rawRecipient);
    const certificateId = randomUUID();
    db.prepare(
      'INSERT INTO certificates (id, job_id, recipient_name, recipient_email, course_or_role, status, error_message, file_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)'
    ).run(
      certificateId,
      jobId,
      recipient.name,
      recipient.email,
      recipient.course_or_role,
      'PENDING',
      now,
      now,
    );
  }

  processJob(jobId).catch((error) => {
    console.error('Error processing job', jobId, error);
  });

  const createdJob = getJobWithCertificates(jobId);
  res.status(201).json({
    job_id: jobId,
    status: 'PROCESSING',
    message: 'Job created successfully.',
    ...createdJob,
  });
});

app.get('/api/v1/jobs/:jobId', (req, res) => {
  const job = getJobWithCertificates(req.params.jobId);
  if (!job) {
    return res.status(404).json({ detail: 'Job not found.' });
  }

  return res.json(job);
});

app.get('/api/v1/jobs/:jobId/download', (req, res) => {
  const job = getJobWithCertificates(req.params.jobId);
  if (!job) {
    return res.status(404).json({ detail: 'Job not found.' });
  }

  const zip = new AdmZip();
  const files = job.certificates
    .map((certificate) => certificate.file_path || null)
    .filter(Boolean);

  for (const filePath of files) {
    if (fs.existsSync(filePath)) {
      zip.addLocalFile(filePath);
    }
  }

  const zipBuffer = zip.toBuffer();
  res.setHeader('Content-Type', 'application/zip');
  res.setHeader('Content-Disposition', `attachment; filename="${req.params.jobId}.zip"`);
  return res.send(zipBuffer);
});

app.get('/api/v1/jobs/:jobId/certificates/:certificateId/download', (req, res) => {
  const certificate = db.prepare(
    'SELECT * FROM certificates WHERE id = ? AND job_id = ?'
  ).get(req.params.certificateId, req.params.jobId);

  if (!certificate || !certificate.file_path) {
    return res.status(404).json({ detail: 'Certificate not found.' });
  }

  if (!fs.existsSync(certificate.file_path)) {
    return res.status(404).json({ detail: 'Certificate file is missing.' });
  }

  return res.download(certificate.file_path, `${certificate.recipient_name || 'certificate'}.pdf`);
});

app.use((req, res) => {
  res.status(404).json({ detail: 'Not found.' });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Bulk certificate API running on http://0.0.0.0:${port}`);
});
