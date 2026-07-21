<script lang="ts">
  import { onMount } from 'svelte';
  import { getRelayStatus, type RelayStatus } from '$lib/api';

  let status = $state<RelayStatus | null>(null);
  let error = $state('');
  let loading = $state(true);

  onMount(async () => {
    await fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  });

  async function fetchStatus() {
    try { status = await getRelayStatus(); error = ''; }
    catch (e) { error = e instanceof Error ? e.message : 'Failed'; }
    finally { loading = false; }
  }

  function timeAgo(ts: string | null): string {
    if (!ts) return '—';
    const diff = Date.now() - new Date(ts).getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return `${Math.floor(diff / 86400000)}d ago`;
  }
</script>

<h1>Relay Monitor</h1>

{#if loading}
  <p class="muted">Loading...</p>
{:else if error}
  <div class="error-banner">{error}</div>
{:else if status}
  <div class="cards">
    <div class="card">
      <div class="card-label">Status</div>
      <div class="card-value" class:connected={status.connected} class:disconnected={!status.connected}>
        {status.connected ? 'Connected' : 'Offline'}
      </div>
      <div class="card-sub">{status.mode || 'unknown'}</div>
    </div>
    <div class="card">
      <div class="card-label">Catch-up</div>
      <div class="card-value" class:active={status.catching_up}>
        {status.catching_up ? 'In Progress' : 'Done'}
      </div>
    </div>
    <div class="card">
      <div class="card-label">Processed</div>
      <div class="card-value">{status.processed_count}</div>
      <div class="card-sub">messages rewritten</div>
    </div>
    <div class="card">
      <div class="card-label">Last Scan</div>
      <div class="card-value">{timeAgo(status.last_scan)}</div>
    </div>
  </div>

  {#if status.pipelines?.length}
    <div class="section">
      <h2>Pipelines</h2>
      <div class="pipeline-list">
        {#each status.pipelines as p}
          <div class="pipeline-card" class:disabled={!p.enabled}>
            <strong>{p.name}</strong>
            <span class="badge" class:active={p.enabled}>{p.enabled ? 'Active' : 'Off'}</span>
            <span class="detail">→ {p.destination_group || 'No dest'}</span>
            <span class="detail">₹{p.markup}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if status.error}
    <div class="section">
      <h2>Error</h2>
      <div class="error-box">{status.error}</div>
    </div>
  {/if}
{/if}

<div class="section">
  <h2>How It Works</h2>
  <div class="info-grid">
    <div class="info-item">
      <div class="info-icon">📡</div>
      <div class="info-text"><strong>Capture</strong><p>Reads messages from supplier groups via WhatsApp Web</p></div>
    </div>
    <div class="info-item">
      <div class="info-icon">🤖</div>
      <div class="info-text"><strong>Rewrite</strong><p>AI applies markup, removes links, adds footer</p></div>
    </div>
    <div class="info-item">
      <div class="info-icon">📤</div>
      <div class="info-text"><strong>Forward</strong><p>Posts rewritten captions to destination group</p></div>
    </div>
    <div class="info-item">
      <div class="info-icon">🔄</div>
      <div class="info-text"><strong>Catch-up</strong><p>On restart, processes all missed messages</p></div>
    </div>
  </div>
</div>

<style>
  h1 { margin: 0 0 24px; font-size: 24px; }
  .muted { color: #666; }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }
  .card { background: #1a1a2e; border-radius: 8px; padding: 20px; }
  .card-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card-value { font-size: 28px; font-weight: 700; color: #fff; }
  .card-value.connected { color: #4caf50; }
  .card-value.disconnected { color: #f44336; }
  .card-value.active { color: #ff9800; }
  .card-sub { font-size: 13px; color: #888; margin-top: 4px; }

  .section { margin-top: 24px; }
  .section h2 { font-size: 16px; margin: 0 0 12px; color: #aaa; }

  .pipeline-list { display: flex; flex-direction: column; gap: 8px; }
  .pipeline-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-left: 3px solid #4caf50;
  }
  .pipeline-card.disabled { border-left-color: #666; opacity: 0.6; }
  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #3e1a1a;
    color: #ef9a9a;
  }
  .badge.active { background: #1b5e20; color: #a5d6a7; }
  .detail { font-size: 13px; color: #888; }

  .error-banner {
    background: #b71c1c;
    color: #fff;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
  .error-box {
    background: #3e1a1a;
    color: #ef9a9a;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .info-item {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 16px;
    display: flex;
    gap: 12px;
  }
  .info-icon { font-size: 24px; }
  .info-text strong { display: block; margin-bottom: 4px; }
  .info-text p { margin: 0; font-size: 13px; color: #888; }
</style>
