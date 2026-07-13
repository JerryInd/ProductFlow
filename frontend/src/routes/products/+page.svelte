<script lang="ts">
  import { onMount } from 'svelte';
  import { getProducts, approveProduct, rejectProduct, type Product } from '$lib/api';

  let products = $state<Product[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let statusFilter = $state('');

  onMount(async () => {
    await loadProducts();
  });

  async function loadProducts() {
    loading = true;
    try {
      const resp = await getProducts({ status: statusFilter || undefined });
      products = resp.products;
      total = resp.total;
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  async function handleApprove(id: number) {
    try {
      await approveProduct(id);
      await loadProducts();
    } catch (e) { console.error(e); }
  }

  async function handleReject(id: number) {
    try {
      await rejectProduct(id);
      await loadProducts();
    } catch (e) { console.error(e); }
  }
</script>

<h1>Products</h1>

<div class="controls">
  <select bind:value={statusFilter} onchange={loadProducts}>
    <option value="">All Status</option>
    <option value="collected">Collected</option>
    <option value="approved">Approved</option>
    <option value="rejected">Rejected</option>
    <option value="posted">Posted</option>
  </select>
  <span class="total">{total} total</span>
</div>

{#if loading}
  <p class="muted">Loading...</p>
{:else if products.length === 0}
  <p class="muted">No products yet.</p>
{:else}
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Original</th>
        <th>Rewritten</th>
        <th>Price</th>
        <th>Profit</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each products as p}
        <tr>
          <td class="mono">{p.id}</td>
          <td class="caption-cell">{p.caption?.slice(0, 80)}...</td>
          <td class="caption-cell">{p.rewritten_caption?.slice(0, 80)}...</td>
          <td>
            {#if p.price_original}
              ₹{p.price_original} → ₹{p.price_new}
            {:else}
              —
            {/if}
          </td>
          <td>
            {#if p.price_original && p.price_new}
              <span class="profit">+₹{p.price_new - p.price_original}</span>
            {:else}
              —
            {/if}
          </td>
          <td><span class="status-badge" class:posted={p.status === 'posted'}>{p.status}</span></td>
          <td>
            {#if p.status === 'collected' || p.status === 'draft'}
              <button class="btn-approve" onclick={() => handleApprove(p.id)}>Approve</button>
              <button class="btn-reject" onclick={() => handleReject(p.id)}>Reject</button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  h1 { margin: 0 0 16px; }
  .muted { color: #666; }
  .controls { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; }
  select {
    padding: 8px 12px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 13px;
  }
  .total { font-size: 13px; color: #888; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #2a2a4e; }
  th { color: #888; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  td { color: #ccc; }
  .mono { font-family: monospace; font-size: 12px; color: #888; }
  .caption-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 11px;
    background: #333;
    color: #aaa;
  }
  .status-badge.posted { background: #1b5e20; color: #4caf50; }
  button {
    padding: 4px 12px;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }
  .btn-approve { background: #1b5e20; color: #4caf50; }
  .btn-reject { background: #4a1a1a; color: #f44336; }
  .profit { color: #4caf50; font-weight: 600; }
</style>
