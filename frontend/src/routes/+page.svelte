<script lang="ts">
  import { onMount } from 'svelte';
  import { status, isLoading } from '$lib/stores/dashboard';
  import { getStatus } from '$lib/api';

  onMount(async () => {
    try {
      const data = await getStatus();
      $status = data;
    } catch (e) {
      console.error('Failed to load status', e);
    } finally {
      $isLoading = false;
    }
  });
</script>

<h1>Dashboard</h1>

{#if $isLoading}
  <p class="muted">Loading...</p>
{:else}
  <div class="cards">
    <div class="card">
      <div class="card-label">WhatsApp</div>
      <div class="card-value" class:connected={$status.whatsapp_status === 'connected'}>
        {$status.whatsapp_status === 'connected' ? 'Connected' : 'Disconnected'}
      </div>
      <div class="card-sub">{$status.connected_number || '—'}</div>
    </div>
    <div class="card">
      <div class="card-label">Products Today</div>
      <div class="card-value">{$status.products_today}</div>
      <div class="card-sub">{$status.products_posted} posted</div>
    </div>
    <div class="card">
      <div class="card-label">Pending Queue</div>
      <div class="card-value">{$status.pending_queue}</div>
      <div class="card-sub">Awaiting publish</div>
    </div>
  </div>

  <div class="section">
    <h2>System</h2>
    <div class="sys-grid">
      <div class="sys-item">
        <span class="sys-label">CPU</span>
        <div class="bar"><div class="bar-fill" style="width: 30%"></div></div>
      </div>
      <div class="sys-item">
        <span class="sys-label">RAM</span>
        <div class="bar"><div class="bar-fill" style="width: 65%"></div></div>
      </div>
      <div class="sys-item">
        <span class="sys-label">Storage</span>
        <div class="bar"><div class="bar-fill" style="width: 40%"></div></div>
      </div>
    </div>
  </div>
{/if}

<style>
  h1 { margin: 0 0 24px; font-size: 24px; }
  .muted { color: #666; }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }
  .card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 20px;
  }
  .card-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card-value { font-size: 28px; font-weight: 700; color: #fff; }
  .card-value.connected { color: #4caf50; }
  .card-sub { font-size: 13px; color: #888; margin-top: 4px; }
  .section { margin-top: 24px; }
  .section h2 { font-size: 16px; margin: 0 0 12px; color: #aaa; }
  .sys-grid { display: flex; flex-direction: column; gap: 12px; }
  .sys-item { display: flex; align-items: center; gap: 12px; }
  .sys-label { width: 60px; font-size: 13px; color: #aaa; }
  .bar { flex: 1; height: 8px; background: #2a2a4e; border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; background: #4fc3f7; border-radius: 4px; }
</style>
