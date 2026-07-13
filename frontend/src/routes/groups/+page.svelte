<script lang="ts">
  import { onMount } from 'svelte';
  import { getGroups, syncGroups } from '$lib/api';
  import type { Group } from '$lib/api';

  let groups = $state<Group[]>([]);
  let search = $state('');
  let loading = $state(true);
  let syncing = $state(false);

  onMount(async () => {
    await loadGroups();
  });

  async function loadGroups() {
    loading = true;
    try {
      groups = await getGroups();
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  async function handleSearch() {
    loading = true;
    try {
      groups = await getGroups(search || undefined);
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  async function handleSync() {
    syncing = true;
    try {
      await syncGroups();
      await loadGroups();
    } catch (e) { console.error(e); }
    syncing = false;
  }
</script>

<h1>Groups</h1>

<div class="controls">
  <input
    type="text"
    placeholder="Search groups..."
    bind:value={search}
    oninput={handleSearch}
  />
  <button class="btn-sync" onclick={handleSync} disabled={syncing}>
    {syncing ? 'Syncing...' : '↻ Sync from WhatsApp'}
  </button>
</div>

{#if loading}
  <p class="muted">Loading...</p>
{:else if groups.length === 0}
  <p class="muted">No groups found. Sync WhatsApp first.</p>
{:else}
  <table>
    <thead>
      <tr>
        <th>Name</th>
        <th>Group ID</th>
        <th>Members</th>
        <th>Last Activity</th>
      </tr>
    </thead>
    <tbody>
      {#each groups as g}
        <tr>
          <td>{g.group_name}</td>
          <td class="mono">{g.group_id}</td>
          <td>{g.member_count}</td>
          <td>{g.last_activity || '—'}</td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  h1 { margin: 0 0 16px; }
  .muted { color: #666; }
  .controls { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; }
  .btn-sync {
    padding: 10px 20px;
    background: #4fc3f7;
    color: #000;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .btn-sync:disabled { opacity: 0.5; cursor: not-allowed; }
  input {
    width: 100%;
    max-width: 400px;
    padding: 10px 14px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 14px;
  }
  input:focus { outline: none; border-color: #4fc3f7; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }
  th, td {
    text-align: left;
    padding: 12px 16px;
    border-bottom: 1px solid #2a2a4e;
  }
  th { color: #888; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
  td { color: #ccc; }
  .mono { font-family: monospace; font-size: 12px; color: #888; }
</style>
