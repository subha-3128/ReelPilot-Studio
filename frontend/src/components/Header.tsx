import React, { useEffect, useState } from 'react';
import { HardDrive, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { AppSettings } from '../types';

interface HeaderProps {
  currentTab: string;
}

export const Header: React.FC<HeaderProps> = ({ currentTab }) => {
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);

  const tabTitles: Record<string, { title: string; subtitle: string }> = {
    dashboard: {
      title: 'Download & Inspect Video',
      subtitle: 'Paste any authorized Instagram Reel, Kuaishou, or Kwai video URL to process',
    },
    library: {
      title: 'Video Library',
      subtitle: 'Browse downloaded assets, voice-over status, and processed derivatives',
    },
    studio: {
      title: 'Video Studio Workflow',
      subtitle: 'Synchronize English voice-over MP4, generate subtitles, and export derivatives',
    },
    calendar: {
      title: 'Publishing Calendar',
      subtitle: 'Review and manage scheduled posts across Instagram and YouTube',
    },
    history: {
      title: 'Publishing History & Audit',
      subtitle: 'Independent per-platform tracking and single-platform retries',
    },
    settings: {
      title: 'Settings & Integrations',
      subtitle: 'Configure local storage, video policies, and social accounts',
    },
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/health');
        setIsBackendHealthy(res.ok);
      } catch {
        setIsBackendHealthy(false);
      }

      try {
        const appSet = await api.getSettings();
        setSettings(appSet);
      } catch {
        // ignore
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const meta = tabTitles[currentTab] || { title: 'Studio', subtitle: '' };

  return (
    <header
      style={{
        padding: '18px 32px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        backgroundColor: 'rgba(17, 24, 39, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <img
          src="/logo.svg"
          alt="ReelPilot Logo"
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            boxShadow: '0 0 16px rgba(236, 72, 153, 0.35)',
            flexShrink: 0,
          }}
        />
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600 }}>{meta.title}</h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted-foreground)', marginTop: '2px' }}>
            {meta.subtitle}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Storage disk info */}
        {settings && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              fontSize: '0.75rem',
            }}
          >
            <HardDrive size={14} color="var(--color-muted-foreground)" />
            <span style={{ color: 'var(--color-muted-foreground)' }}>Mac Disk:</span>
            <span style={{ fontWeight: 600, color: '#FFFFFF' }}>
              {settings.free_disk_space_gb} GB Free
            </span>
          </div>
        )}

        {/* Backend health indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            backgroundColor:
              isBackendHealthy === true
                ? 'rgba(16, 185, 129, 0.1)'
                : isBackendHealthy === false
                ? 'rgba(220, 38, 38, 0.1)'
                : 'rgba(255, 255, 255, 0.04)',
            border: `1px solid ${
              isBackendHealthy === true
                ? 'rgba(16, 185, 129, 0.3)'
                : isBackendHealthy === false
                ? 'rgba(220, 38, 38, 0.3)'
                : 'rgba(255, 255, 255, 0.08)'
            }`,
            borderRadius: '8px',
            fontSize: '0.75rem',
          }}
        >
          {isBackendHealthy === true ? (
            <>
              <CheckCircle2 size={13} color="var(--color-success)" />
              <span style={{ color: '#34D399', fontWeight: 500 }}>Backend Online (127.0.0.1)</span>
            </>
          ) : isBackendHealthy === false ? (
            <>
              <AlertCircle size={13} color="var(--color-destructive)" />
              <span style={{ color: '#F87171', fontWeight: 500 }}>Backend Offline</span>
            </>
          ) : (
            <>
              <Activity size={13} color="var(--color-muted-foreground)" />
              <span style={{ color: 'var(--color-muted-foreground)' }}>Connecting...</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
