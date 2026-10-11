import React, { useState } from 'react';
import {
  DownloadCloud,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { api } from '../api/client';
import type { DownloadInspectResponse, VideoAsset } from '../types';

interface DashboardPageProps {
  onOpenInStudio: (assetId: string) => void;
  onOpenLibrary: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onOpenInStudio,
  onOpenLibrary,
}) => {
  const [url, setUrl] = useState('');
  const [rightsAcknowledged, setRightsAcknowledged] = useState(true);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [inspectResult, setInspectResult] = useState<DownloadInspectResponse | null>(null);
  const [downloadedAsset, setDownloadedAsset] = useState<VideoAsset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadStage, setDownloadStage] = useState<string>('');

  const handleInspect = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url.trim()) return;
    setError(null);
    setInspectResult(null);
    setDownloadedAsset(null);
    setIsInspecting(true);

    try {
      const res = await api.inspectUrl(url.trim());
      setInspectResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect link.');
    } finally {
      setIsInspecting(false);
    }
  };

  const handleDownload = async () => {
    if (!url.trim()) return;
    if (!rightsAcknowledged) {
      setError('Please acknowledge rights/authorization before downloading.');
      return;
    }

    setError(null);
    setIsDownloading(true);
    setDownloadStage('Connecting to Kuaishou / Kwai video source...');

    try {
      setDownloadStage('Extracting video stream with yt-dlp...');
      const asset = await api.downloadVideo(url.trim(), rightsAcknowledged);
      setDownloadedAsset(asset);
      setDownloadStage('Video downloaded and saved locally on your Mac!');
    } catch (err: any) {
      setError(err.message || 'Download failed.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="page-wrapper" style={{ maxWidth: '960px' }}>
      {/* Hero Header */}
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Download Kuaishou / Kwai Video</h2>
        <p className="text-muted" style={{ marginTop: '4px' }}>
          Fetch source videos locally to your Mac storage, ready for voice-over replacement and captioning.
        </p>
      </div>

      {/* Main Download Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <form onSubmit={handleInspect}>
          <label
            htmlFor="kuaishou-url-input"
            style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '8px' }}
          >
            Kuaishou / Kwai Video URL
          </label>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input
              id="kuaishou-url-input"
              type="url"
              className="input"
              placeholder="https://v.kuaishou.com/xxxxxx or https://kwai.com/v/xxxxxx"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setError(null);
              }}
              required
            />
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={isInspecting || isDownloading || !url.trim()}
              style={{ whiteSpace: 'nowrap' }}
            >
              {isInspecting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Inspecting...</span>
                </>
              ) : (
                'Inspect Link'
              )}
            </button>
          </div>

          {/* Rights disclaimer acknowledgment */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 14px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              marginBottom: '20px',
            }}
          >
            <input
              type="checkbox"
              id="rights-checkbox"
              checked={rightsAcknowledged}
              onChange={(e) => setRightsAcknowledged(e.target.checked)}
              style={{ marginTop: '3px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
            />
            <label
              htmlFor="rights-checkbox"
              style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)', cursor: 'pointer', lineHeight: 1.4 }}
            >
              I confirm that I have authorized rights or permission to download, dub, and adapt this video content.
            </label>
          </div>

          {/* Primary Action Button */}
          <button
            type="button"
            className="btn btn-primary"
            disabled={isDownloading || !url.trim() || !rightsAcknowledged}
            onClick={handleDownload}
            style={{ width: '100%', height: '44px' }}
          >
            {isDownloading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Downloading to Mac Storage...</span>
              </>
            ) : (
              <>
                <DownloadCloud size={18} />
                <span>Download Video to Mac</span>
              </>
            )}
          </button>
        </form>

        {/* Error Notification */}
        {error && (
          <div className="alert alert-error" style={{ marginTop: '20px' }}>
            <AlertTriangle size={18} />
            <div>
              <strong>Action required:</strong> {error}
            </div>
          </div>
        )}

        {/* Progress Notification */}
        {isDownloading && (
          <div className="alert alert-info" style={{ marginTop: '20px' }}>
            <Loader2 size={18} className="animate-spin" />
            <div>
              <strong>Download in progress:</strong> {downloadStage}
            </div>
          </div>
        )}
      </div>

      {/* Inspect Card (Duplicate Warning or Preview) */}
      {inspectResult && (
        <div
          className="card"
          style={{
            marginBottom: '24px',
            borderColor: inspectResult.duplicate_asset_id
              ? 'rgba(245, 158, 11, 0.4)'
              : 'rgba(37, 99, 235, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            {inspectResult.duplicate_asset_id ? (
              <AlertTriangle size={20} color="var(--color-warning)" />
            ) : (
              <CheckCircle2 size={20} color="var(--color-accent)" />
            )}
            <h3 style={{ fontSize: '1.1rem' }}>
              {inspectResult.duplicate_asset_id ? 'Duplicate Detected in Library' : 'Video Information Verified'}
            </h3>
          </div>

          <p style={{ fontSize: '0.875rem', marginBottom: '16px', color: 'var(--color-muted-foreground)' }}>
            {inspectResult.message}
          </p>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {inspectResult.duplicate_asset_id ? (
              <button
                className="btn btn-secondary"
                onClick={() => onOpenInStudio(inspectResult.duplicate_asset_id!)}
              >
                <Sparkles size={16} color="var(--color-primary)" />
                <span>Open Existing Video in Studio</span>
              </button>
            ) : (
              <button
                className="btn btn-accent"
                onClick={handleDownload}
                disabled={isDownloading}
              >
                <DownloadCloud size={16} />
                <span>Proceed with Download</span>
              </button>
            )}
            <button className="btn btn-secondary" onClick={onOpenLibrary}>
              View All Library Assets
            </button>
          </div>
        </div>
      )}

      {/* Successfully Downloaded Banner */}
      {downloadedAsset && (
        <div
          className="card"
          style={{
            borderColor: 'rgba(16, 185, 129, 0.4)',
            backgroundColor: 'rgba(16, 185, 129, 0.05)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <CheckCircle2 size={24} color="var(--color-success)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Download Completed</h3>
              <p className="text-muted">{downloadedAsset.filename}</p>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: '12px',
              padding: '12px',
              backgroundColor: 'rgba(0,0,0,0.3)',
              borderRadius: '8px',
              marginBottom: '20px',
              fontSize: '0.8125rem',
            }}
          >
            <div>
              <span className="text-muted">Duration:</span>
              <p style={{ fontWeight: 600 }}>{downloadedAsset.duration.toFixed(1)}s</p>
            </div>
            <div>
              <span className="text-muted">Resolution:</span>
              <p style={{ fontWeight: 600 }}>
                {downloadedAsset.width}x{downloadedAsset.height} ({downloadedAsset.aspect_ratio})
              </p>
            </div>
            <div>
              <span className="text-muted">File Size:</span>
              <p style={{ fontWeight: 600 }}>
                {(downloadedAsset.file_size / (1024 * 1024)).toFixed(1)} MB
              </p>
            </div>
            <div>
              <span className="text-muted">Platform:</span>
              <p style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                {downloadedAsset.source_platform}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn btn-primary"
              onClick={() => onOpenInStudio(downloadedAsset.id)}
            >
              <Sparkles size={16} />
              <span>Launch in Studio (Replace Voice-over)</span>
            </button>
            <button className="btn btn-secondary" onClick={onOpenLibrary}>
              Go to Library
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
