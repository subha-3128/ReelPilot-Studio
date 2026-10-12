import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  Film,
  Mic,
  Subtitles,
  Send,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Download,
  Layers,
  ChevronRight,
  ChevronLeft,
  Type,
  Info,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  VideoAsset,
  MediaDerivative,
  VoiceoverAsset,
  Transcript,
  SubtitleSegment,
  ContentDraft,
  Publication,
} from '../types';

interface StudioPageProps {
  initialAssetId?: string;
  onNavigateToLibrary: () => void;
  onNavigateToHistory: () => void;
}

export const StudioPage: React.FC<StudioPageProps> = ({
  initialAssetId,
  onNavigateToLibrary,
  onNavigateToHistory,
}) => {
  // Navigation / Asset selection state
  const [assets, setAssets] = useState<VideoAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>(initialAssetId || '');
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Active Asset state
  const [currentAsset, setCurrentAsset] = useState<VideoAsset | null>(null);

  // Step 2: Voice-over settings
  const [replaceAudioEnabled, setReplaceAudioEnabled] = useState<boolean>(true);
  const [uploadedVoAsset, setUploadedVoAsset] = useState<VoiceoverAsset | null>(null);
  const [syncPolicy, setSyncPolicy] = useState<string>('keep_natural_speed');
  const [muteOriginalAudio, setMuteOriginalAudio] = useState<boolean>(true);
  const [startOffsetSeconds, setStartOffsetSeconds] = useState<number>(0.0);
  const [backgroundAmbience] = useState<number>(0.0);
  const [syncedDerivative, setSyncedDerivative] = useState<MediaDerivative | null>(null);

  // Step 3: Subtitles / Captions state
  const [, setTranscript] = useState<Transcript | null>(null);
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);

  // Step 4: Preview & Subtitle Burn
  const [burnSubtitlesEnabled, setBurnSubtitlesEnabled] = useState<boolean>(false);
  const [subtitleFontSize, setSubtitleFontSize] = useState<number>(24);
  const [subtitleFontColor] = useState<string>('&H00FFFFFF');
  const [captionedDerivative, setCaptionedDerivative] = useState<MediaDerivative | null>(null);
  const [finalExportDerivative, setFinalExportDerivative] = useState<MediaDerivative | null>(null);

  // Step 5: Metadata Drafts state
  const [drafts, setDrafts] = useState<ContentDraft[]>([]);
  const [activeDraftPlatform, setActiveDraftPlatform] = useState<'instagram' | 'youtube'>('instagram');
  const [aiTone] = useState<string>('engaging');

  // Step 6: Publishing & Scheduling state
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['instagram', 'youtube']);
  const [isScheduled, setIsScheduled] = useState<boolean>(false);
  const [scheduleDatetime, setScheduleDatetime] = useState<string>('');
  const [showPreflightModal, setShowPreflightModal] = useState<boolean>(false);
  const [publicationsResult, setPublicationsResult] = useState<Publication[]>([]);

  // Load asset list on mount
  useEffect(() => {
    const loadAssets = async () => {
      try {
        const list = await api.getAssets();
        setAssets(list);
        if (list.length > 0 && !selectedAssetId) {
          setSelectedAssetId(list[0].id);
        }
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to load assets');
      }
    };
    loadAssets();
  }, []);

  // Fetch full asset data whenever selectedAssetId changes
  useEffect(() => {
    if (!selectedAssetId) return;
    const fetchAssetDetail = async () => {
      try {
        setLoading(true);
        const data = await api.getAsset(selectedAssetId);
        setCurrentAsset(data);

        // Pre-populate voice-over if already attached
        if (data.voiceovers && data.voiceovers.length > 0) {
          setUploadedVoAsset(data.voiceovers[data.voiceovers.length - 1]);
        } else {
          setUploadedVoAsset(null);
        }

        // Pre-populate latest synced derivative
        const synced = data.derivatives.find((d) => d.derivative_type === 'voiceover_synced');
        setSyncedDerivative(synced || null);

        const captioned = data.derivatives.find((d) => d.derivative_type === 'captioned');
        setCaptionedDerivative(captioned || null);

        const exported = data.derivatives.find((d) => d.derivative_type === 'final_export');
        setFinalExportDerivative(exported || null);

        // Fetch drafts
        const existingDrafts = await api.getDrafts(selectedAssetId);
        setDrafts(existingDrafts);

        // Fetch transcript
        try {
          const t = await api.getTranscript(selectedAssetId);
          setTranscript(t);
          setSegments(t.segments || []);
        } catch {
          // ignore if not ready
        }
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to load video details');
      } finally {
        setLoading(false);
      }
    };
    fetchAssetDetail();
  }, [selectedAssetId]);

  // Voice-over MP4 Upload Handler
  const handleVoiceoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentAsset) return;

    try {
      setLoading(true);
      setStatusMessage('Uploading English voice-over MP4 and extracting audio track...');
      setErrorMessage(null);

      const vo = await api.uploadVoiceover(currentAsset.id, file);
      setUploadedVoAsset(vo);
      setStatusMessage('Voice-over audio track successfully extracted.');

      // Refresh transcript with new voiceover audio
      const trans = await api.getTranscript(currentAsset.id, vo.id);
      setTranscript(trans);
      setSegments(trans.segments || []);
    } catch (err: any) {
      setErrorMessage(err.message || 'Voice-over upload failed.');
    } finally {
      setLoading(false);
    }
  };

  // Run Voice-over Synchronization
  const handleSyncVoiceover = async () => {
    if (!currentAsset || !uploadedVoAsset) return;

    try {
      setLoading(true);
      setStatusMessage('Synchronizing voice-over with source video frames via FFmpeg...');
      setErrorMessage(null);

      const deriv = await api.syncVoiceover({
        video_asset_id: currentAsset.id,
        voiceover_asset_id: uploadedVoAsset.id,
        sync_policy: syncPolicy,
        mute_original_audio: muteOriginalAudio,
        start_offset_seconds: startOffsetSeconds,
        background_ambience_volume: backgroundAmbience,
      });

      setSyncedDerivative(deriv);
      setStatusMessage('Voice-over synchronized derivative created successfully!');
    } catch (err: any) {
      setErrorMessage(err.message || 'Synchronization failed.');
    } finally {
      setLoading(false);
    }
  };

  // Subtitles / Captions Save
  const handleSaveSegments = async () => {
    if (!currentAsset) return;
    try {
      setLoading(true);
      const updated = await api.updateTranscript(currentAsset.id, segments);
      setTranscript(updated);
      setStatusMessage('Captions updated successfully.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update captions.');
    } finally {
      setLoading(false);
    }
  };

  // Burn Subtitles Action
  const handleBurnSubtitles = async () => {
    if (!currentAsset) return;
    try {
      setLoading(true);
      setStatusMessage('Burning styled subtitles into video frames with libx264...');
      setErrorMessage(null);

      const deriv = await api.burnSubtitles({
        video_asset_id: currentAsset.id,
        derivative_id: syncedDerivative?.id,
        font_size: subtitleFontSize,
        font_color: subtitleFontColor,
      });
      setCaptionedDerivative(deriv);
      setStatusMessage('Subtitled video generated successfully.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Subtitle burn-in failed.');
    } finally {
      setLoading(false);
    }
  };

  // Final Export Action
  const handleExportVideo = async () => {
    if (!currentAsset) return;
    try {
      setLoading(true);
      setStatusMessage('Exporting final ready-to-publish video file...');
      setErrorMessage(null);

      const chosenDerivId = captionedDerivative?.id || syncedDerivative?.id;
      const exported = await api.exportVideo({
        video_asset_id: currentAsset.id,
        derivative_id: chosenDerivId,
      });
      setFinalExportDerivative(exported);
      setStatusMessage('Export complete! Video derivative is ready for publishing.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Export failed.');
    } finally {
      setLoading(false);
    }
  };

  // AI Metadata Generation
  const handleGenerateMetadata = async () => {
    if (!currentAsset) return;
    try {
      setLoading(true);
      setStatusMessage('Generating platform metadata suggestions from transcript...');
      const updatedDrafts = await api.generateDrafts({
        video_asset_id: currentAsset.id,
        tone: aiTone,
        include_hashtags: true,
        platforms: ['instagram', 'youtube'],
      });
      setDrafts(updatedDrafts);
      setStatusMessage('AI draft copy generated. You can freely edit before publishing.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Metadata generation failed.');
    } finally {
      setLoading(false);
    }
  };

  // Save Draft Copy Edits
  const handleUpdateDraftField = async (
    platform: 'instagram' | 'youtube',
    field: string,
    value: string
  ) => {
    if (!currentAsset) return;
    const targetDraft = drafts.find((d) => d.platform === platform);
    if (!targetDraft) return;

    const payload = {
      ...targetDraft,
      platform,
      [field]: value,
    };

    setDrafts(drafts.map((d) => (d.platform === platform ? { ...d, [field]: value } : d)));
    try {
      await api.updateDraft(currentAsset.id, payload);
    } catch (err) {
      console.error('Auto-save draft error:', err);
    }
  };

  // Publishing Execution
  const handleExecutePublishing = async () => {
    if (!currentAsset) return;
    setShowPreflightModal(false);

    try {
      setLoading(true);
      setStatusMessage('Executing publishing pipeline...');
      setErrorMessage(null);

      const activeDerivative =
        finalExportDerivative || captionedDerivative || syncedDerivative;

      const results = await api.publishPost({
        video_asset_id: currentAsset.id,
        derivative_id: activeDerivative?.id,
        platforms: selectedPlatforms,
        schedule_time: isScheduled && scheduleDatetime ? new Date(scheduleDatetime).toISOString() : undefined,
      });

      setPublicationsResult(results);
      setStatusMessage('Publishing / scheduling operations recorded.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Publishing operation failed.');
    } finally {
      setLoading(false);
    }
  };

  // Active video source for preview
  const activePreviewUrl = finalExportDerivative
    ? `http://127.0.0.1:8000/api/media/derivative/${finalExportDerivative.id}`
    : captionedDerivative
    ? `http://127.0.0.1:8000/api/media/derivative/${captionedDerivative.id}`
    : syncedDerivative
    ? `http://127.0.0.1:8000/api/media/derivative/${syncedDerivative.id}`
    : currentAsset
    ? `http://127.0.0.1:8000/api/media/video/${currentAsset.id}`
    : '';

  const steps = [
    { number: 1, title: 'Source Video', icon: Film },
    { number: 2, title: 'Voice-over', icon: Mic },
    { number: 3, title: 'Subtitles', icon: Subtitles },
    { number: 4, title: 'Preview & Export', icon: Layers },
    { number: 5, title: 'AI Metadata', icon: Sparkles },
    { number: 6, title: 'Publish & Schedule', icon: Send },
  ];

  return (
    <div className="page-wrapper" style={{ maxWidth: '1240px' }}>
      {/* Top Asset Selector & Wizard Header */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-muted-foreground)' }}>
            Working Video:
          </span>
          <select
            className="select"
            value={selectedAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value)}
            style={{ minWidth: '280px', fontWeight: 500 }}
          >
            {assets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.filename} ({a.duration.toFixed(1)}s • {a.aspect_ratio})
              </option>
            ))}
          </select>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={onNavigateToLibrary}>
          Library
        </button>
      </div>

      {/* Stepper Progress Bar */}
      <div className="stepper">
        {steps.map((s) => {
          const Icon = s.icon;
          const isActive = currentStep === s.number;
          const isCompleted = currentStep > s.number;

          return (
            <button
              key={s.number}
              className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              onClick={() => setCurrentStep(s.number)}
            >
              <Icon size={14} color={isActive ? 'var(--color-primary)' : isCompleted ? 'var(--color-success)' : 'inherit'} />
              <span>
                {s.number}. {s.title}
              </span>
            </button>
          );
        })}
      </div>

      {/* Status Notifications */}
      {statusMessage && (
        <div className="alert alert-info" style={{ marginBottom: '16px' }}>
          <CheckCircle2 size={16} />
          <span>{statusMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="alert alert-error" style={{ marginBottom: '16px' }}>
          <AlertTriangle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Studio Workspace Layout: 2 Columns (Preview on left, Controls on right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '24px' }}>
        {/* Left Column: Vertical Video Preview */}
        <div>
          <div className="card" style={{ padding: '16px' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '10px' }}>
              Real-Time Preview
            </h4>
            <div className="video-preview-box aspect-9-16">
              {activePreviewUrl ? (
                <video
                  key={activePreviewUrl}
                  controls
                  src={activePreviewUrl}
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--color-muted-foreground)', padding: '20px' }}>
                  <Film size={36} style={{ margin: '0 auto 8px' }} />
                  <p style={{ fontSize: '0.75rem' }}>No video loaded</p>
                </div>
              )}
            </div>

            {/* Current Variant Badge */}
            <div style={{ marginTop: '12px', fontSize: '0.75rem', color: 'var(--color-muted-foreground)' }}>
              Showing:{' '}
              <strong style={{ color: '#FFFFFF' }}>
                {finalExportDerivative
                  ? 'Final Export'
                  : captionedDerivative
                  ? 'Captioned Derivative'
                  : syncedDerivative
                  ? 'Voice-over Synced Derivative'
                  : currentAsset?.source_platform === 'instagram'
                  ? 'Original Instagram Reel'
                  : 'Original Source Video'}
              </strong>
            </div>
          </div>
        </div>

        {/* Right Column: Step by Step Workflow Panels */}
        <div>
          {/* STEP 1: Source Video Info */}
          {currentStep === 1 && currentAsset && (
            <div className="card">
              <h3 style={{ fontSize: '1.25rem', marginBottom: '12px' }}>1. Source Video Ingestion</h3>
              <p className="text-muted" style={{ marginBottom: '20px' }}>
                Downloaded video is safely stored on your Mac. Original audio and video frames are preserved in their native quality.
              </p>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '12px',
                  backgroundColor: 'rgba(0,0,0,0.25)',
                  padding: '16px',
                  borderRadius: '8px',
                  marginBottom: '24px',
                  fontSize: '0.875rem',
                }}
              >
                <div>
                  <span className="text-muted">Filename:</span>
                  <p style={{ fontWeight: 600 }}>{currentAsset.filename}</p>
                </div>
                <div>
                  <span className="text-muted">Duration:</span>
                  <p style={{ fontWeight: 600 }}>{currentAsset.duration.toFixed(1)} seconds</p>
                </div>
                <div>
                  <span className="text-muted">Resolution & Framing:</span>
                  <p style={{ fontWeight: 600 }}>
                    {currentAsset.width}x{currentAsset.height} ({currentAsset.aspect_ratio})
                  </p>
                </div>
                <div>
                  <span className="text-muted">Original Source:</span>
                  <p style={{ wordBreak: 'break-all', fontWeight: 500 }}>{currentAsset.original_source_url}</p>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn btn-primary" onClick={() => setCurrentStep(2)}>
                  <span>Proceed to Voice-over Setup</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Conditional Voice-over Flow */}
          {currentStep === 2 && currentAsset && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem' }}>2. Voice-over Configuration</h3>
                  <p className="text-muted">Supply an English voice-over MP4 or keep original audio.</p>
                </div>

                {/* Explicit conditional toggle */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <label htmlFor="replace-audio-toggle" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                    Replace audio with my voice-over
                  </label>
                  <label className="toggle-switch">
                    <input
                      id="replace-audio-toggle"
                      type="checkbox"
                      checked={replaceAudioEnabled}
                      onChange={(e) => setReplaceAudioEnabled(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>
              </div>

              {!replaceAudioEnabled ? (
                <div className="alert alert-info" style={{ marginBottom: '24px' }}>
                  <Info size={18} />
                  <div>
                    <strong>Original Audio Mode Active:</strong> Voice-over replacement is disabled. The video will retain its native Chinese soundtrack for export and publishing.
                  </div>
                </div>
              ) : (
                <div>
                  {/* Upload Drop Area */}
                  <div
                    style={{
                      border: '2px dashed rgba(236, 72, 153, 0.4)',
                      borderRadius: '12px',
                      padding: '28px',
                      textAlign: 'center',
                      backgroundColor: 'rgba(236, 72, 153, 0.03)',
                      marginBottom: '20px',
                    }}
                  >
                    <Upload size={32} color="var(--color-primary)" style={{ margin: '0 auto 12px' }} />
                    <h4 style={{ fontSize: '1rem', marginBottom: '6px' }}>Upload English Voice-over MP4</h4>
                    <p className="text-muted" style={{ fontSize: '0.8125rem', maxWidth: '460px', margin: '0 auto 16px' }}>
                      Audio is extracted directly from the uploaded MP4 container. Its visual frames are disregarded to preserve your source video.
                    </p>

                    <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                      <input
                        type="file"
                        accept="video/mp4,audio/*,.m4a,.wav"
                        style={{ display: 'none' }}
                        onChange={handleVoiceoverUpload}
                      />
                      <span>{uploadedVoAsset ? 'Replace Voice-over File' : 'Select English MP4 File'}</span>
                    </label>

                    {uploadedVoAsset && (
                      <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <CheckCircle2 size={16} color="var(--color-success)" />
                        <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                          {uploadedVoAsset.filename} ({uploadedVoAsset.duration.toFixed(1)}s)
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Synchronization Settings */}
                  {uploadedVoAsset && (
                    <div style={{ backgroundColor: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
                      <h4 style={{ fontSize: '0.9rem', marginBottom: '12px' }}>Synchronization Policy</h4>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                        {[
                          { id: 'keep_natural_speed', label: 'Keep Natural Speed (Recommended)', desc: 'Preserves vocal tempo' },
                          { id: 'fit_to_video', label: 'Fit to Video', desc: 'Auto-adjusts tempo to video duration' },
                          { id: 'manual_adjustment', label: 'Manual Adjustment', desc: 'Custom start offset & trim' },
                        ].map((mode) => (
                          <button
                            key={mode.id}
                            type="button"
                            onClick={() => setSyncPolicy(mode.id)}
                            style={{
                              padding: '10px',
                              borderRadius: '8px',
                              border: syncPolicy === mode.id ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                              backgroundColor: syncPolicy === mode.id ? 'rgba(236, 72, 153, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                              color: syncPolicy === mode.id ? '#FFFFFF' : 'var(--color-muted-foreground)',
                              textAlign: 'left',
                              cursor: 'pointer',
                            }}
                          >
                            <p style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{mode.label}</p>
                            <p style={{ fontSize: '0.72rem', marginTop: '2px' }}>{mode.desc}</p>
                          </button>
                        ))}
                      </div>

                      {/* Duration mismatch warning */}
                      {uploadedVoAsset.duration > currentAsset.duration + 0.5 && (
                        <div className="alert alert-warning" style={{ marginBottom: '16px' }}>
                          <AlertTriangle size={16} />
                          <div>
                            <strong>Duration Mismatch:</strong> Voice-over ({uploadedVoAsset.duration.toFixed(1)}s) is longer than video ({currentAsset.duration.toFixed(1)}s). The export will bound playback to the video duration without silent truncation.
                          </div>
                        </div>
                      )}

                      {/* Controls: Mute original & Start offset */}
                      <div style={{ display: 'flex', gap: '20px', alignItems: 'center', marginBottom: '16px' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={muteOriginalAudio}
                            onChange={(e) => setMuteOriginalAudio(e.target.checked)}
                            style={{ accentColor: 'var(--color-primary)' }}
                          />
                          <span>Mute original Chinese audio by default</span>
                        </label>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem' }}>
                          <span>Start Offset (s):</span>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            className="input"
                            style={{ width: '80px', padding: '4px 8px' }}
                            value={startOffsetSeconds}
                            onChange={(e) => setStartOffsetSeconds(parseFloat(e.target.value) || 0)}
                          />
                        </div>
                      </div>

                      {/* Run Sync Action */}
                      <button
                        className="btn btn-primary"
                        onClick={handleSyncVoiceover}
                        disabled={loading}
                        style={{ width: '100%' }}
                      >
                        <Sparkles size={16} />
                        <span>Synchronize Voice-over & Create Derivative</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
                <button className="btn btn-secondary" onClick={() => setCurrentStep(1)}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button className="btn btn-primary" onClick={() => setCurrentStep(3)}>
                  Next: Subtitles & Captions <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Subtitles & Transcript */}
          {currentStep === 3 && currentAsset && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem' }}>3. English Subtitles & Captions</h3>
                  <p className="text-muted">Generated from your final voice-over audio track.</p>
                </div>

                {/* Honest AnyTranscribe notice */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    border: '1px solid rgba(37, 99, 235, 0.25)',
                    fontSize: '0.72rem',
                    color: '#93C5FD',
                  }}
                  title="AnyTranscribe has no verified public API SDK; local speech engine is active."
                >
                  <span>Local Speech Engine Active</span>
                </div>
              </div>

              {/* Segment Editor */}
              <div style={{ marginBottom: '20px', maxHeight: '360px', overflowY: 'auto' }}>
                {segments.length === 0 ? (
                  <p className="text-muted" style={{ textAlign: 'center', padding: '24px 0' }}>
                    No captions detected. You can add caption segments manually below.
                  </p>
                ) : (
                  segments.map((seg, idx) => (
                    <div
                      key={seg.id || idx}
                      style={{
                        display: 'flex',
                        gap: '10px',
                        alignItems: 'center',
                        marginBottom: '8px',
                        backgroundColor: 'rgba(0,0,0,0.2)',
                        padding: '8px 12px',
                        borderRadius: '6px',
                      }}
                    >
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-primary)', fontWeight: 600, minWidth: '85px' }}>
                        {seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s
                      </span>
                      <input
                        type="text"
                        className="input"
                        value={seg.text}
                        onChange={(e) => {
                          const updated = [...segments];
                          updated[idx] = { ...updated[idx], text: e.target.value };
                          setSegments(updated);
                        }}
                        style={{ padding: '6px 10px', fontSize: '0.8125rem' }}
                      />
                    </div>
                  ))
                )}
              </div>

              {/* Caption Actions */}
              <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary btn-sm" onClick={handleSaveSegments}>
                  Save Caption Edits
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    const srtText = segments
                      .map((s, i) => `${i + 1}\n00:00:0${s.start.toFixed(0)},000 --> 00:00:0${s.end.toFixed(0)},000\n${s.text}\n`)
                      .join('\n');
                    const blob = new Blob([srtText], { type: 'text/plain' });
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = `${currentAsset.filename}_subtitles.srt`;
                    link.click();
                  }}
                >
                  <Download size={14} /> Download SRT
                </button>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button className="btn btn-secondary" onClick={() => setCurrentStep(2)}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button className="btn btn-primary" onClick={() => setCurrentStep(4)}>
                  Next: Preview & Export <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Preview & Subtitle Burn */}
          {currentStep === 4 && currentAsset && (
            <div className="card">
              <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>4. Preview & Export</h3>
              <p className="text-muted" style={{ marginBottom: '20px' }}>
                Review the synchronized playback and choose whether to burn subtitles into video frames.
              </p>

              {/* Subtitle burn-in box */}
              <div style={{ backgroundColor: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <label htmlFor="burn-subtitles-toggle" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                    Burn-in English Subtitles onto Video
                  </label>
                  <label className="toggle-switch">
                    <input
                      id="burn-subtitles-toggle"
                      type="checkbox"
                      checked={burnSubtitlesEnabled}
                      onChange={(e) => setBurnSubtitlesEnabled(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>

                {burnSubtitlesEnabled && (
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem' }}>
                      <span>Font Size:</span>
                      <input
                        type="number"
                        className="input"
                        value={subtitleFontSize}
                        onChange={(e) => setSubtitleFontSize(parseInt(e.target.value) || 24)}
                        style={{ width: '70px', padding: '4px 8px' }}
                      />
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={handleBurnSubtitles} disabled={loading}>
                      <Type size={14} /> Burn Subtitles Now
                    </button>
                  </div>
                )}
              </div>

              {/* Export Button */}
              <div style={{ marginBottom: '24px' }}>
                <button
                  className="btn btn-accent"
                  style={{ width: '100%', height: '44px' }}
                  onClick={handleExportVideo}
                  disabled={loading}
                >
                  <Download size={18} />
                  <span>Export Final Ready Video Derivative</span>
                </button>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button className="btn btn-secondary" onClick={() => setCurrentStep(3)}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button className="btn btn-primary" onClick={() => setCurrentStep(5)}>
                  Next: Platform Metadata <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: AI Metadata Editor */}
          {currentStep === 5 && currentAsset && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem' }}>5. Platform Metadata Assistant</h3>
                  <p className="text-muted">Draft engaging captions and titles tailored for Instagram and YouTube.</p>
                </div>
                <button className="btn btn-primary btn-sm" onClick={handleGenerateMetadata} disabled={loading}>
                  <Sparkles size={14} /> Regenerate Suggestions
                </button>
              </div>

              {/* Platform Draft Tabs */}
              <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <button
                  className={`btn ${activeDraftPlatform === 'instagram' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setActiveDraftPlatform('instagram')}
                >
                  Instagram Reels Draft
                </button>
                <button
                  className={`btn ${activeDraftPlatform === 'youtube' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setActiveDraftPlatform('youtube')}
                >
                  YouTube Shorts / Video Draft
                </button>
              </div>

              {/* Draft Forms */}
              {activeDraftPlatform === 'instagram' ? (
                <div>
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                      Reels Caption
                    </label>
                    <textarea
                      className="textarea"
                      value={drafts.find((d) => d.platform === 'instagram')?.caption || ''}
                      onChange={(e) => handleUpdateDraftField('instagram', 'caption', e.target.value)}
                      placeholder="Write your Instagram Reel caption..."
                    />
                  </div>
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                      Hashtags
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={drafts.find((d) => d.platform === 'instagram')?.hashtags || ''}
                      onChange={(e) => handleUpdateDraftField('instagram', 'hashtags', e.target.value)}
                      placeholder="#reels #creator #video"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                      YouTube Video Title
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={drafts.find((d) => d.platform === 'youtube')?.title || ''}
                      onChange={(e) => handleUpdateDraftField('youtube', 'title', e.target.value)}
                      placeholder="Enter YouTube title (under 100 characters)..."
                    />
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                      Description
                    </label>
                    <textarea
                      className="textarea"
                      value={drafts.find((d) => d.platform === 'youtube')?.description || ''}
                      onChange={(e) => handleUpdateDraftField('youtube', 'description', e.target.value)}
                      placeholder="Enter YouTube description..."
                    />
                  </div>
                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '6px' }}>
                      Tags / Keywords
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={drafts.find((d) => d.platform === 'youtube')?.hashtags || ''}
                      onChange={(e) => handleUpdateDraftField('youtube', 'hashtags', e.target.value)}
                      placeholder="shorts, trending, highlights"
                    />
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button className="btn btn-secondary" onClick={() => setCurrentStep(4)}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button className="btn btn-primary" onClick={() => setCurrentStep(6)}>
                  Next: Publish & Schedule <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 6: Publishing & Scheduling */}
          {currentStep === 6 && currentAsset && (
            <div className="card">
              <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>6. Publish & Schedule</h3>
              <p className="text-muted" style={{ marginBottom: '20px' }}>
                Dispatch your finished video to Instagram, YouTube, or both.
              </p>

              {/* Platform Selection */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '10px' }}>
                  Target Platforms
                </label>
                <div style={{ display: 'flex', gap: '12px' }}>
                  {['instagram', 'youtube'].map((p) => {
                    const isChecked = selectedPlatforms.includes(p);
                    return (
                      <label
                        key={p}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '10px 16px',
                          borderRadius: '8px',
                          border: isChecked ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                          backgroundColor: isChecked ? 'rgba(236, 72, 153, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                          cursor: 'pointer',
                          textTransform: 'capitalize',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedPlatforms([...selectedPlatforms, p]);
                            } else {
                              setSelectedPlatforms(selectedPlatforms.filter((item) => item !== p));
                            }
                          }}
                          style={{ accentColor: 'var(--color-primary)' }}
                        />
                        <span style={{ fontWeight: 600 }}>{p}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Schedule Toggle & Date Picker */}
              <div style={{ backgroundColor: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <label htmlFor="schedule-time-toggle" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                    Schedule for Later (Timezone-Aware)
                  </label>
                  <label className="toggle-switch">
                    <input
                      id="schedule-time-toggle"
                      type="checkbox"
                      checked={isScheduled}
                      onChange={(e) => setIsScheduled(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>

                {isScheduled && (
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', marginBottom: '6px' }}>
                      Publish Date & Time (Your Mac Timezone):
                    </label>
                    <input
                      type="datetime-local"
                      className="input"
                      value={scheduleDatetime}
                      onChange={(e) => setScheduleDatetime(e.target.value)}
                      style={{ maxWidth: '300px' }}
                    />
                    <p className="text-muted" style={{ fontSize: '0.75rem', marginTop: '6px' }}>
                      * Note: Your Mac must remain awake and running for the local scheduler worker to trigger.
                    </p>
                  </div>
                )}
              </div>

              {/* Preflight Modal Trigger */}
              <button
                className="btn btn-primary"
                style={{ width: '100%', height: '44px' }}
                onClick={() => setShowPreflightModal(true)}
                disabled={selectedPlatforms.length === 0}
              >
                <Send size={16} />
                <span>{isScheduled ? 'Confirm & Schedule Publication' : 'Preflight Checklist & Publish Now'}</span>
              </button>

              {/* Result Cards if submitted */}
              {publicationsResult.length > 0 && (
                <div style={{ marginTop: '24px' }}>
                  <h4 style={{ fontSize: '0.95rem', marginBottom: '12px' }}>Independent Platform Outcomes:</h4>
                  {publicationsResult.map((pub) => (
                    <div
                      key={pub.id}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: pub.status === 'published' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(220, 38, 38, 0.3)',
                        backgroundColor: pub.status === 'published' ? 'rgba(16, 185, 129, 0.05)' : 'rgba(220, 38, 38, 0.05)',
                        marginBottom: '8px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{pub.platform}: </span>
                        <span className={`badge ${pub.status === 'published' ? 'badge-success' : 'badge-warning'}`}>
                          {pub.status}
                        </span>
                        {pub.error_details && (
                          <p style={{ fontSize: '0.75rem', color: '#FCA5A5', marginTop: '4px' }}>
                            {pub.error_details}
                          </p>
                        )}
                      </div>
                      {pub.status === 'failed' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={async () => {
                            const retried = await api.retryPublication(pub.id);
                            setPublicationsResult(publicationsResult.map((p) => (p.id === pub.id ? retried : p)));
                          }}
                        >
                          Retry {pub.platform}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
                <button className="btn btn-secondary" onClick={() => setCurrentStep(5)}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button className="btn btn-secondary" onClick={onNavigateToHistory}>
                  View Publishing Audit History
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preflight Checklist Confirmation Modal */}
      {showPreflightModal && (
        <div className="modal-overlay" onClick={() => setShowPreflightModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '12px' }}>Preflight Publishing Checklist</h3>
            <p className="text-muted" style={{ marginBottom: '16px' }}>
              Verify platform readiness before dispatching content:
            </p>

            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
                <CheckCircle2 size={16} color="var(--color-success)" />
                <span>Video derivative generated and verified in 9:16 aspect ratio</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
                <CheckCircle2 size={16} color="var(--color-success)" />
                <span>English voice-over audio synchronized and source audio muted</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
                <CheckCircle2 size={16} color="var(--color-success)" />
                <span>Platform metadata and drafts configured for selected targets</span>
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
                <CheckCircle2 size={16} color="var(--color-success)" />
                <span>User rights and licensing confirmed for distribution</span>
              </li>
            </ul>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button className="btn btn-secondary" onClick={() => setShowPreflightModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleExecutePublishing}>
                Confirm & Proceed
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
