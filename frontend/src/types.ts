export interface Artist {
  id: number;
  name: string;
  slug: string;
  bio?: string | null;
  is_archived: boolean;
}

export interface SetlistEntry {
  id: number;
  position: number;
  song_id: number;
  song_title: string;
  is_archived: boolean;
}

export interface Performance {
  id: number;
  artist_id: number;
  venue: string;
  city: string;
  performed_on: string;
  notes?: string | null;
  is_archived: boolean;
  attendance_count: number;
}

export interface PerformanceDetail extends Performance {
  setlist: SetlistEntry[];
}

export interface Revision {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  summary: string;
  actor_id: number | null;
  created_at: string;
}

export interface Attendance {
  performance_id: number;
  attending: boolean;
  attendance_count: number;
}

export interface Features {
  attendance: boolean;
  add_song: boolean;
  public_api: boolean;
}

export interface ApiError {
  code: string;
  message: string;
}
