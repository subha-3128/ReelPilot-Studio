import React, { useEffect, useState } from 'react';
import { Calendar as CalendarIcon, Clock, XCircle, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import type { Publication, AppSettings } from '../types';

export const CalendarPage: React.FC = () => {
  const [publications, setPublications] = useState<Publication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [settings, setSettings] = useState<AppSettings | null>(null);

  const fetchScheduled = async () => {
    try {
      setLoading(true);
      const data = await api.getPublications(
        platformFilter !== 'all' ? platformFilter : undefined,
        'scheduled'
      );
      setPublications(data);
      const s = await api.getSettings();
      setSettings(s);
    } catch (err) {
      console.error('Failed to load scheduled publications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduled();
  }, [platformFilter]);

  const handleCancel = async (id: string) => {
    if (!window.confirm('Cancel this scheduled post?')) return;
    try {
      await api.cancelPublication(id);
      setPublications(publications.filter((p) => p.id !== id));
    } catch (err: any) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  return (
    <div className="page-wrapper" style={{ maxWidth: '1000px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Publishing Calendar</h2>
          <p className="text-muted">
            Scheduled social media publications. Active timezone: <strong>{settings?.timezone || 'Local'}</strong>
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <select
            className="select"
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="all">All Platforms</option>
            <option value="instagram">Instagram Only</option>
            <option value="youtube">YouTube Only</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={fetchScheduled}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Mac awake notice */}
      <div className="alert alert-warning" style={{ marginBottom: '24px' }}>
        <Clock size={18} />
        <div>
          <strong>Scheduler Notice:</strong> Scheduled jobs run on your local Mac background worker. The Mac and studio application must remain running and connected at the scheduled time to publish.
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-muted-foreground)' }}>
          Loading scheduled posts...
        </div>
      ) : publications.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <CalendarIcon size={48} color="var(--color-muted-foreground)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>No posts scheduled</h3>
          <p className="text-muted">
            Go to the Studio tab and select "Schedule for Later" when publishing a video.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {publications.map((pub) => (
            <div
              key={pub.id}
              className="card"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px 20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span className="badge badge-primary" style={{ textTransform: 'capitalize' }}>
                    {pub.platform}
                  </span>
                  <span className="badge badge-warning">Scheduled</span>
                </div>
                <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                  Planned Time: {pub.scheduled_time ? new Date(pub.scheduled_time).toLocaleString() : 'N/A'}
                </p>
                <p className="text-muted" style={{ fontSize: '0.75rem' }}>
                  Idempotency Key: {pub.idempotency_key}
                </p>
              </div>

              <button
                className="btn btn-danger btn-sm"
                onClick={() => handleCancel(pub.id)}
              >
                <XCircle size={14} /> Cancel Schedule
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
