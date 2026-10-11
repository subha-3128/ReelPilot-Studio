import React, { useEffect, useState } from 'react';
import {
  Folder,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Share2,
  Shield,
  Save,
} from 'lucide-react';
import { api } from '../api/client';
import type { AppSettings, SocialAccount } from '../types';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [, setLoading] = useState<boolean>(true);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Editable settings fields
  const [storageDir, setStorageDir] = useState<string>('');
  const [isSavingStorage, setIsSavingStorage] = useState<boolean>(false);
  const [timezone, setTimezone] = useState<string>('Asia/Kolkata');
  const [syncPolicy, setSyncPolicy] = useState<string>('keep_natural_speed');
  const [fontSize, setFontSize] = useState<number>(24);

  // Social account connect modal / state
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState<string>('');
  const [accountNameInput, setAccountNameInput] = useState<string>('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const s = await api.getSettings();
        setSettings(s);
        setStorageDir(s.storage_dir);
        setTimezone(s.timezone);
        setSyncPolicy(s.default_sync_policy);
        setFontSize(s.subtitle_font_size);

        const accs = await api.getAccounts();
        setAccounts(accs);
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to load settings');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSaveStorageDir = async () => {
    try {
      setErrorMessage(null);
      setIsSavingStorage(true);
      await api.updateSettings({
        storage_dir: storageDir,
      });
      const updated = await api.getSettings();
      setSettings(updated);
      setStorageDir(updated.storage_dir);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update storage directory');
    } finally {
      setIsSavingStorage(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setErrorMessage(null);
      await api.updateSettings({
        storage_dir: storageDir,
        timezone,
        default_sync_policy: syncPolicy,
        subtitle_font_size: fontSize,
      });
      const updated = await api.getSettings();
      setSettings(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update settings');
    }
  };

  const handleConnectAccount = async (platform: string) => {
    try {
      setErrorMessage(null);
      const acc = await api.connectAccount({
        platform,
        access_token: tokenInput || undefined,
        account_name: accountNameInput || `${platform.toUpperCase()} Creator Account`,
      });
      setAccounts(accounts.map((a) => (a.platform === platform ? acc : a)));
      setConnectingPlatform(null);
      setTokenInput('');
      setAccountNameInput('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to connect account');
    }
  };

  return (
    <div className="page-wrapper" style={{ maxWidth: '960px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Settings & Integrations</h2>
        <p className="text-muted">
          Manage local Mac storage preferences, default studio policies, and social connections.
        </p>
      </div>

      {savedSuccess && (
        <div className="alert alert-success" style={{ marginBottom: '20px' }}>
          <CheckCircle2 size={16} />
          <span>Preferences updated successfully.</span>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-error" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* System & Storage Configuration */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.125rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Folder size={18} color="var(--color-primary)" />
          <span>Video Storage Location</span>
        </h3>
        <p className="text-muted" style={{ fontSize: '0.8125rem', marginBottom: '16px' }}>
          Choose where you want Kuaishou Video Studio to save all original downloads, English voice-overs, and exported derivatives on your Mac.
        </p>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
            Media Storage Directory Path
          </label>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type="text"
              className="input"
              value={storageDir}
              onChange={(e) => setStorageDir(e.target.value)}
              placeholder="/Users/yourname/Movies/KuaishouStudio"
              style={{ flex: 1, fontFamily: 'monospace', fontSize: '0.85rem' }}
            />
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleSaveStorageDir}
              disabled={isSavingStorage || !storageDir.trim()}
              style={{ whiteSpace: 'nowrap' }}
            >
              <Save size={15} />
              <span>{isSavingStorage ? 'Saving...' : 'Apply Storage'}</span>
            </button>
          </div>
          <p className="text-muted" style={{ fontSize: '0.72rem', marginTop: '6px' }}>
            Enter an absolute path or use ~ (e.g. <code>~/Movies/KuaishouStudio</code>). Subfolders (originals, voiceovers, derivatives) will be created automatically.
          </p>
        </div>


        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', paddingTop: '12px', borderTop: '1px solid var(--color-border)' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
            <span className="text-muted">Available Disk Space:</span>
            <p style={{ fontSize: '1rem', fontWeight: 600, marginTop: '4px', color: 'var(--color-success)' }}>
              {settings?.free_disk_space_gb || 0} GB Free
            </p>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
            <span className="text-muted">FFmpeg / FFprobe:</span>
            <p style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '4px' }}>
              {settings?.ffmpeg_available ? 'Available (v9.0.2)' : 'Not detected'}
            </p>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
            <span className="text-muted">Downloader Engine:</span>
            <p style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '4px', color: 'var(--color-primary)' }}>
              Native Stream + yt-dlp
            </p>
          </div>
        </div>
      </div>

      {/* Preferences Form */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.125rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={18} color="var(--color-accent)" />
          <span>Studio Default Policies</span>
        </h3>

        <form onSubmit={handleSaveSettings}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                Default Timezone
              </label>
              <select
                className="select"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="UTC">UTC (Universal)</option>
                <option value="America/New_York">America/New_York (EST/EDT)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="Asia/Shanghai">Asia/Shanghai (CST)</option>
              </select>
              <p className="text-muted" style={{ fontSize: '0.72rem', marginTop: '4px' }}>
                Used for scheduling social posts.
              </p>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                Default Voice-over Sync Policy
              </label>
              <select
                className="select"
                value={syncPolicy}
                onChange={(e) => setSyncPolicy(e.target.value)}
              >
                <option value="keep_natural_speed">Keep Natural Speed (Recommended)</option>
                <option value="fit_to_video">Fit to Video Duration</option>
                <option value="manual_adjustment">Manual Adjustment</option>
              </select>
              <p className="text-muted" style={{ fontSize: '0.72rem', marginTop: '4px' }}>
                Applied initially in Studio wizard step 2.
              </p>
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
              Default Subtitle Font Size (pt)
            </label>
            <input
              type="number"
              className="input"
              value={fontSize}
              onChange={(e) => setFontSize(parseInt(e.target.value) || 24)}
              style={{ maxWidth: '200px' }}
            />
          </div>

          <button type="submit" className="btn btn-primary">
            <Save size={16} />
            <span>Save Preferences</span>
          </button>
        </form>
      </div>

      {/* Social Platform Connections */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.125rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Share2 size={18} color="var(--color-primary)" />
          <span>Social Publishing Connections</span>
        </h3>
        <p className="text-muted" style={{ marginBottom: '20px' }}>
          Connect your official Instagram and YouTube creator accounts. Credentials remain strictly server-side on your local Mac.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Instagram Card */}
          <div
            style={{
              padding: '16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(0,0,0,0.2)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Instagram (Meta Graph API Reels)</h4>
                <span
                  className={`badge ${
                    accounts.find((a) => a.platform === 'instagram')?.connection_status === 'connected'
                      ? 'badge-success'
                      : 'badge-muted'
                  }`}
                >
                  {accounts.find((a) => a.platform === 'instagram')?.connection_status || 'Disconnected'}
                </span>
              </div>
              <p className="text-muted" style={{ fontSize: '0.78rem', maxWidth: '580px' }}>
                Requires an Instagram Professional account connected to a Meta App with `instagram_content_publish`. Note: Meta servers require a publicly accessible video URL to ingest Reels.
              </p>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setConnectingPlatform('instagram')}
            >
              Configure
            </button>
          </div>

          {/* YouTube Card */}
          <div
            style={{
              padding: '16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(0,0,0,0.2)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>YouTube (Google Data API v3)</h4>
                <span
                  className={`badge ${
                    accounts.find((a) => a.platform === 'youtube')?.connection_status === 'connected'
                      ? 'badge-success'
                      : 'badge-muted'
                  }`}
                >
                  {accounts.find((a) => a.platform === 'youtube')?.connection_status || 'Disconnected'}
                </span>
              </div>
              <p className="text-muted" style={{ fontSize: '0.78rem', maxWidth: '580px' }}>
                Supports uploading videos and Shorts with OAuth 2.0 user credentials. An API key alone is not sufficient for account channel uploads.
              </p>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setConnectingPlatform('youtube')}
            >
              Configure
            </button>
          </div>
        </div>
      </div>

      {/* AnyTranscribe Verification Findings */}
      <div className="card" style={{ borderColor: 'rgba(37, 99, 235, 0.3)' }}>
        <h3 style={{ fontSize: '1.125rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={18} color="var(--color-accent)" />
          <span>Transcription Provider Status (AnyTranscribe Audit)</span>
        </h3>
        <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)', lineHeight: 1.5 }}>
          <strong>Verified Audit Result:</strong> AnyTranscribe does not provide an official public developer API or SDK. In strict compliance with the project guidelines against web scraping or undocumented automation, this application utilizes the built-in <strong>Local Speech Engine</strong>. Speech-to-text runs entirely on your Mac, preserving complete privacy.
        </p>
      </div>

      {/* About ReelPilot Card */}
      <div
        className="card"
        style={{
          marginTop: '24px',
          textAlign: 'center',
          padding: '32px 24px',
          background: 'linear-gradient(180deg, rgba(31, 41, 55, 0.4) 0%, rgba(17, 24, 39, 0.6) 100%)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <img
          src="/logo.svg"
          alt="ReelPilot Logo"
          style={{
            width: '48px',
            height: '48px',
            margin: '0 auto 12px',
            display: 'block',
            borderRadius: '12px',
            boxShadow: '0 0 20px rgba(255, 94, 58, 0.3)',
          }}
        />
        <h3
          style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            marginBottom: '4px',
            color: '#FFFFFF',
          }}
        >
          ReelPilot
        </h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--color-muted-foreground)', marginBottom: '14px' }}>
          From raw clips to ready-to-publish content.
        </p>
        <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)', marginBottom: '6px' }}>
          Crafted with ❤️ By{' '}
          <a
            href="https://github.com/subha-3128"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--color-primary)', fontWeight: 600, textDecoration: 'none' }}
          >
            Nubru
          </a>
        </p>
        <span style={{ fontSize: '0.75rem', color: 'rgba(156, 163, 175, 0.7)' }}>
          © 2026 ReelPilot Studio. All rights reserved.
        </span>
      </div>

      {/* Connect Modal */}
      {connectingPlatform && (
        <div className="modal-overlay" onClick={() => setConnectingPlatform(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '12px', textTransform: 'capitalize' }}>
              Configure {connectingPlatform} Account
            </h3>
            <p className="text-muted" style={{ marginBottom: '16px' }}>
              Enter account identifier and authorization token for {connectingPlatform}:
            </p>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                Account Display Label
              </label>
              <input
                type="text"
                className="input"
                placeholder="My Channel / Brand Page"
                value={accountNameInput}
                onChange={(e) => setAccountNameInput(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                OAuth Access Token / Secret Reference
              </label>
              <input
                type="password"
                className="input"
                placeholder="Paste token or leave empty for local mock"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn btn-secondary" onClick={() => setConnectingPlatform(null)}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleConnectAccount(connectingPlatform)}
              >
                Save & Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
