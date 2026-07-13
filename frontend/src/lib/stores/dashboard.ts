import { writable } from 'svelte/store';
import type { DashboardStatus } from '$lib/api';

export const status = writable<DashboardStatus>({
  whatsapp_status: 'disconnected',
  connected_number: null,
  products_today: 0,
  products_posted: 0,
  pending_queue: 0,
});

export const isLoading = writable(true);
