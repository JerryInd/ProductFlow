<script lang="ts">
  import { onMount } from 'svelte';
  import { getRelayStatus, getRelayConfig, updateRelayConfig, type RelayStatus } from '$lib/api';

  let status = $state<RelayStatus | null>(null);
  let prompt = $state('');
  let markup = $state(1000);
  let error = $state('');
  let saveMsg = $state('');
  let saving = $state(false);
  let loading = $state(true);

  onMount(async () => {
    await Promise.all([fetchStatus(), fetchConfig()]);
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  });

  async function fetchStatus() {
    try {
      status = await getRelayStatus();
      error = '';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to fetch relay status';
    } finally {
      loading = false;
    }
  }

  async function fetchConfig() {
    try {
      const cfg = await getRelayConfig();
      prompt = cfg.prompt;
      markup = cfg.markup;
    } catch (e) {
      console.error('Failed to load config', e);
    }
  }

  async function saveConfig() {
    saving = true;
    saveMsg = '';
    try {
      await updateRelayConfig({ prompt, markup });
      saveMsg = 'Saved! New prompt takes effect on next message.';
      setTimeout(() => saveMsg = '', 3000);
    } catch (e) {
      saveMsg = 'Failed to save: ' + (e instanceof Error ? e.message : 'Unknown error');
    } finally {
      saving = false;
    }
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
      <div class="card-sub">Pending message recovery</div>
    </div>
    <div class="card">
      <div class="card-label">Processed</div>
      <div class="card-value">{status.processed_count}</div>
      <div class="card-sub">messages rewritten</div>
    </div>
    <div class="card">
      <div class="card-label">Last Scan</div>
      <div class="card-value">{timeAgo(status.last_scan)}</div>
      <div class="card-sub">live monitoring cycle</div>
    </div>
  </div>

  <div class="section">
    <h2>Configuration</h2>
    <div class="config-grid">
      <div class="config-item">
        <span class="config-label">Source Groups</span>
        <div class="tags">
          {#each status.source_groups as group}
            <span class="tag">{group}</span>
          {/each}
          {#if status.source_groups.length === 0}
            <span class="muted">None configured</span>
          {/if}
        </div>
      </div>
      <div class="config-item">
        <span class="config-label">Destination</span>
        <span class="tag dest">{status.destination_group || 'None'}</span>
      </div>
    </div>
  </div>

  {#if status.error}
    <div class="section">
      <h2>Error</h2>
      <div class="error-box">{status.error}</div>
    </div>
  {/if}
{/if}

<div class="section">
  <h2>AI Prompt</h2>
  <div class="prompt-card">
    <div class="prompt-header">
      <label class="config-label" for="markup">Markup (₹ added to price)</label>
      <input id="markup" type="number" bind:value={markup} class="markup-input" min="0" step="100" />
    </div>
    <textarea
      class="prompt-editor"
      bind:value={prompt}
      rows="18"
      placeholder="Enter the AI rewrite prompt..."
    ></textarea>
    <div class="prompt-footer">
      <button class="btn-save" onclick={saveConfig} disabled={saving}>
        {saving ? 'Saving...' : 'Save Prompt'}
      </button>
      {#if saveMsg}
        <span class="save-msg" class:error={saveMsg.includes('Failed')}>{saveMsg}</span>
      {/if}
    </div>
  </div>
</div>

<div class="section">
  <h2>How It Works</h2>
  <div class="info-grid">
    <div class="info-item">
      <div class="info-icon">📡</div>
      <div class="info-text">
        <strong>Capture</strong>
        <p>Reads messages from supplier groups via WhatsApp Web</p>
      </div>
    </div>
    <div class="info-item">
      <div class="info-icon">🤖</div>
      <div class="info-text">
        <strong>Rewrite</strong>
        <p>AI applies markup, removes links, adds footer</p>
      </div>
    </div>
    <div class="info-item">
      <div class="info-icon">📤</div>
      <div class="info-text">
        <strong>Forward</strong>
        <p>Posts rewritten captions to destination group</p>
      </div>
    </div>
    <div class="info-item">
      <div class="info-icon">🔄</div>
      <div class="info-text">
        <strong>Catch-up</strong>
        <p>On restart, processes all missed messages</p>
      </div>
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
  .card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 20px;
  }
  .card-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card-value { font-size: 28px; font-weight: 700; color: #fff; }
  .card-value.connected { color: #4caf50; }
  .card-value.disconnected { color: #f44336; }
  .card-value.active { color: #ff9800; }
  .card-sub { font-size: 13px; color: #888; margin-top: 4px; }

  .section { margin-top: 24px; }
  .section h2 { font-size: 16px; margin: 0 0 12px; color: #aaa; }

  .config-grid { display: flex; flex-direction: column; gap: 16px; }
  .config-item { background: #1a1a2e; border-radius: 8px; padding: 16px; }
  .config-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; display: block; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    background: #2a2a4e;
    color: #4fc3f7;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 13px;
  }
  .tag.dest { background: #1b5e20; color: #a5d6a7; }

  .prompt-card { background: #1a1a2e; border-radius: 8px; padding: 20px; }
  .prompt-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .prompt-header .config-label { margin-bottom: 0; }
  .markup-input {
    width: 100px;
    background: #2a2a4e;
    border: 1px solid #3a3a5e;
    color: #fff;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 14px;
  }
  .prompt-editor {
    width: 100%;
    background: #0f0f1a;
    border: 1px solid #2a2a4e;
    color: #e0e0e0;
    padding: 14px;
    border-radius: 6px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.6;
    resize: vertical;
  }
  .prompt-editor:focus { outline: none; border-color: #4fc3f7; }
  .prompt-footer { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
  .btn-save {
    background: #4fc3f7;
    color: #0f0f1a;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 14px;
  }
  .btn-save:hover { background: #81d4fa; }
  .btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
  .save-msg { font-size: 13px; color: #4caf50; }
  .save-msg.error { color: #f44336; }

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
    align-items: flex-start;
  }
  .info-icon { font-size: 24px; }
  .info-text strong { display: block; margin-bottom: 4px; }
  .info-text p { margin: 0; font-size: 13px; color: #888; }
</style>
