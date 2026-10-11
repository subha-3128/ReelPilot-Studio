import React from 'react';
import {
  DownloadCloud,
  Film,
  Sparkles,
  Calendar,
  History,
  Settings as SettingsIcon,
  ShieldCheck,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  selectedAssetCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Add Video / URL', icon: DownloadCloud },
    { id: 'library', label: 'Video Library', icon: Film },
    { id: 'studio', label: 'Video Studio', icon: Sparkles },
    { id: 'calendar', label: 'Publishing Calendar', icon: Calendar },
    { id: 'history', label: 'Publishing History', icon: History },
    { id: 'settings', label: 'Settings & OAuth', icon: SettingsIcon },
  ];

  return (
    <aside
      style={{
        width: '260px',
        backgroundColor: '#111827',
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '24px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img
            src="/logo.svg"
            alt="Kuaishou Video Studio"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              boxShadow: '0 0 14px rgba(255, 94, 58, 0.35)',
              flexShrink: 0,
            }}
          />
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '-0.01em', background: 'linear-gradient(135deg, #FF5E3A 0%, #EC4899 50%, #A855F7 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Kuaishou Studio
            </h2>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-muted-foreground)' }}>
              Mac Local Engine
            </span>
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav style={{ flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '11px 14px',
                borderRadius: '8px',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#FFFFFF' : 'var(--color-muted-foreground)',
                backgroundColor: isActive ? 'rgba(236, 72, 153, 0.15)' : 'transparent',
                border: isActive ? '1px solid rgba(236, 72, 153, 0.3)' : '1px solid transparent',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 150ms ease',
              }}
            >
              <Icon
                size={18}
                color={isActive ? 'var(--color-primary)' : 'var(--color-muted-foreground)'}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* System Status Footer */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <ShieldCheck size={14} color="var(--color-success)" />
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-foreground)' }}>
            Local-First & Private
          </span>
        </div>
        <p style={{ fontSize: '0.72rem', color: 'var(--color-muted-foreground)', lineHeight: 1.3 }}>
          Media stored locally on Mac. Original videos never overwritten.
        </p>
      </div>
    </aside>
  );
};
