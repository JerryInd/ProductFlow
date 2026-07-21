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
  let formPrompt = $state('');

  const DEFAULT_PROMPT = `You are a WhatsApp product post editor.

MARKUP = {markup}

TASK

Edit the supplied WhatsApp product post by following these rules exactly.

RULES

1. Find the MAIN SELLING PRICE.
   The main selling price is usually:
   - The only product price in the post.
   - The price after words like Price, Rs, Rate, Available, Available@, Only.
   - The primary selling price of the product.

2. Ignore prices related to:
   - Shipping, OG Box, Indian Box, Accessories, Dust Cover, Invoice, Extra Charges, Any optional add-ons.

3. Extract only the numeric value of the main selling price.

4. Remove commas from the number if present.

5. Add MARKUP to the extracted price.

6. Replace ONLY the main selling price with the calculated price.

7. Preserve the original price format.

8. Remove every line that contains any of the following:
   - http, https, www, Place Orders, Product Direct Link, Order Here, Buy Now, Checkout, Cart, Store Link

9. Remove any empty blank lines created after deleting text.

10. Append this footer exactly:

━━━━━━━━━━━━━━
🔥 Perfect Deals 🔥
Premium Quality Products
📦 Pan India Shipping

WhatsApp:
+918169858589
https://chat.whatsapp.com/Khx2ym45DSy1AXfp3XtY86

Posted by |NotJerry|
━━━━━━━━━━━━━━

11. Do NOT change: Product title, Brand name, Description, Features, Specifications, Size, Quality, Emojis, Hashtags, Formatting, Existing line breaks.

12. Return ONLY the final edited WhatsApp post.`;

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
    formPrompt = DEFAULT_PROMPT.replace('{markup}', '1000');
  }

  function startEdit(p: RelayPipeline) {
    showNew = false;
    editing = p;
    formName = p.name;
    formEnabled = p.enabled;
    formSources = p.source_groups.join(', ');
    formDest = p.destination_group;
    formMarkup = p.markup;
    formPrompt = p.prompt || DEFAULT_PROMPT.replace('{markup}', String(p.markup));
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
      prompt: formPrompt,
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
          <label for="pname">Pipeline Name</label>
          <input id="pname" type="text" bind:value={formName} placeholder="e.g. Watches Pipeline" />
        </div>
        <div class="form-row">
          <label>Enabled</label>
          <label class="toggle">
            <input type="checkbox" bind:checked={formEnabled} />
            <span class="slider"></span>
          </label>
        </div>
        <div class="form-row">
          <label for="psrc">Source Groups</label>
          <input id="psrc" type="text" bind:value={formSources} placeholder="Rizwan WATCH, Asian Watch" />
          <span class="hint">Comma-separated group names</span>
        </div>
        <div class="form-row">
          <label for="pdst">Destination Group</label>
          <input id="pdst" type="text" bind:value={formDest} placeholder="Perfect Deals" />
        </div>
        <div class="form-row">
          <label for="pmarkup">Markup (₹)</label>
          <input id="pmarkup" type="number" bind:value={formMarkup} min="0" step="100" />
        </div>
        <div class="form-row full">
          <label for="pprompt">AI Prompt</label>
          <textarea id="pprompt" class="prompt-editor" bind:value={formPrompt} rows="16"></textarea>
          <span class="hint">Use {'{markup}'} as placeholder for the markup value</span>
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-save" onclick={save} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        <button class="btn-cancel" onclick={cancel}>Cancel</button>
      </div>
    </div>
  {/if}

  {#if pipelines.length === 0}
    <p class="muted">No pipelines yet. Click "+ New Pipeline" to create one.</p>
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
  .form-row.full { grid-column: 1 / -1; }
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
  .prompt-editor {
    width: 100%;
    background: #0f0f1a;
    border: 1px solid #2a2a4e;
    color: #e0e0e0;
    padding: 12px;
    border-radius: 6px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px;
    line-height: 1.5;
    resize: vertical;
  }
  .prompt-editor:focus { outline: none; border-color: #4fc3f7; }
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
</style>
