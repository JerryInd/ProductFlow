<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { createPipeline, getGroups, syncGroups } from '$lib/api';
  import type { Group } from '$lib/api';

  let name = $state('');
  let autoPublish = $state(true);
  let enabled = $state(true);
  let promptTemplate = $state('');
  let saving = $state(false);
  let syncing = $state(false);

  let groups = $state<Group[]>([]);
  let selectedSources = $state<string[]>([]);
  let selectedDests = $state<string[]>([]);
  let sourceSearch = $state('');
  let destSearch = $state('');

  let filteredSources = $derived(
    sourceSearch
      ? groups.filter(g => g.group_name.toLowerCase().includes(sourceSearch.toLowerCase()))
      : groups
  );
  let filteredDests = $derived(
    destSearch
      ? groups.filter(g => g.group_name.toLowerCase().includes(destSearch.toLowerCase()))
      : groups
  );

  onMount(async () => {
    await loadGroups();
  });

  async function loadGroups() {
    try {
      groups = await getGroups();
    } catch (e) { /* ignore */ }
  }

  async function handleSync() {
    syncing = true;
    try {
      await syncGroups();
      await loadGroups();
    } catch (e) { console.error(e); }
    syncing = false;
  }

  function toggleSource(gid: string) {
    if (selectedSources.includes(gid)) {
      selectedSources = selectedSources.filter(g => g !== gid);
    } else {
      selectedSources = [...selectedSources, gid];
    }
  }
  function toggleDest(gid: string) {
    if (selectedDests.includes(gid)) {
      selectedDests = selectedDests.filter(g => g !== gid);
    } else {
      selectedDests = [...selectedDests, gid];
    }
  }

  async function handleSave() {
    if (!name) return;
    saving = true;
    try {
      const p = await createPipeline({
        name,
        enabled: enabled ? 1 : 0,
        pricing_mode: 'ai',
        pricing_value: 0,
        auto_publish: autoPublish ? 1 : 0,
        draft_mode: autoPublish ? 0 : 1,
        prompt_template: promptTemplate,
        source_group_ids: selectedSources,
        destination_group_ids: selectedDests,
      });
      goto('/pipelines');
    } catch (e) {
      console.error(e);
    }
    saving = false;
  }
</script>

<h1>New Pipeline</h1>

<div class="form">
  <div class="field">
    <label>Pipeline Name</label>
    <input type="text" bind:value={name} placeholder="e.g. Luxury Bags" />
  </div>

  <div class="field">
    <label>Status</label>
    <div class="toggle-row">
      <button type="button" class="toggle" class:active={enabled} onclick={() => enabled = !enabled}>
        <span class="toggle-knob"></span>
      </button>
      <div class="toggle-info">
        <span class="toggle-label">{enabled ? 'Enabled' : 'Disabled'}</span>
        <span class="toggle-desc">
          {enabled
            ? 'Pipeline is active and processing messages'
            : 'Pipeline is paused — no messages will be processed'}
        </span>
      </div>
    </div>
  </div>

  <div class="field">
    <label>Approval Mode</label>
    <div class="toggle-row">
      <button type="button" class="toggle" class:active={autoPublish} onclick={() => autoPublish = !autoPublish}>
        <span class="toggle-knob"></span>
      </button>
      <div class="toggle-info">
        <span class="toggle-label">{autoPublish ? 'Auto Publish' : 'Manual Approval'}</span>
        <span class="toggle-desc">
          {autoPublish
            ? 'Products publish instantly to destination groups'
            : 'Products wait in the Products page for your approval before publishing'}
        </span>
      </div>
    </div>
  </div>

  <div class="field">
    <label>Prompt Template</label>
    <textarea bind:value={promptTemplate} rows="5" placeholder="Instructions for AI rewrite..."></textarea>
  </div>

  <div class="field">
    <div class="label-row">
      <label>Source Groups</label>
      <button class="btn-refresh" onclick={handleSync} disabled={syncing}>
        {syncing ? 'Syncing...' : '↻ Refresh'}
      </button>
    </div>
    <input type="text" class="search-input" placeholder="Search groups..." bind:value={sourceSearch} />
    <div class="group-list">
      {#if groups.length === 0}
        <p class="muted">No groups found. Click Refresh to sync from WhatsApp.</p>
      {/if}
      {#each filteredSources as g}
        <label class="group-option">
          <input type="checkbox" checked={selectedSources.includes(g.group_id)} onchange={() => toggleSource(g.group_id)} />
          {g.group_name} ({g.member_count})
        </label>
      {/each}
    </div>
  </div>

  <div class="field">
    <label>Destination Groups</label>
    <input type="text" class="search-input" placeholder="Search groups..." bind:value={destSearch} />
    <div class="group-list">
      {#each filteredDests as g}
        <label class="group-option">
          <input type="checkbox" checked={selectedDests.includes(g.group_id)} onchange={() => toggleDest(g.group_id)} />
          {g.group_name} ({g.member_count})
        </label>
      {/each}
    </div>
  </div>

  <button onclick={handleSave} disabled={saving || !name}>
    {saving ? 'Saving...' : 'Create Pipeline'}
  </button>
</div>

<style>
  h1 { margin: 0 0 24px; }
  .form { max-width: 600px; display: flex; flex-direction: column; gap: 20px; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 13px; color: #aaa; font-weight: 600; }
  input[type="text"], textarea {
    padding: 10px 14px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 14px;
  }
  textarea { resize: vertical; font-family: inherit; }
  input:focus, textarea:focus { outline: none; border-color: #4fc3f7; }
  input[type="checkbox"] { margin-right: 8px; }
  .toggle-row { display: flex; align-items: center; gap: 14px; }
  .toggle {
    width: 44px; height: 24px; border-radius: 12px;
    background: #333; border: none; cursor: pointer;
    position: relative; transition: background 0.2s; padding: 0;
    flex-shrink: 0;
  }
  .toggle.active { background: #4fc3f7; }
  .toggle-knob {
    width: 18px; height: 18px; border-radius: 50%;
    background: #fff; position: absolute; top: 3px; left: 3px;
    transition: transform 0.2s;
  }
  .toggle.active .toggle-knob { transform: translateX(20px); }
  .toggle-info { display: flex; flex-direction: column; gap: 2px; }
  .toggle-label { font-size: 14px; color: #e0e0e0; font-weight: 600; }
  .toggle-desc { font-size: 12px; color: #888; }
  .group-list {
    max-height: 200px;
    overflow-y: auto;
    background: #1a1a2e;
    border-radius: 6px;
    padding: 8px;
    border: 1px solid #333;
  }
  .group-option {
    display: block;
    padding: 6px 8px;
    font-size: 13px;
    font-weight: 400;
    cursor: pointer;
  }
  .group-option:hover { background: #2a2a4e; }
  button {
    padding: 12px 24px;
    background: #4fc3f7;
    color: #000;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .label-row { display: flex; justify-content: space-between; align-items: center; }
  .btn-refresh {
    padding: 4px 12px;
    background: #2a2a4e;
    color: #4fc3f7;
    border: 1px solid #4fc3f7;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }
  .btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }
  .muted { color: #666; font-size: 13px; padding: 8px; }
  .search-input {
    padding: 6px 10px;
    border: 1px solid #333;
    border-radius: 4px;
    background: #12122a;
    color: #e0e0e0;
    font-size: 12px;
    width: 100%;
  }
  .search-input:focus { outline: none; border-color: #4fc3f7; }
</style>
