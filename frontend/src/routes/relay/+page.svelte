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
</script>

<h1>Relay Monitor</h1>

{#if loading}
  <p class="muted">Loading...</p>
{:else if error}
  <div class="error-banner">{error}</div>
{:else if status}
  <div class="cards">
    <div class="card">
      <div class="card-label">WhatsApp</div>
      <div class="card-value" class:connected={status.connected} class:disconnected={!status.connected}>
        {status.connected ? 'Connected' : 'Offline'}
      </div>
      <div class="card-sub">{status.mode || 'unknown'}</div>
    </div>
    <div class="card">
      <div class="card-label">Pipelines</div>
      <div class="card-value">{status.pipelines?.length || 0}</div>
      <div class="card-sub">active routes</div>
    </div>
  </div>

  {#if status.pipelines && status.pipelines.length > 0}
    <div class="section">
      <h2>Active Pipelines</h2>
      <div class="pipeline-list">
        {#each status.pipelines as p}
          <div class="pipeline-row" class:disabled={!p.enabled}>
            <span class="pipeline-name">{p.name}</span>
            <span class="badge" class:active={p.enabled}>{p.enabled ? 'Active' : 'Off'}</span>
            <span class="pipeline-sources">{p.source_group_ids?.length || 0} sources</span>
            <span class="pipeline-dests">{p.dest_group_ids?.length || 0} destinations</span>
          </div>
        {/each}
      </div>
      <p class="hint">Manage pipelines in the <a href="/pipelines">Pipelines</a> page.</p>
    </div>
  {/if}
{/if}

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
  .card-sub { font-size: 13px; color: #888; margin-top: 4px; }

  .section { margin-top: 24px; }
  .section h2 { font-size: 16px; margin: 0 0 12px; color: #aaa; }

  .pipeline-list { display: flex; flex-direction: column; gap: 8px; }
  .pipeline-row {
    background: #1a1a2e;
    border-radius: 6px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }
  .pipeline-row.disabled { opacity: 0.5; }
  .pipeline-name { font-weight: 600; color: #fff; }
  .pipeline-sources, .pipeline-dests { color: #888; font-size: 12px; }

  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #3e1a1a;
    color: #ef9a9a;
  }
  .badge.active { background: #1b5e20; color: #a5d6a7; }

  .hint { font-size: 12px; color: #666; margin-top: 12px; }
  .hint a { color: #4fc3f7; }

  .error-banner {
    background: #b71c1c;
    color: #fff;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
</style>
