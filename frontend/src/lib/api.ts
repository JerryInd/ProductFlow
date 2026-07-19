const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export interface DashboardStatus {
  whatsapp_status: string;
  connected_number: string | null;
  products_today: number;
  products_posted: number;
  pending_queue: number;
}

export interface WhatsAppSession {
  status: string;
  phone_number: string | null;
}

export interface Group {
  id: number;
  group_id: string;
  group_name: string;
  member_count: number;
  last_activity: string | null;
  role: string;
}

export interface Pipeline {
  id: number;
  name: string;
  enabled: number;
  prompt_template: string;
  pricing_mode: string;
  pricing_value: number;
  pricing_tiers: string | null;
  collector_window_seconds: number;
  auto_publish: number;
  draft_mode: number;
  sources: { group_id: string }[];
  destinations: { group_id: string }[];
  created_at: string;
}

export interface Product {
  id: number;
  pipeline_id: number | null;
  source_group_id: string | null;
  caption: string;
  rewritten_caption: string;
  media_paths: string;
  video_paths: string;
  price_original: number | null;
  price_new: number | null;
  hash: string;
  status: string;
  created_at: string;
  queue_status?: string;
}

export interface ProductsResponse {
  products: Product[];
  total: number;
}

// Dashboard
export const getStatus = () => request<DashboardStatus>('/home/status');

// WhatsApp
export const getWhatsAppStatus = () => request<WhatsAppSession>('/whatsapp/status');
export const getQR = () => request<{ qr: string }>('/whatsapp/qr');
export const connectWA = () => request<{ message: string }>('/whatsapp/connect', { method: 'POST' });
export const disconnectWA = () => request<{ message: string }>('/whatsapp/disconnect', { method: 'POST' });

// Groups
export const getGroups = (search?: string) =>
  request<Group[]>(`/groups/${search ? `?search=${encodeURIComponent(search)}` : ''}`);
export const getGroup = (id: string) => request<Group>(`/groups/${id}`);
export const syncGroups = () =>
  request<{ message: string; synced: number }>('/groups/sync', { method: 'POST' });

// Pipelines
export const getPipelines = () => request<Pipeline[]>('/pipelines/');
export const getPipeline = (id: number) => request<Pipeline>(`/pipelines/${id}`);
export const createPipeline = (data: { name: string; enabled: number; pricing_mode: string; pricing_value: number; auto_publish: number; draft_mode: number; prompt_template: string; source_group_ids: string[]; destination_group_ids: string[] }) =>
  request<Pipeline>('/pipelines/', { method: 'POST', body: JSON.stringify(data) });
export const updatePipeline = (id: number, data: Partial<Pipeline> & { source_group_ids?: string[]; destination_group_ids?: string[] }) =>
  request<{ message: string }>(`/pipelines/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deletePipeline = (id: number) =>
  request<{ message: string }>(`/pipelines/${id}`, { method: 'DELETE' });

// Products
export const getProducts = (params?: { status?: string; pipeline_id?: number; limit?: number; offset?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set('status', params.status);
  if (params?.pipeline_id) q.set('pipeline_id', String(params.pipeline_id));
  if (params?.limit) q.set('limit', String(params.limit));
  if (params?.offset) q.set('offset', String(params.offset));
  const qs = q.toString();
  return request<ProductsResponse>(`/products/${qs ? `?${qs}` : ''}`);
};
export const approveProduct = (id: number) =>
  request<{ message: string }>(`/products/${id}/approve`, { method: 'POST' });
export const rejectProduct = (id: number) =>
  request<{ message: string }>(`/products/${id}/reject`, { method: 'POST' });

// WhatsApp Chats & Forward
export interface Chat {
  jid: string;
  name: string;
  lastMessage: string;
  timestamp: number;
}
export const getWhatsAppChats = () =>
  request<{ chats: Chat[] }>('/whatsapp/chats');
export const forwardProducts = (product_ids: number[], recipient: string) =>
  request<{ sent: number; failed: number; errors: string[] }>('/whatsapp/forward', {
    method: 'POST',
    body: JSON.stringify({ product_ids, recipient }),
  });

// Unified Chats & Forward
export interface PlatformChat {
  jid: string;
  name: string;
  platform: 'whatsapp';
}
export const getChats = () =>
  request<{ chats: PlatformChat[] }>('/chats');
export const forwardToPlatforms = (product_ids: number[], recipients: { platform: string; jid: string }[]) =>
  request<{ sent: number; failed: number; errors: string[] }>('/forward', {
    method: 'POST',
    body: JSON.stringify({ product_ids, recipients }),
  });
