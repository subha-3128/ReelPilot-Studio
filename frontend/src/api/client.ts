import type {
  VideoAsset,
  DownloadInspectResponse,
  MediaDerivative,
  VoiceoverAsset,
  Transcript,
  SubtitleSegment,
  ContentDraft,
  Publication,
  SocialAccount,
  AppSettings,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // --- Assets ---
  async getAssets(query?: string, filterStatus?: string): Promise<VideoAsset[]> {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (filterStatus) params.append('filter_status', filterStatus);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<VideoAsset[]>(`/assets${qs}`);
  },

  async getAsset(id: string): Promise<VideoAsset> {
    return request<VideoAsset>(`/assets/${id}`);
  },

  async inspectUrl(url: string): Promise<DownloadInspectResponse> {
    return request<DownloadInspectResponse>('/assets/inspect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, rights_acknowledged: true }),
    });
  },

  async downloadVideo(url: string, rightsAcknowledged: boolean = true): Promise<VideoAsset> {
    return request<VideoAsset>('/assets/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, rights_acknowledged: rightsAcknowledged }),
    });
  },

  async deleteAsset(id: string, deleteFiles: boolean = true): Promise<{ message: string }> {
    return request<{ message: string }>(`/assets/${id}?delete_files=${deleteFiles}`, {
      method: 'DELETE',
    });
  },

  async deleteDerivative(assetId: string, derivativeId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/assets/${assetId}/derivatives/${derivativeId}`, {
      method: 'DELETE',
    });
  },

  // --- Studio ---
  async uploadVoiceover(videoAssetId: string, file: File): Promise<VoiceoverAsset> {
    const formData = new FormData();
    formData.append('video_asset_id', videoAssetId);
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/studio/upload-voiceover`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload voiceover MP4');
    }
    return res.json();
  },

  async syncVoiceover(params: {
    video_asset_id: string;
    voiceover_asset_id: string;
    sync_policy: string;
    mute_original_audio: boolean;
    start_offset_seconds: number;
    audio_trim_seconds?: number;
    background_ambience_volume: number;
  }): Promise<MediaDerivative> {
    return request<MediaDerivative>('/studio/sync-voiceover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  async getTranscript(assetId: string, voiceoverId?: string): Promise<Transcript> {
    const qs = voiceoverId ? `?voiceover_id=${voiceoverId}` : '';
    return request<Transcript>(`/studio/${assetId}/transcript${qs}`);
  },

  async updateTranscript(assetId: string, segments: SubtitleSegment[]): Promise<Transcript> {
    return request<Transcript>(`/studio/${assetId}/transcript`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segments }),
    });
  },

  async burnSubtitles(params: {
    video_asset_id: string;
    derivative_id?: string;
    font_size?: number;
    font_color?: string;
  }): Promise<MediaDerivative> {
    return request<MediaDerivative>('/studio/burn-subtitles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  async exportVideo(params: { video_asset_id: string; derivative_id?: string }): Promise<MediaDerivative> {
    return request<MediaDerivative>('/studio/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  // --- Drafts ---
  async getDrafts(assetId: string): Promise<ContentDraft[]> {
    return request<ContentDraft[]>(`/drafts/${assetId}`);
  },

  async updateDraft(assetId: string, draft: Partial<ContentDraft> & { platform: string }): Promise<ContentDraft> {
    return request<ContentDraft>(`/drafts/${assetId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    });
  },

  async generateDrafts(params: {
    video_asset_id: string;
    tone?: string;
    include_hashtags?: boolean;
    platforms?: string[];
  }): Promise<ContentDraft[]> {
    return request<ContentDraft[]>('/drafts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  // --- Publishing ---
  async publishPost(params: {
    video_asset_id: string;
    derivative_id?: string;
    platforms: string[];
    schedule_time?: string;
  }): Promise<Publication[]> {
    return request<Publication[]>('/publications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },

  async getPublications(platform?: string, status?: string): Promise<Publication[]> {
    const params = new URLSearchParams();
    if (platform) params.append('platform', platform);
    if (status) params.append('status', status);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<Publication[]>(`/publications${qs}`);
  },

  async retryPublication(id: string): Promise<Publication> {
    return request<Publication>(`/publications/${id}/retry`, {
      method: 'POST',
    });
  },

  async cancelPublication(id: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/publications/${id}/cancel`, {
      method: 'DELETE',
    });
  },

  // --- Settings ---
  async getSettings(): Promise<AppSettings> {
    return request<AppSettings>('/settings');
  },

  async updateSettings(data: Partial<AppSettings>): Promise<{ message: string }> {
    return request<{ message: string }>('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  async getAccounts(): Promise<SocialAccount[]> {
    return request<SocialAccount[]>('/settings/accounts');
  },

  async connectAccount(data: { platform: string; access_token?: string; account_name?: string }): Promise<SocialAccount> {
    return request<SocialAccount>('/settings/accounts/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
};
