<script lang="ts">
  import { onMount } from 'svelte';
  import { getProducts, approveProduct, rejectProduct, getChats, forwardToPlatforms, type Product, type PlatformChat } from '$lib/api';

  let products = $state<Product[]>([]);
  let allProducts = $state<Product[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let statusFilter = $state('');
  let searchQuery = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  type SortOption = 'newest' | 'oldest' | 'price_low' | 'price_high';
  let sortBy = $state<SortOption>('newest');
  let showSortMenu = $state(false);
  let expandedId = $state<number | null>(null);

  let selectedIds = $state<Set<number>>(new Set());
  let showForwardModal = $state(false);
  let chats = $state<PlatformChat[]>([]);
  let chatSearch = $state('');
  let selectedRecipients = $state<Set<string>>(new Set());
  let sending = $state(false);
  let sendResult = $state<{ sent: number; failed: number; errors: string[] } | null>(null);

  let filteredChats = $derived(
    chatSearch
      ? chats.filter(c => c.name.toLowerCase().includes(chatSearch.toLowerCase()) || c.jid.includes(chatSearch))
      : chats
  );

  let selectAll = $state(false);

  $effect(() => {
    const allIds = products.map(p => p.id);
    const allSelected = allIds.length > 0 && allIds.every(id => selectedIds.has(id));
    selectAll = allSelected;
  });

  function toggleSelectAll() {
    if (selectAll) {
      selectedIds = new Set(products.map(p => p.id));
    } else {
      selectedIds = new Set();
    }
  }

  function toggleSelect(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    selectedIds = next;
  }

  async function openForwardModal() {
    if (selectedIds.size === 0) return;
    showForwardModal = true;
    sendResult = null;
    chatSearch = '';
    selectedRecipients = new Set();
    try {
      const resp = await getChats();
      chats = resp.chats;
    } catch (e) {
      chats = [];
    }
  }

  function closeForwardModal() {
    showForwardModal = false;
    sendResult = null;
  }

  function toggleRecipient(platform: string, jid: string) {
    const key = `${platform}:${jid}`;
    const next = new Set(selectedRecipients);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    selectedRecipients = next;
  }

  async function handleForward() {
    if (selectedRecipients.size === 0 || selectedIds.size === 0) return;
    sending = true;
    sendResult = null;
    try {
      const ids = Array.from(selectedIds);
      const recipients = Array.from(selectedRecipients).map(key => {
        const [platform, ...jidParts] = key.split(':');
        return { platform, jid: jidParts.join(':') };
      });
      sendResult = await forwardToPlatforms(ids, recipients);
      if (sendResult.failed === 0) {
        selectedIds = new Set();
      }
    } catch (e: any) {
      sendResult = { sent: 0, failed: 1, errors: [e.message] };
    }
    sending = false;
  }

  onMount(async () => {
    await loadProducts();
  });

  async function loadProducts() {
    loading = true;
    try {
      const resp = await getProducts({ status: statusFilter || undefined, limit: 500 });
      allProducts = resp.products;
      total = resp.total;
      applyFilters();
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  function applyFilters() {
    let filtered = [...allProducts];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        (p.caption && p.caption.toLowerCase().includes(q)) ||
        (p.rewritten_caption && p.rewritten_caption.toLowerCase().includes(q)) ||
        (p.hash && p.hash.toLowerCase().includes(q))
      );
    }

    if (dateFrom) {
      const from = new Date(dateFrom).getTime();
      filtered = filtered.filter(p => p.created_at && new Date(p.created_at).getTime() >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo + 'T23:59:59').getTime();
      filtered = filtered.filter(p => p.created_at && new Date(p.created_at).getTime() <= to);
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return (b.created_at ? new Date(b.created_at).getTime() : 0) - (a.created_at ? new Date(a.created_at).getTime() : 0);
        case 'oldest':
          return (a.created_at ? new Date(a.created_at).getTime() : 0) - (b.created_at ? new Date(b.created_at).getTime() : 0);
        case 'price_low':
          return (a.price_original || 0) - (b.price_original || 0);
        case 'price_high':
          return (b.price_original || 0) - (a.price_original || 0);
      }
    });

    products = filtered;
  }

  function setSort(opt: SortOption) {
    sortBy = opt;
    showSortMenu = false;
    applyFilters();
  }

  function handleSortToggle() {
    showSortMenu = !showSortMenu;
  }

  function handleSortOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest('.sort-row')) {
      showSortMenu = false;
    }
  }

  $effect(() => {
    searchQuery;
    dateFrom;
    dateTo;
    applyFilters();
  });

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

  function formatDateTime(ts: string | null): string {
    if (!ts) return '—';
    const d = new Date(ts);
    const date = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const time = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    return `${date} ${time}`;
  }

  function formatDateShort(ts: string | null): string {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
</script>

<svelte:window onclick={handleSortOutside} />

<h1>Products</h1>

<div class="controls">
  <div class="filter-row">
    <select bind:value={statusFilter} onchange={loadProducts}>
      <option value="">All Status</option>
      <option value="collected">Collected</option>
      <option value="approved">Approved</option>
      <option value="rejected">Rejected</option>
      <option value="posted">Posted</option>
    </select>

    <input
      type="text"
      class="search-input"
      placeholder="Search caption, hash..."
      bind:value={searchQuery}
    />

    <div class="date-filter">
      <label class="date-label">From</label>
      <input type="date" bind:value={dateFrom} />
    </div>
    <div class="date-filter">
      <label class="date-label">To</label>
      <input type="date" bind:value={dateTo} />
    </div>

    {#if searchQuery || dateFrom || dateTo}
      <button class="btn-clear" onclick={() => { searchQuery = ''; dateFrom = ''; dateTo = ''; }}>Clear</button>
    {/if}
  </div>
  <div class="sort-row">
    <button class="sort-icon" onclick={handleSortToggle}>⇵</button>
    {#if showSortMenu}
      <div class="sort-menu">
        <button class="sort-option" class:active={sortBy === 'newest'} onclick={() => setSort('newest')}>Newest</button>
        <button class="sort-option" class:active={sortBy === 'oldest'} onclick={() => setSort('oldest')}>Oldest</button>
        <button class="sort-option" class:active={sortBy === 'price_low'} onclick={() => setSort('price_low')}>Price Low</button>
        <button class="sort-option" class:active={sortBy === 'price_high'} onclick={() => setSort('price_high')}>Price High</button>
      </div>
    {/if}
  </div>
  <div class="controls-right">
    <span class="total">{products.length} of {total} total</span>
    {#if selectedIds.size > 0}
      <button class="btn-forward" onclick={openForwardModal}>Send to Customer ({selectedIds.size})</button>
    {/if}
  </div>
</div>

{#if loading}
  <p class="muted">Loading...</p>
{:else if products.length === 0}
  <p class="muted">No products found.</p>
{:else}
  <table>
    <thead>
      <tr>
        <th class="col-check">
          <input type="checkbox" checked={selectAll} onchange={toggleSelectAll} />
        </th>
        <th class="col-expand"></th>
        <th>ID</th>
        <th>Original</th>
        <th>Rewritten</th>
        <th class="col-price">Captured</th>
        <th class="col-price">Profit</th>
        <th class="col-price">Selling</th>
        <th>Status</th>
        <th>Date</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each products as p (p.id)}
        <tr class="main-row" class:expanded={expandedId === p.id} class:selected={selectedIds.has(p.id)}>
          <td class="col-check">
            <input type="checkbox" checked={selectedIds.has(p.id)} onchange={() => toggleSelect(p.id)} />
          </td>
          <td class="col-expand">
            <button class="expand-btn" class:open={expandedId === p.id} onclick={() => toggleExpand(p.id)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>
          </td>
          <td class="mono">{p.id}</td>
          <td class="caption-cell">{p.caption?.slice(0, 60)}{p.caption && p.caption.length > 60 ? '...' : ''}</td>
          <td class="caption-cell">{p.rewritten_caption?.slice(0, 60)}{p.rewritten_caption && p.rewritten_caption.length > 60 ? '...' : ''}</td>
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
          <td class="col-date">
            <span class="date-main">{formatDateShort(p.created_at)}</span>
            <span class="date-time">{new Date(p.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}</span>
          </td>
          <td>
            {#if p.status === 'collected' || p.status === 'draft'}
              <button class="btn-approve" onclick={() => handleApprove(p.id)}>Approve</button>
              <button class="btn-reject" onclick={() => handleReject(p.id)}>Reject</button>
            {/if}
          </td>
        </tr>

        {#if expandedId === p.id}
          <tr class="detail-row">
            <td colspan="11">
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
                    <span class="meta-value">{formatDateTime(p.created_at)}</span>
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

{#if showForwardModal}
  <div class="modal-backdrop" onclick={closeForwardModal}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <div class="modal-header">
        <h2>Send to Customer</h2>
        <button class="modal-close" onclick={closeForwardModal}>&times;</button>
      </div>

      {#if sendResult}
        <div class="send-result" class:success={sendResult.failed === 0}>
          {#if sendResult.sent > 0}
            <p>Sent {sendResult.sent} item{sendResult.sent > 1 ? 's' : ''} successfully</p>
          {/if}
          {#if sendResult.failed > 0}
            <p class="error">{sendResult.failed} failed: {sendResult.errors.join(', ')}</p>
          {/if}
        </div>
      {:else}
        <div class="modal-body">
          <label class="modal-label">Search Groups</label>
          <input
            type="text"
            class="chat-search"
            placeholder="Search WhatsApp & Telegram groups..."
            bind:value={chatSearch}
          />
          <div class="chat-list">
            {#each filteredChats as chat}
              {@const key = `${chat.platform}:${chat.jid}`}
              <button
                class="chat-item"
                class:active={selectedRecipients.has(key)}
                onclick={() => toggleRecipient(chat.platform, chat.jid)}
              >
                <span class="platform-icon" class:wa={chat.platform === 'whatsapp'} class:tg={chat.platform === 'telegram'}>
                  {chat.platform === 'whatsapp' ? 'WA' : 'TG'}
                </span>
                <span class="chat-name">{chat.name}</span>
                <span class="chat-check">{selectedRecipients.has(key) ? '✓' : ''}</span>
              </button>
            {/each}
            {#if filteredChats.length === 0}
              <p class="no-chats">No groups found</p>
            {/if}
          </div>
        </div>
      {/if}

      <div class="modal-footer">
        <button class="btn-cancel" onclick={closeForwardModal}>Cancel</button>
        {#if !sendResult}
          <button class="btn-send" onclick={handleForward} disabled={selectedRecipients.size === 0 || sending}>
            {sending ? 'Sending...' : `Send to ${selectedRecipients.size} group${selectedRecipients.size !== 1 ? 's' : ''}`}
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  h1 { margin: 0 0 16px; }
  .muted { color: #666; }

  .controls { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
  .filter-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

  select {
    padding: 8px 12px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 13px;
  }

  .search-input {
    padding: 8px 12px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 13px;
    min-width: 200px;
  }
  .search-input:focus { outline: none; border-color: #4fc3f7; }

  .date-filter { display: flex; align-items: center; gap: 4px; }
  .date-label { font-size: 11px; color: #666; }
  .date-filter input[type="date"] {
    padding: 7px 10px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 12px;
  }
  .date-filter input[type="date"]:focus { outline: none; border-color: #4fc3f7; }

  .btn-clear {
    padding: 6px 14px;
    background: #2a2a4e;
    color: #aaa;
    border: 1px solid #444;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
  }
  .btn-clear:hover { background: #3a3a5e; color: #e0e0e0; }

  .total { font-size: 13px; color: #888; }

  .sort-row { display: flex; align-items: center; position: relative; }
  .sort-icon {
    padding: 6px 10px;
    background: #1a1a2e;
    color: #888;
    border: 1px solid #333;
    border-radius: 6px;
    font-size: 16px;
    cursor: pointer;
    line-height: 1;
    transition: all 0.15s;
  }
  .sort-icon:hover { background: #2a2a4e; color: #ccc; }
  .sort-menu {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 4px 0;
    z-index: 10;
    min-width: 130px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }
  .sort-option {
    display: block;
    width: 100%;
    padding: 8px 14px;
    background: none;
    border: none;
    color: #aaa;
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    transition: background 0.1s;
  }
  .sort-option:hover { background: #2a2a4e; color: #e0e0e0; }
  .sort-option.active { color: #4fc3f7; background: rgba(79, 195, 247, 0.1); }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #2a2a4e; }
  th { color: #888; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  td { color: #ccc; }

  .mono { font-family: monospace; font-size: 12px; color: #888; }
  .caption-cell { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .col-price { text-align: right; white-space: nowrap; }
  .price-captured { color: #aaa; font-family: monospace; }
  .price-profit { color: #4caf50; font-weight: 600; font-family: monospace; }
  .price-selling { color: #e0e0e0; font-weight: 600; font-family: monospace; }
  .price-none { color: #444; }

  .col-date { white-space: nowrap; }
  .date-main { display: block; font-size: 12px; color: #aaa; }
  .date-time { display: block; font-size: 11px; color: #666; }

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

  .col-check { width: 40px; text-align: center; }
  .col-check input[type="checkbox"] { accent-color: #4fc3f7; cursor: pointer; width: 16px; height: 16px; }
  .selected { background: rgba(79, 195, 247, 0.06) !important; }

  .controls-right { display: flex; align-items: center; gap: 12px; }
  .btn-forward {
    padding: 7px 16px;
    background: #1565c0;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-forward:hover { background: #1976d2; }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal {
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 10px;
    width: 480px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
  }
  .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #2a2a4e; }
  .modal-header h2 { margin: 0; font-size: 16px; color: #e0e0e0; }
  .modal-close { background: none; border: none; color: #888; font-size: 20px; cursor: pointer; padding: 0 4px; }
  .modal-close:hover { color: #e0e0e0; }

  .modal-body { padding: 16px 20px; overflow-y: auto; flex: 1; }
  .modal-label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin: 12px 0 6px; }
  .modal-label:first-child { margin-top: 0; }

  .chat-search {
    width: 100%;
    padding: 7px 12px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #12122a;
    color: #e0e0e0;
    font-size: 12px;
    margin-bottom: 6px;
    box-sizing: border-box;
  }
  .chat-search:focus { outline: none; border-color: #4fc3f7; }

  .chat-list {
    border: 1px solid #2a2a4e;
    border-radius: 6px;
    max-height: 200px;
    overflow-y: auto;
  }
  .chat-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    border-bottom: 1px solid #1e1e3a;
    cursor: pointer;
    text-align: left;
    transition: background 0.1s;
  }
  .chat-item:last-child { border-bottom: none; }
  .chat-item:hover { background: #2a2a4e; }
  .chat-item.active { background: rgba(79, 195, 247, 0.15); }
  .platform-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .platform-icon.wa { background: #25d366; color: #fff; }
  .platform-icon.tg { background: #0088cc; color: #fff; }
  .chat-name { color: #e0e0e0; font-size: 13px; flex: 1; }
  .chat-check { color: #4fc3f7; font-size: 14px; width: 20px; text-align: center; }
  .no-chats { color: #555; font-size: 12px; padding: 12px; text-align: center; margin: 0; }

  .modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px; border-top: 1px solid #2a2a4e; }
  .btn-cancel { padding: 7px 16px; background: #2a2a4e; color: #aaa; border: 1px solid #444; border-radius: 6px; font-size: 13px; cursor: pointer; }
  .btn-cancel:hover { background: #3a3a5e; color: #e0e0e0; }
  .btn-send { padding: 7px 16px; background: #1565c0; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
  .btn-send:hover { background: #1976d2; }
  .btn-send:disabled { opacity: 0.5; cursor: not-allowed; }

  .send-result { padding: 16px 20px; }
  .send-result p { margin: 0 0 8px; color: #4caf50; font-size: 13px; }
  .send-result .error { color: #f44336; }
</style>
