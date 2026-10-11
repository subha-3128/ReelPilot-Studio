import React, { useEffect, useState } from 'react';
import {
  Film,
  Sparkles,
  Trash2,
  Search,
  Layers,
  Mic,
  Eye,
} from 'lucide-react';
import { api } from '../api/client';
import type { VideoAsset } from '../types';

interface LibraryPageProps {
  onOpenInStudio: (assetId: string) => void;
  onNavigateToDownload: () => void;
}

export const LibraryPage: React.FC<LibraryPageProps> = ({
  onOpenInStudio,
  onNavigateToDownload,
}) => {
  const [assets, setAssets] = useState<VideoAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedAsset, setSelectedAsset] = useState<VideoAsset | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const data = await api.getAssets(
        searchQuery || undefined,
        filterStatus !== 'all' ? filterStatus : undefined
      );
      setAssets(data);
    } catch (err) {
      console.error('Failed to load assets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [filterStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAssets();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this original video asset and its derivatives? This cannot be undone.')) {
      return;
    }
    try {
      setDeletingId(id);
      await api.deleteAsset(id, true);
      setAssets(assets.filter((a) => a.id !== id));
      if (selectedAsset?.id === id) {
        setSelectedAsset(null);
      }
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="page-wrapper">
      {/* Top Controls */}
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
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '400px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search
              size={16}
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted-foreground)' }}
            />
            <input
              type="text"
              className="input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search filename or URL..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-secondary">
            Search
          </button>
        </form>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)' }}>Filter:</span>
          <select
            className="select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ width: 'auto', minWidth: '160px' }}
          >
            <option value="all">All Videos</option>
            <option value="has_voiceover">With Voice-over</option>
            <option value="has_derivatives">With Derivatives</option>
          </select>

          <button className="btn btn-primary" onClick={onNavigateToDownload}>
            + Download New
          </button>
        </div>
      </div>

      {/* Asset Grid / List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-muted-foreground)' }}>
          Loading your media library...
        </div>
      ) : assets.length === 0 ? (
        <div
          className="card"
          style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}
        >
          <Film size={48} color="var(--color-muted-foreground)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>No videos in library yet</h3>
          <p className="text-muted" style={{ maxWidth: '420px', margin: '0 auto 24px' }}>
            Paste a Kuaishou / Kwai link in the downloader tab to ingest your first video.
          </p>
          <button className="btn btn-primary" onClick={onNavigateToDownload}>
            Go to Downloader
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '20px',
          }}
        >
          {assets.map((asset) => {
            const hasVO = asset.voiceovers && asset.voiceovers.length > 0;
            const hasDeriv = asset.derivatives && asset.derivatives.length > 0;

            return (
              <div
                key={asset.id}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '16px',
                  backgroundColor: 'var(--color-card)',
                }}
              >
                {/* Thumbnail / Video Box */}
                <div
                  style={{
                    position: 'relative',
                    width: '100%',
                    height: '180px',
                    borderRadius: '8px',
                    backgroundColor: '#000000',
                    overflow: 'hidden',
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {asset.thumbnail_path ? (
                    <img
                      src={`http://127.0.0.1:8000/api/media/thumbnail/${asset.id}`}
                      alt={asset.filename}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={(e) => {
                        // Fallback to placeholder if thumbnail is missing
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <Film size={36} color="var(--color-muted-foreground)" />
                  )}

                  {/* Duration Badge */}
                  <span
                    style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      backgroundColor: 'rgba(0, 0, 0, 0.75)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                    }}
                  >
                    {asset.duration.toFixed(1)}s
                  </span>

                  {/* Aspect Ratio Badge */}
                  <span
                    style={{
                      position: 'absolute',
                      top: '8px',
                      left: '8px',
                      backgroundColor: 'rgba(0, 0, 0, 0.75)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 500,
                    }}
                  >
                    {asset.aspect_ratio}
                  </span>
                </div>

                {/* Details */}
                <h4
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    marginBottom: '6px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={asset.filename}
                >
                  {asset.filename}
                </h4>

                <p className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '12px' }}>
                  {asset.width}x{asset.height} • {(asset.file_size / (1024 * 1024)).toFixed(1)} MB • {asset.source_platform}
                </p>

                {/* Status Badges */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  {hasVO ? (
                    <span className="badge badge-primary">
                      <Mic size={11} /> Voice-over Attached
                    </span>
                  ) : (
                    <span className="badge badge-muted">Original Audio Only</span>
                  )}

                  {hasDeriv ? (
                    <span className="badge badge-accent">
                      <Layers size={11} /> {asset.derivatives.length} Derivative(s)
                    </span>
                  ) : null}
                </div>

                {/* Actions */}
                <div style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-primary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => onOpenInStudio(asset.id)}
                  >
                    <Sparkles size={14} />
                    <span>Open in Studio</span>
                  </button>

                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setSelectedAsset(asset)}
                    title="Inspect details"
                  >
                    <Eye size={14} />
                  </button>

                  <button
                    className="btn btn-danger btn-sm"
                    disabled={deletingId === asset.id}
                    onClick={() => handleDelete(asset.id)}
                    title="Delete original and derivatives"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Asset Detail Modal */}
      {selectedAsset && (
        <div className="modal-overlay" onClick={() => setSelectedAsset(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem' }}>Asset Inspector</h3>
                <p className="text-muted">{selectedAsset.filename}</p>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedAsset(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <video
                controls
                style={{ width: '100%', maxHeight: '320px', borderRadius: '8px', backgroundColor: '#000' }}
                src={`http://127.0.0.1:8000/api/media/video/${selectedAsset.id}`}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.8125rem', marginBottom: '20px' }}>
              <div style={{ padding: '8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                <span className="text-muted">Original Source URL:</span>
                <p style={{ wordBreak: 'break-all', marginTop: '2px' }}>{selectedAsset.original_source_url}</p>
              </div>
              <div style={{ padding: '8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                <span className="text-muted">Aspect Ratio / Size:</span>
                <p style={{ marginTop: '2px' }}>{selectedAsset.aspect_ratio} • {(selectedAsset.file_size / (1024*1024)).toFixed(1)} MB</p>
              </div>
              <div style={{ padding: '8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                <span className="text-muted">Attached Voiceovers:</span>
                <p style={{ marginTop: '2px' }}>{selectedAsset.voiceovers?.length || 0} track(s)</p>
              </div>
              <div style={{ padding: '8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                <span className="text-muted">Exported Derivatives:</span>
                <p style={{ marginTop: '2px' }}>{selectedAsset.derivatives?.length || 0} variant(s)</p>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn btn-secondary" onClick={() => setSelectedAsset(null)}>
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  const id = selectedAsset.id;
                  setSelectedAsset(null);
                  onOpenInStudio(id);
                }}
              >
                Launch Studio
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
