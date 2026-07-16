<script lang="ts">
  import { onMount } from 'svelte';
  import { getProducts, approveProduct, rejectProduct, type Product } from '$lib/api';

  let products = $state<Product[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let statusFilter = $state('');
  let expandedId = $state<number | null>(null);

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

  function toggleExpand(id: number) {
    expandedId = expandedId === id ? null : id;
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

  function parseMediaPaths(paths: string | null): string[] {
    if (!paths) return [];
    try { return JSON.parse(paths); } catch { return []; }
  }

  function formatTime(ts: string | null): string {
    if (!ts) return '—';
    return new Date(ts).toLocaleString();
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
        <th class="col-expand"></th>
        <th>ID</th>
        <th>Original</th>
        <th>Rewritten</th>
        <th class="col-price">Captured</th>
        <th class="col-price">Profit</th>
        <th class="col-price">Selling</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each products as p (p.id)}
        <tr class="main-row" class:expanded={expandedId === p.id}>
          <td class="col-expand">
            <button class="expand-btn" class:open={expandedId === p.id} onclick={() => toggleExpand(p.id)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>
          </td>
          <td class="mono">{p.id}</td>
          <td class="caption-cell">{p.caption?.slice(0, 80)}{p.caption && p.caption.length > 80 ? '...' : ''}</td>
          <td class="caption-cell">{p.rewritten_caption?.slice(0, 80)}{p.rewritten_caption && p.rewritten_caption.length > 80 ? '...' : ''}</td>
          <td class="col-price">
            {#if p.price_original}
              <span class="price-captured">₹{p.price_original}</span>
            {:else}
              <span class="price-none">—</span>
            {/if}
          </td>
          <td class="col-price">
            {#if p.price_original && p.price_new}
              <span class="price-profit">+₹{p.price_new - p.price_original}</span>
            {:else}
              <span class="price-none">—</span>
            {/if}
          </td>
          <td class="col-price">
            {#if p.price_new}
              <span class="price-selling">₹{p.price_new}</span>
            {:else}
              <span class="price-none">—</span>
            {/if}
          </td>
          <td><span class="status-badge" class:posted={p.status === 'posted'} class:collected={p.status === 'collected'} class:approved={p.status === 'approved'} class:rejected={p.status === 'rejected'}>{p.status}</span></td>
          <td>
            {#if p.status === 'collected' || p.status === 'draft'}
              <button class="btn-approve" onclick={() => handleApprove(p.id)}>Approve</button>
              <button class="btn-reject" onclick={() => handleReject(p.id)}>Reject</button>
            {/if}
          </td>
        </tr>

        {#if expandedId === p.id}
          <tr class="detail-row">
            <td colspan="9">
              <div class="detail-panel">
                <div class="detail-grid">
                  <div class="detail-section">
                    <h4>Original Caption</h4>
                    <p class="detail-text">{p.caption || '—'}</p>
                  </div>
                  <div class="detail-section">
                    <h4>Rewritten Caption</h4>
                    <p class="detail-text">{p.rewritten_caption || '—'}</p>
                  </div>
                </div>

                <div class="detail-grid">
                  <div class="detail-section">
                    <h4>Media</h4>
                    {#if parseMediaPaths(p.media_paths).length > 0}
                      <ul class="media-list">
                        {#each parseMediaPaths(p.media_paths) as path}
                          <li class="media-item">
                            <span class="media-icon">IMG</span>
                            <span class="media-name">{path.split(/[/\\]/).pop()}</span>
                          </li>
                        {/each}
                      </ul>
                    {:else}
                      <p class="detail-muted">No images</p>
                    {/if}
                  </div>
                  <div class="detail-section">
                    <h4>Videos</h4>
                    {#if parseMediaPaths(p.video_paths).length > 0}
                      <ul class="media-list">
                        {#each parseMediaPaths(p.video_paths) as path}
                          <li class="media-item">
                            <span class="media-icon vid">VID</span>
                            <span class="media-name">{path.split(/[/\\]/).pop()}</span>
                          </li>
                        {/each}
                      </ul>
                    {:else}
                      <p class="detail-muted">No videos</p>
                    {/if}
                  </div>
                </div>

                <div class="detail-meta">
                  <div class="meta-item">
                    <span class="meta-label">Captured Price</span>
                    <span class="meta-value">{p.price_original ? `₹${p.price_original}` : '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Profit</span>
                    <span class="meta-value">{p.price_original && p.price_new ? `+₹${p.price_new - p.price_original}` : '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Selling Price</span>
                    <span class="meta-value">{p.price_new ? `₹${p.price_new}` : '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Source</span>
                    <span class="meta-value mono">{p.source_group_id || '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Pipeline</span>
                    <span class="meta-value">{p.pipeline_id || '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Hash</span>
                    <span class="meta-value mono">{p.hash?.slice(0, 16) || '—'}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">Created</span>
                    <span class="meta-value">{formatTime(p.created_at)}</span>
                  </div>
                </div>
              </div>
            </td>
          </tr>
        {/if}
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

  .col-price { text-align: right; white-space: nowrap; }
  .price-captured { color: #aaa; font-family: monospace; }
  .price-profit { color: #4caf50; font-weight: 600; font-family: monospace; }
  .price-selling { color: #e0e0e0; font-weight: 600; font-family: monospace; }
  .price-none { color: #444; }

  .col-expand { width: 32px; padding: 0 !important; }
  .expand-btn {
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s, color 0.2s;
  }
  .expand-btn:hover { color: #4fc3f7; background: rgba(79, 195, 247, 0.1); }
  .expand-btn.open { transform: rotate(180deg); color: #4fc3f7; }

  .main-row { cursor: default; }
  .main-row:hover { background: rgba(255, 255, 255, 0.02); }

  .detail-row td { padding: 0 !important; border-bottom: 1px solid #2a2a4e; }
  .detail-panel {
    padding: 16px 20px 16px 44px;
    background: rgba(79, 195, 247, 0.03);
    border-top: 1px solid #1e3a5f;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }

  .detail-section h4 {
    margin: 0 0 8px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #4fc3f7;
    font-weight: 600;
  }

  .detail-text {
    margin: 0;
    font-size: 13px;
    color: #ccc;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    background: #12122a;
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid #2a2a4e;
    max-height: 200px;
    overflow-y: auto;
  }

  .detail-muted { color: #555; font-size: 12px; margin: 0; }

  .media-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .media-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #999;
  }
  .media-icon {
    font-size: 9px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 3px;
    background: #1b5e20;
    color: #4caf50;
    flex-shrink: 0;
  }
  .media-icon.vid { background: #4a1a1a; color: #f44336; }
  .media-name { font-family: monospace; }

  .detail-meta {
    display: flex;
    gap: 24px;
    padding-top: 12px;
    border-top: 1px solid #2a2a4e;
  }
  .meta-item { display: flex; flex-direction: column; gap: 2px; }
  .meta-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #555; }
  .meta-value { font-size: 12px; color: #999; }

  .status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 11px;
    background: #333;
    color: #aaa;
  }
  .status-badge.posted { background: #1b5e20; color: #4caf50; }
  .status-badge.collected { background: #1a237e; color: #7986cb; }
  .status-badge.approved { background: #1b5e20; color: #4caf50; }
  .status-badge.rejected { background: #4a1a1a; color: #f44336; }

  button {
    padding: 4px 12px;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }
  .btn-approve { background: #1b5e20; color: #4caf50; }
  .btn-reject { background: #4a1a1a; color: #f44336; }
</style>
