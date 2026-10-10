import { useEffect, useState } from 'react'
import './App.css'

const sampleRecipients = [
  { name: 'Alice Example', email: 'alice@example.com', course_or_role: 'Python' },
  { name: 'Bob Example', email: 'bob@example.com', course_or_role: 'Machine Learning' },
]

const emptyRecipient = { name: '', email: '', course_or_role: '' }

function App() {
  const [eventName, setEventName] = useState('Summer Bootcamp')
  const [issuerName, setIssuerName] = useState('Acme Education')
  const [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0, 10))
  const [recipients, setRecipients] = useState(sampleRecipients)
  const [errorMessage, setErrorMessage] = useState('')
  const [job, setJob] = useState(null)
  const [poller, setPoller] = useState(null)

  const apiFetch = async (url, options = {}) => {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    })

    const text = await response.text()
    let payload = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = text
      }
    }

    if (!response.ok) {
      throw new Error(payload?.detail || payload || 'Request failed')
    }

    return payload
  }

  const updateRecipient = (index, field, value) => {
    setRecipients((current) =>
      current.map((recipient, i) => {
        if (i !== index) return recipient
        return { ...recipient, [field]: value }
      }),
    )
  }

  const addRecipient = () => {
    setRecipients((current) => [...current, { ...emptyRecipient }])
  }

  const removeRecipient = (index) => {
    setRecipients((current) => current.filter((_, i) => i !== index))
  }

  const loadSample = () => {
    setEventName('Summer Bootcamp')
    setIssuerName('Acme Education')
    setIssueDate(new Date().toISOString().slice(0, 10))
    setRecipients(sampleRecipients)
    setErrorMessage('')
  }

  const fetchJobStatus = async (jobId) => {
    const data = await apiFetch(`/api/v1/jobs/${jobId}?limit=100`)
    setJob(data)
    return data
  }

  const startPolling = (jobId) => {
    if (poller) window.clearInterval(poller)
    const timer = window.setInterval(async () => {
      try {
        const data = await fetchJobStatus(jobId)
        if (['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes((data.status || '').toUpperCase())) {
          window.clearInterval(timer)
          setPoller(null)
        }
      } catch {
        window.clearInterval(timer)
        setPoller(null)
      }
    }, 1500)
    setPoller(timer)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setErrorMessage('')

    const payload = {
      event_name: eventName.trim(),
      issuer_name: issuerName.trim(),
      issue_date: issueDate || undefined,
      recipients: recipients
        .filter((recipient) => recipient.name || recipient.email || recipient.course_or_role)
        .map((recipient) => ({
          name: recipient.name.trim(),
          email: recipient.email.trim(),
          course_or_role: recipient.course_or_role.trim() || null,
        })),
    }

    try {
      const result = await apiFetch('/api/v1/jobs', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      if (result.job_id) {
        setJob({ job_id: result.job_id, status: result.status, ...result })
        startPolling(result.job_id)
      }
    } catch (err) {
      setErrorMessage(err.message)
    }
  }

  const refreshJob = async () => {
    if (!job?.job_id) return
    try {
      const data = await fetchJobStatus(job.job_id)
      if (['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes((data.status || '').toUpperCase())) {
        if (poller) window.clearInterval(poller)
        setPoller(null)
      }
    } catch (err) {
      setErrorMessage(err.message)
    }
  }

  const statusLabel = (value) => (value || 'PENDING').toUpperCase()

  const statusClass = (value) => {
    const item = statusLabel(value)
    if (item === 'COMPLETED') return 'status success'
    if (item === 'FAILED') return 'status danger'
    if (item === 'COMPLETED_WITH_ERRORS' || item === 'PROCESSING') return 'status warning'
    return 'status'
  }

  useEffect(() => {
    return () => {
      if (poller) window.clearInterval(poller)
    }
  }, [poller])

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Bulk Certificate Generator</h1>
        </div>
        <button type="button" className="secondary-btn" onClick={loadSample}>
          Load sample
        </button>
      </header>

      <main className="layout-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Job setup</h2>
          </div>

          <form onSubmit={handleSubmit} className="job-form">
            <div className="field-grid">
              <label>
                <span>Event name</span>
                <input value={eventName} onChange={(e) => setEventName(e.target.value)} />
              </label>
              <label>
                <span>Issuer name</span>
                <input value={issuerName} onChange={(e) => setIssuerName(e.target.value)} />
              </label>
            </div>

            <label>
              <span>Issue date</span>
              <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
            </label>

            <div className="recipient-toolbar">
              <h3>Recipients</h3>
              <button type="button" className="secondary-btn" onClick={addRecipient}>Add recipient</button>
            </div>

            <div className="recipient-list">
              {recipients.map((recipient, index) => (
                <div className="recipient-card" key={`${recipient.email || 'new'}-${index}`}>
                  <div className="recipient-row">
                    <label>
                      <span>Name</span>
                      <input
                        value={recipient.name}
                        onChange={(e) => updateRecipient(index, 'name', e.target.value)}
                      />
                    </label>
                    <label>
                      <span>Email</span>
                      <input
                        type="email"
                        value={recipient.email}
                        onChange={(e) => updateRecipient(index, 'email', e.target.value)}
                      />
                    </label>
                    <label>
                      <span>Course / role</span>
                      <input
                        value={recipient.course_or_role || ''}
                        onChange={(e) => updateRecipient(index, 'course_or_role', e.target.value)}
                      />
                    </label>
                  </div>
                  {recipients.length > 1 && (
                    <button type="button" className="link-button" onClick={() => removeRecipient(index)}>
                      Remove
                    </button>
                  )}
                </div>
              ))}
            </div>

            {errorMessage && <div className="error-box">{errorMessage}</div>}

            <div className="submit-row">
              <button type="submit" className="primary-btn">Create job</button>
              <button type="button" className="secondary-btn" onClick={refreshJob}>Refresh status</button>
            </div>
          </form>
        </section>

        <aside className="panel">
          <div className="panel-header">
            <h2>Job status</h2>
          </div>

          <div className="status-box">
            <div className="status-topline">
              {job ? <span className={statusClass(job.status)}>{statusLabel(job.status)}</span> : <span className="status">PENDING</span>}
              {job && <strong>{job.job_id}</strong>}
            </div>

            {job && (
              <>
                <div className="stats-grid">
                  <div><span>Total</span><strong>{job.total_count || 0}</strong></div>
                  <div><span>Success</span><strong>{job.succeeded_count || 0}</strong></div>
                  <div><span>Failed</span><strong>{job.failed_count || 0}</strong></div>
                  <div><span>Pending</span><strong>{job.pending_count || 0}</strong></div>
                </div>

                <div className="progress-row">
                  <label>Progress</label>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${Number(job.progress_percentage || 0)}%` }} />
                  </div>
                  <strong>{Number(job.progress_percentage || 0).toFixed(0)}%</strong>
                </div>

                {job.status !== 'FAILED' && (
                  <button type="button" className="secondary-btn wide" onClick={() => window.open(`/api/v1/jobs/${job.job_id}/download`, '_blank')}>
                    Download ZIP
                  </button>
                )}
              </>
            )}
          </div>
        </aside>
      </main>

      <section className="panel cert-panel">
        <div className="panel-header">
          <h2>Certificates</h2>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Message</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {!job || !job.certificates?.length ? (
                <tr>
                  <td colSpan="5" className="empty-state">No certificates generated yet.</td>
                </tr>
              ) : (
                job.certificates.map((certificate) => (
                  <tr key={certificate.id}>
                    <td>{certificate.recipient_name}</td>
                    <td>{certificate.recipient_email}</td>
                    <td>
                      <span className={statusClass(certificate.status)}>{statusLabel(certificate.status)}</span>
                    </td>
                    <td>{certificate.error_message || '-'}</td>
                    <td>
                      {certificate.download_url ? (
                        <a href={certificate.download_url} target="_blank" rel="noreferrer">
                          Download
                        </a>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

export default App
