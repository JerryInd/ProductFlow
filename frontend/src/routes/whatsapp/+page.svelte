<script lang="ts">
  import { onMount } from 'svelte';
  import { getWhatsAppStatus, getQR, connectWA, disconnectWA } from '$lib/api';

  let wsStatus = $state('disconnected');
  let phoneNumber = $state<string | null>(null);
  let qrCode = $state('');
  let loading = $state(false);

  onMount(async () => {
    const s = await getWhatsAppStatus();
    wsStatus = s.status;
    phoneNumber = s.phone_number;
  });

  async function handleGetQR() {
    loading = true;
    try {
      const resp = await getQR();
      qrCode = resp.qr;
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  async function handleConnect() {
    loading = true;
    try {
      await connectWA();
      wsStatus = 'connected';
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }

  async function handleDisconnect() {
    loading = true;
    try {
      await disconnectWA();
      wsStatus = 'disconnected';
      phoneNumber = null;
      qrCode = '';
    } catch (e) {
      console.error(e);
    }
    loading = false;
  }
</script>

<h1>WhatsApp</h1>

<div class="status-bar">
  Status: <span class="status" class:connected={wsStatus === 'connected'}>{wsStatus}</span>
  {#if phoneNumber}
    <span class="phone">| {phoneNumber}</span>
  {/if}
</div>

<div class="actions">
  {#if wsStatus === 'disconnected'}
    <button onclick={handleGetQR} disabled={loading}>
      {loading ? 'Generating...' : 'Generate QR'}
    </button>
  {:else}
    <button class="danger" onclick={handleDisconnect} disabled={loading}>
      Disconnect
    </button>
  {/if}
</div>

{#if qrCode}
  <div class="qr-section">
    <h2>Scan QR with WhatsApp</h2>
    <div class="qr-box">{qrCode}</div>
    <button onclick={handleConnect} disabled={loading}>
      I've Scanned — Connect
    </button>
  </div>
{/if}

<style>
  h1 { margin: 0 0 16px; }
  .status-bar { font-size: 14px; color: #aaa; margin-bottom: 20px; }
  .status { color: #f44336; font-weight: 600; }
  .status.connected { color: #4caf50; }
  .phone { color: #888; margin-left: 8px; }
  .actions { margin-bottom: 24px; }
  button {
    padding: 10px 24px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    background: #4fc3f7;
    color: #000;
    font-weight: 600;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.danger { background: #f44336; color: #fff; }
  .qr-section { margin-top: 20px; }
  .qr-section h2 { font-size: 14px; color: #aaa; margin-bottom: 12px; }
  .qr-box {
    background: #fff;
    color: #000;
    padding: 24px;
    border-radius: 8px;
    font-family: monospace;
    font-size: 12px;
    word-break: break-all;
    max-width: 300px;
    margin-bottom: 16px;
  }
</style>
