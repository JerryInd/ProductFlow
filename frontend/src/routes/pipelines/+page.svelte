<script lang="ts">
  import { onMount } from 'svelte';
  import { getPipelines, deletePipeline, type Pipeline } from '$lib/api';

  let pipelines = $state<Pipeline[]>([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      pipelines = await getPipelines();
    } catch (e) {
      console.error(e);
    }
    loading = false;
  });

  async function handleDelete(id: number) {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await deletePipeline(id);
      pipelines = pipelines.filter(p => p.id !== id);
    } catch (e) {
      console.error(e);
    }
  }
</script>

<h1>Pipelines</h1>

<div class="controls">
  <a href="/pipelines/new" class="btn">+ New Pipeline</a>
</div>

{#if loading}
  <p class="muted">Loading...</p>
{:else if pipelines.length === 0}
  <p class="muted">No pipelines yet. Create one to start.</p>
{:else}
  <div class="pipeline-list">
    {#each pipelines as p}
      <div class="pipeline-card">
        <div class="card-header">
          <span class="name">{p.name}</span>
          <span class="toggle" class:active={p.enabled}>{p.enabled ? 'Enabled' : 'Disabled'}</span>
        </div>
        <div class="card-details">
          <div class="detail">
            <span class="label">Sources</span>
            <span>{p.sources.length} groups</span>
          </div>
          <div class="detail">
            <span class="label">Destinations</span>
            <span>{p.destinations.length} groups</span>
          </div>
          <div class="detail">
            <span class="label">Pricing</span>
            <span>{p.pricing_mode} {p.pricing_value}{p.pricing_mode === 'percentage' ? '%' : ''}</span>
          </div>
          <div class="detail">
            <span class="label">Auto Publish</span>
            <span>{p.auto_publish ? 'Yes' : 'No'}</span>
          </div>
        </div>
        <div class="card-actions">
          <a href="/pipeline/{p.id}" class="btn-sm">Edit</a>
          <button class="btn-sm danger" onclick={() => handleDelete(p.id)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  h1 { margin: 0 0 16px; }
  .muted { color: #666; }
  .controls { margin-bottom: 20px; }
  .btn {
    display: inline-block;
    padding: 10px 24px;
    background: #4fc3f7;
    color: #000;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
    border: none;
    cursor: pointer;
    text-decoration: none;
  }
  .pipeline-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }
  .pipeline-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 20px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .name { font-size: 16px; font-weight: 600; color: #fff; }
  .toggle {
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 12px;
    background: #333;
    color: #888;
  }
  .toggle.active { background: #1b5e20; color: #4caf50; }
  .card-details { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
  .detail { display: flex; justify-content: space-between; font-size: 13px; }
  .label { color: #888; }
  .card-actions { display: flex; gap: 8px; }
  .btn-sm {
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 13px;
    background: #2a2a4e;
    color: #ccc;
    border: none;
    cursor: pointer;
    text-decoration: none;
  }
  .btn-sm.danger { background: #4a1a1a; color: #f44336; }
</style>
