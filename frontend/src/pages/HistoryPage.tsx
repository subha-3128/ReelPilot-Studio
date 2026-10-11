import React, { useEffect, useState } from 'react';
import {
  History as HistoryIcon,
  RotateCcw,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import type { Publication } from '../types';

export const HistoryPage: React.FC = () => {
  const [publications, setPublications] = useState<Publication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getPublications(
        platformFilter !== 'all' ? platformFilter : undefined,
        statusFilter !== 'all' ? statusFilter : undefined
      );
      setPublications(data);
    } catch (err) {
      console.error('Failed to load publication history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [platformFilter, statusFilter]);

  const handleRetry = async (id: string) => {
    try {
      setRetryingId(id);
      const updated = await api.retryPublication(id);
      setPublications(publications.map((p) => (p.id === id ? updated : p)));
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div className="page-wrapper" style={{ maxWidth: '1080px' }}>
      {/* Header & Filters */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '24px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Publishing History & Audit</h2>
          <p className="text-muted">
            Independent per-platform records. Failed platforms can be retried without duplicating successful posts.
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
            <option value="instagram">Instagram</option>
            <option value="youtube">YouTube</option>
          </select>

          <select
            className="select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="all">All Statuses</option>
            <option value="published">Published</option>
            <option value="failed">Failed</option>
            <option value="scheduled">Scheduled</option>
            <option value="publishing">Publishing</option>
          </select>

          <button className="btn btn-secondary btn-sm" onClick={fetchHistory}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-muted-foreground)' }}>
          Loading publication audit records...
        </div>
      ) : publications.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <HistoryIcon size={48} color="var(--color-muted-foreground)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>No publishing history yet</h3>
          <p className="text-muted">
            Publications initiated from the Video Studio will appear here with full audit trails.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {publications.map((pub) => {
            const isSuccess = pub.status === 'published';
            const isFailed = pub.status === 'failed';

            return (
              <div
                key={pub.id}
                className="card"
                style={{
                  padding: '16px 20px',
                  borderColor: isSuccess
                    ? 'rgba(16, 185, 129, 0.3)'
                    : isFailed
                    ? 'rgba(220, 38, 38, 0.3)'
                    : 'var(--color-border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span
                        className="badge badge-primary"
                        style={{ textTransform: 'capitalize', fontWeight: 600 }}
                      >
                        {pub.platform}
                      </span>
                      <span
                        className={`badge ${
                          isSuccess
                            ? 'badge-success'
                            : isFailed
                            ? 'badge-warning'
                            : 'badge-muted'
                        }`}
                      >
                        {pub.status}
                      </span>
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                        Attempts: {pub.attempts}
                      </span>
                    </div>

                    <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)', marginBottom: '4px' }}>
                      Created: {new Date(pub.created_at).toLocaleString()} • Updated: {new Date(pub.updated_at).toLocaleString()}
                    </p>

                    {/* Remote Post Link */}
                    {pub.remote_post_url && (
                      <a
                        href={pub.remote_post_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          color: 'var(--color-primary)',
                          fontSize: '0.8125rem',
                          fontWeight: 600,
                          textDecoration: 'none',
                          marginTop: '4px',
                        }}
                      >
                        <span>View Live Post</span>
                        <ExternalLink size={12} />
                      </a>
                    )}

                    {/* Error details */}
                    {pub.error_details && (
                      <div
                        style={{
                          marginTop: '8px',
                          padding: '8px 12px',
                          backgroundColor: 'rgba(220, 38, 38, 0.1)',
                          borderRadius: '6px',
                          border: '1px solid rgba(220, 38, 38, 0.2)',
                          fontSize: '0.78rem',
                          color: '#FECACA',
                        }}
                      >
                        <strong>Provider Message:</strong> {pub.error_details}
                      </div>
                    )}
                  </div>

                  {/* Retry Button */}
                  {isFailed && (
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={retryingId === pub.id}
                      onClick={() => handleRetry(pub.id)}
                    >
                      <RotateCcw size={14} />
                      <span>Retry {pub.platform}</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
