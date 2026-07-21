<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getRelayStatus, getRelayPipelines, createRelayPipeline,
    updateRelayPipeline, deleteRelayPipeline,
    type RelayStatus, type RelayPipeline
  } from '$lib/api';

  let status = $state<RelayStatus | null>(null);
  let pipelines = $state<RelayPipeline[]>([]);
  let error = $state('');
  let loading = $state(true);

  let editing = $state<RelayPipeline | null>(null);
  let showNew = $state(false);
  let saveMsg = $state('');
  let saving = $state(false);

  let formName = $state('');
  let formEnabled = $state(true);
  let formSources = $state('');
  let formDest = $state('');
  let formMarkup = $state(1000);

  onMount(async () => {
    await Promise.all([fetchStatus(), fetchPipelines()]);
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  });

  async function fetchStatus() {
    try { status = await getRelayStatus(); error = ''; }
    catch (e) { error = e instanceof Error ? e.message : 'Failed'; }
    finally { loading = false; }
  }

  async function fetchPipelines() {
    try { pipelines = await getRelayPipelines(); } catch {}
  }

  function startNew() {
    editing = null;
    showNew = true;
    formName = '';
    formEnabled = true;
    formSources = '';
    formDest = '';
    formMarkup = 1000;
  }

  function startEdit(p: RelayPipeline) {
    showNew = false;
    editing = p;
    formName = p.name;
    formEnabled = p.enabled;
    formSources = p.source_groups.join(', ');
    formDest = p.destination_group;
    formMarkup = p.markup;
  }

  function cancel() {
    showNew = false;
    editing = null;
  }

  async function save() {
    saving = true;
    saveMsg = '';
    const data = {
      name: formName,
      enabled: formEnabled,
      source_groups: formSources.split(',').map(s => s.trim()).filter(Boolean),
      destination_group: formDest.trim(),
      markup: formMarkup,
      prompt_file: 'prompt.txt',
    };
    try {
      if (editing) {
        await updateRelayPipeline(editing.id, data);
      } else {
        await createRelayPipeline(data);
      }
      await fetchPipelines();
      saveMsg = 'Saved!';
      showNew = false;
      editing = null;
      setTimeout(() => saveMsg = '', 2000);
    } catch (e) {
      saveMsg = 'Failed: ' + (e instanceof Error ? e.message : 'Unknown');
    } finally {
      saving = false;
    }
  }

  async function remove(id: number) {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await deleteRelayPipeline(id);
      await fetchPipelines();
    } catch {}
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
{/if}

<div class="section">
  <div class="section-header">
    <h2>Pipelines</h2>
    <button class="btn-new" onclick={startNew}>+ New Pipeline</button>
  </div>

  {#if saveMsg}
    <div class="save-banner" class:error={saveMsg.includes('Failed')}>{saveMsg}</div>
  {/if}

  {#if showNew || editing}
    <div class="form-card">
      <h3>{editing ? 'Edit Pipeline' : 'New Pipeline'}</h3>
      <div class="form-grid">
        <div class="form-row">
          <label>Name</label>
          <input type="text" bind:value={formName} placeholder="e.g. Watches Pipeline" />
        </div>
        <div class="form-row">
          <label>Enabled</label>
          <label class="toggle">
            <input type="checkbox" bind:checked={formEnabled} />
            <span class="slider"></span>
          </label>
        </div>
        <div class="form-row">
          <label>Source Groups</label>
          <input type="text" bind:value={formSources} placeholder="Rizwan WATCH, Rizwan Collection" />
          <span class="hint">Comma-separated group names</span>
        </div>
        <div class="form-row">
          <label>Destination Group</label>
          <input type="text" bind:value={formDest} placeholder="Perfect Deals" />
        </div>
        <div class="form-row">
          <label>Markup (₹)</label>
          <input type="number" bind:value={formMarkup} min="0" step="100" />
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-save" onclick={save} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        <button class="btn-cancel" onclick={cancel}>Cancel</button>
      </div>
    </div>
  {/if}

  {#if pipelines.length === 0}
    <p class="muted">No pipelines configured. Click "+ New Pipeline" to create one.</p>
  {:else}
    <div class="pipeline-list">
      {#each pipelines as p}
        <div class="pipeline-card" class:disabled={!p.enabled}>
          <div class="pipeline-header">
            <div>
              <strong>{p.name}</strong>
              <span class="badge" class:active={p.enabled}>{p.enabled ? 'Active' : 'Disabled'}</span>
            </div>
            <div class="pipeline-actions">
              <button class="btn-edit" onclick={() => startEdit(p)}>Edit</button>
              <button class="btn-delete" onclick={() => remove(p.id)}>Delete</button>
            </div>
          </div>
          <div class="pipeline-details">
            <div class="detail">
              <span class="detail-label">Sources</span>
              <div class="tags">
                {#each p.source_groups as g}
                  <span class="tag">{g}</span>
                {/each}
                {#if p.source_groups.length === 0}
                  <span class="muted">None</span>
                {/if}
              </div>
            </div>
            <div class="detail">
              <span class="detail-label">Destination</span>
              <span class="tag dest">{p.destination_group || 'None'}</span>
            </div>
            <div class="detail">
              <span class="detail-label">Markup</span>
              <span>₹{p.markup}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

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
  .section h2 { font-size: 16px; margin: 0; color: #aaa; }
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }

  .btn-new {
    background: #4fc3f7;
    color: #0f0f1a;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 13px;
  }
  .btn-new:hover { background: #81d4fa; }

  .save-banner {
    background: #1b5e20;
    color: #a5d6a7;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 12px;
    font-size: 13px;
  }
  .save-banner.error { background: #b71c1c; color: #ef9a9a; }

  .form-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .form-card h3 { margin: 0 0 16px; font-size: 16px; }
  .form-grid { display: flex; flex-direction: column; gap: 14px; }
  .form-row { display: flex; flex-direction: column; gap: 4px; }
  .form-row label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
  .form-row input[type="text"],
  .form-row input[type="number"] {
    background: #0f0f1a;
    border: 1px solid #2a2a4e;
    color: #e0e0e0;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
  }
  .form-row input:focus { outline: none; border-color: #4fc3f7; }
  .hint { font-size: 11px; color: #666; }
  .form-actions { display: flex; gap: 10px; margin-top: 16px; }
  .btn-save {
    background: #4fc3f7;
    color: #0f0f1a;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-cancel {
    background: transparent;
    color: #888;
    border: 1px solid #2a2a4e;
    padding: 8px 20px;
    border-radius: 6px;
    cursor: pointer;
  }

  .toggle { position: relative; display: inline-block; width: 44px; height: 24px; cursor: pointer; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider {
    position: absolute;
    inset: 0;
    background: #2a2a4e;
    border-radius: 24px;
    transition: 0.3s;
  }
  .slider::before {
    content: '';
    position: absolute;
    width: 18px;
    height: 18px;
    left: 3px;
    bottom: 3px;
    background: #fff;
    border-radius: 50%;
    transition: 0.3s;
  }
  .toggle input:checked + .slider { background: #4caf50; }
  .toggle input:checked + .slider::before { transform: translateX(20px); }

  .pipeline-list { display: flex; flex-direction: column; gap: 12px; }
  .pipeline-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 16px;
    border-left: 3px solid #4caf50;
  }
  .pipeline-card.disabled { border-left-color: #666; opacity: 0.7; }
  .pipeline-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .pipeline-header strong { font-size: 15px; }
  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
    background: #3e1a1a;
    color: #ef9a9a;
  }
  .badge.active { background: #1b5e20; color: #a5d6a7; }
  .pipeline-actions { display: flex; gap: 6px; }
  .btn-edit, .btn-delete {
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
  }
  .btn-edit { background: #2a2a4e; color: #4fc3f7; }
  .btn-delete { background: #3e1a1a; color: #ef9a9a; }

  .pipeline-details { display: flex; gap: 20px; flex-wrap: wrap; }
  .detail { display: flex; flex-direction: column; gap: 4px; }
  .detail-label { font-size: 11px; color: #666; text-transform: uppercase; }
  .tags { display: flex; flex-wrap: wrap; gap: 4px; }
  .tag {
    background: #2a2a4e;
    color: #4fc3f7;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
  }
  .tag.dest { background: #1b5e20; color: #a5d6a7; }

  .error-banner {
    background: #b71c1c;
    color: #fff;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
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
