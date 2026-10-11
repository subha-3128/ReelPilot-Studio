export interface MediaDerivative {
  id: string;
  video_asset_id: string;
  derivative_type: 'voiceover_synced' | 'captioned' | 'final_export';
  local_path: string;
  thumbnail_path?: string;
  duration: number;
  width: number;
  height: number;
  file_size: number;
  checksum?: string;
  settings: Record<string, any>;
  created_at: string;
}

export interface VoiceoverAsset {
  id: string;
  video_asset_id: string;
  filename: string;
  duration: number;
  file_size: number;
  extracted_audio_path: string;
  created_at: string;
}

export interface VideoAsset {
  id: string;
  original_source_url: string;
  source_platform: string;
  filename: string;
  thumbnail_path?: string;
  duration: number;
  width: number;
  height: number;
  aspect_ratio: string;
  file_size: number;
  checksum?: string;
  has_audio: boolean;
  rights_notes: string;
  created_at: string;
  derivatives: MediaDerivative[];
  voiceovers: VoiceoverAsset[];
}

export interface DownloadInspectResponse {
  url: string;
  title?: string;
  thumbnail?: string;
  duration?: number;
  is_supported: boolean;
  duplicate_asset_id?: string;
  message?: string;
}

export interface SubtitleSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  id: string;
  video_asset_id: string;
  derivative_id?: string;
  provider: string;
  source_lang: string;
  target_lang: string;
  full_text: string;
  segments: SubtitleSegment[];
  created_at: string;
}

export interface ContentDraft {
  id: string;
  video_asset_id: string;
  platform: 'instagram' | 'youtube';
  title: string;
  caption: string;
  description: string;
  hashtags: string;
  language: string;
  generation_source: string;
  updated_at: string;
}

export interface Publication {
  id: string;
  video_asset_id: string;
  derivative_id?: string;
  platform: 'instagram' | 'youtube';
  scheduled_time?: string;
  status: 'draft' | 'scheduled' | 'publishing' | 'published' | 'failed';
  remote_post_id?: string;
  remote_post_url?: string;
  attempts: number;
  error_details?: string;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
}

export interface SocialAccount {
  id: string;
  platform: 'instagram' | 'youtube';
  account_identifier: string;
  account_name: string;
  connection_status: 'connected' | 'disconnected' | 'expired';
  scopes: string;
  updated_at: string;
}

export interface AppSettings {
  storage_dir: string;
  free_disk_space_gb: number;
  timezone: string;
  default_sync_policy: string;
  subtitle_font_size: number;
  subtitle_font_color: string;
  ffmpeg_available: boolean;
  ytdlp_available: boolean;
}
