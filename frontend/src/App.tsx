import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { LibraryPage } from './pages/LibraryPage';
import { StudioPage } from './pages/StudioPage';
import { CalendarPage } from './pages/CalendarPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedStudioAssetId, setSelectedStudioAssetId] = useState<string>('');

  const handleOpenInStudio = (assetId: string) => {
    setSelectedStudioAssetId(assetId);
    setCurrentTab('studio');
  };

  return (
    <div className="app-container">
      {/* Fixed Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
        }}
      />

      {/* Main Scrollable View */}
      <div className="main-content">
        <Header currentTab={currentTab} />

        <main style={{ flex: 1, paddingBottom: '60px' }}>
          {currentTab === 'dashboard' && (
            <DashboardPage
              onOpenInStudio={handleOpenInStudio}
              onOpenLibrary={() => setCurrentTab('library')}
            />
          )}

          {currentTab === 'library' && (
            <LibraryPage
              onOpenInStudio={handleOpenInStudio}
              onNavigateToDownload={() => setCurrentTab('dashboard')}
            />
          )}

          {currentTab === 'studio' && (
            <StudioPage
              key={selectedStudioAssetId}
              initialAssetId={selectedStudioAssetId}
              onNavigateToLibrary={() => setCurrentTab('library')}
              onNavigateToHistory={() => setCurrentTab('history')}
            />
          )}

          {currentTab === 'calendar' && <CalendarPage />}

          {currentTab === 'history' && <HistoryPage />}

          {currentTab === 'settings' && <SettingsPage />}
        </main>
      </div>
    </div>
  );
};

export default App;
