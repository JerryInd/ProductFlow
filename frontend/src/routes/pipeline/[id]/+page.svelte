<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { getPipeline, updatePipeline, getGroups } from '$lib/api';
  import type { Pipeline, Group } from '$lib/api';

  let pipeline = $state<Pipeline | null>(null);
  let groups = $state<Group[]>([]);
  let loading = $state(true);
  let saving = $state(false);

  let name = $state('');
  let enabled = $state(false);
  let pricingMode = $state('percentage');
  let pricingValue = $state(0);
  let autoPublish = $state(true);
  let promptTemplate = $state('');
  let selectedSources = $state<string[]>([]);
  let selectedDests = $state<string[]>([]);

  onMount(async () => {
    const id = Number($page.params.id);
    try {
      const [p, g] = await Promise.all([getPipeline(id), getGroups()]);
      pipeline = p;
      groups = g;
      name = p.name;
      enabled = !!p.enabled;
      pricingMode = p.pricing_mode;
      pricingValue = p.pricing_value;
      autoPublish = !!p.auto_publish;
      promptTemplate = p.prompt_template || '';
      selectedSources = p.sources.map(s => s.group_id);
      selectedDests = p.destinations.map(d => d.group_id);
    } catch (e) {
      console.error(e);
    }
    loading = false;
  });

  function toggleSource(gid: string) {
    selectedSources = selectedSources.includes(gid)
      ? selectedSources.filter(g => g !== gid)
      : [...selectedSources, gid];
  }
  function toggleDest(gid: string) {
    selectedDests = selectedDests.includes(gid)
      ? selectedDests.filter(g => g !== gid)
      : [...selectedDests, gid];
  }

  async function handleSave() {
    if (!pipeline) return;
    saving = true;
    try {
      await updatePipeline(pipeline.id, {
        name,
        enabled: enabled ? 1 : 0,
        pricing_mode: pricingMode,
        pricing_value: pricingValue,
        auto_publish: autoPublish ? 1 : 0,
        draft_mode: autoPublish ? 0 : 1,
        prompt_template: promptTemplate,
      } as any);
      goto('/pipelines');
    } catch (e) {
      console.error(e);
    }
    saving = false;
  }
</script>

{#if loading}
  <p class="muted">Loading...</p>
{:else if !pipeline}
  <p class="muted">Pipeline not found.</p>
{:else}
  <h1>Edit: {pipeline.name}</h1>

  <div class="form">
    <div class="field">
      <label>Pipeline Name</label>
      <input type="text" bind:value={name} />
    </div>

    <div class="field">
      <label>
        <input type="checkbox" bind:checked={enabled} /> Enabled
      </label>
    </div>

    <div class="field">
      <label>Pricing Mode</label>
      <select bind:value={pricingMode}>
        <option value="percentage">Percentage</option>
        <option value="fixed">Fixed Amount</option>
        <option value="tiered">Tiered</option>
      </select>
    </div>

    <div class="field">
      <label>Pricing Value</label>
      <input type="number" bind:value={pricingValue} />
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
      <textarea bind:value={promptTemplate} rows="5"></textarea>
    </div>

    <div class="field">
      <label>Source Groups</label>
      <div class="group-list">
        {#each groups as g}
          <label class="group-option">
            <input type="checkbox" checked={selectedSources.includes(g.group_id)} onchange={() => toggleSource(g.group_id)} />
            {g.group_name}
          </label>
        {/each}
      </div>
    </div>

    <div class="field">
      <label>Destination Groups</label>
      <div class="group-list">
        {#each groups as g}
          <label class="group-option">
            <input type="checkbox" checked={selectedDests.includes(g.group_id)} onchange={() => toggleDest(g.group_id)} />
            {g.group_name}
          </label>
        {/each}
      </div>
    </div>

    <button onclick={handleSave} disabled={saving || !name}>
      {saving ? 'Saving...' : 'Save Changes'}
    </button>
  </div>
{/if}

<style>
  .muted { color: #666; }
  h1 { margin: 0 0 24px; }
  .form { max-width: 600px; display: flex; flex-direction: column; gap: 20px; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 13px; color: #aaa; font-weight: 600; }
  input[type="text"], input[type="number"], select, textarea {
    padding: 10px 14px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 14px;
  }
  textarea { resize: vertical; font-family: inherit; }
  input:focus, select:focus, textarea:focus { outline: none; border-color: #4fc3f7; }
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
  .group-option { display: block; padding: 6px 8px; font-size: 13px; font-weight: 400; cursor: pointer; }
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
</style>
