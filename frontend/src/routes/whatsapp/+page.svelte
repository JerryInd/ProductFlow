<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getWhatsAppStatus, getQR, connectWA, disconnectWA
  } from '$lib/api';
  import QRCode from '$lib/components/QRCode.svelte';

  let wsStatus = $state('disconnected');
  let wsPhone = $state<string | null>(null);
  let qrImage = $state('');
  let wsLoading = $state(false);
  let wsPolling: ReturnType<typeof setInterval> | null = null;

  onMount(() => {
    (async () => {
      const ws = await getWhatsAppStatus();
      wsStatus = ws.status;
      wsPhone = ws.phone_number;
    })();
    return () => {
      if (wsPolling) clearInterval(wsPolling);
    };
  });

  async function handleGetQR() {
    wsLoading = true;
    qrImage = '';
    try {
      const resp = await fetch('/api/whatsapp/qr');
      const data = await resp.json();
      qrImage = data.qr_image || '';
      wsPolling = setInterval(async () => {
        try {
          const s = await getWhatsAppStatus();
          if (s.status === 'connected') {
            wsStatus = 'connected';
            wsPhone = s.phone_number;
            if (wsPolling) clearInterval(wsPolling);
            qrImage = '';
            return;
          }
          const qrResp = await fetch('/api/whatsapp/qr');
          if (qrResp.ok) {
            const qrData = await qrResp.json();
            if (qrData.qr_image) qrImage = qrData.qr_image;
          }
        } catch (_) {}
      }, 5000);
    } catch (e) {
      console.error(e);
    }
    wsLoading = false;
  }

  async function handleWSDisconnect() {
    wsLoading = true;
    try {
      await disconnectWA();
    } catch (e) {
      console.error(e);
    }
    wsStatus = 'disconnected';
    wsPhone = null;
    qrImage = '';
    if (wsPolling) clearInterval(wsPolling);
    wsLoading = false;
  }
</script>

<div class="page-header">
  <h1>Connections</h1>
</div>

<div class="cards">
  <div class="card">
    <div class="card-header">
      <div class="card-icon whatsapp">WA</div>
      <div>
        <h2>WhatsApp</h2>
        <p class="subtitle">QR code login</p>
      </div>
    </div>

    <div class="status-row">
      <span class="status-dot" class:connected={wsStatus === 'connected'}></span>
      <span class="status-text">{wsStatus}</span>
      {#if wsPhone}
        <span class="phone">{wsPhone}</span>
      {/if}
    </div>

    <div class="card-actions">
      {#if wsStatus === 'disconnected' || wsStatus === 'scanning'}
        {#if !qrImage}
          <button onclick={handleGetQR} disabled={wsLoading}>
            {wsLoading ? 'Generating...' : 'Login'}
          </button>
        {:else}
          <button class="secondary" onclick={() => { qrImage = ''; if (wsPolling) clearInterval(wsPolling); }}>
            Cancel
          </button>
        {/if}
      {:else}
        <button class="danger" onclick={handleWSDisconnect} disabled={wsLoading}>
          Disconnect
        </button>
      {/if}
    </div>

    {#if qrImage}
      <div class="qr-section">
        <p class="qr-instruction">Scan this QR code with WhatsApp</p>
        <div class="qr-wrapper">
          <QRCode src={qrImage} />
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .page-header { margin-bottom: 24px; }
  h1 { margin: 0; }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 20px;
    max-width: 800px;
  }

  .card {
    background: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 12px;
    padding: 24px;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;
  }

  .card-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 16px;
    flex-shrink: 0;
  }
  .card-icon.whatsapp { background: #25d366; color: #fff; }

  .card-header h2 { margin: 0; font-size: 18px; }
  .subtitle { margin: 2px 0 0; font-size: 12px; color: #888; }

  .status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    padding: 10px 14px;
    background: #12122a;
    border-radius: 8px;
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #f44336;
    flex-shrink: 0;
  }
  .status-dot.connected { background: #4caf50; }

  .status-text { font-size: 14px; color: #e0e0e0; }
  .phone { font-size: 12px; color: #888; margin-left: auto; }

  .card-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  button {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    background: #4fc3f7;
    color: #000;
    align-self: flex-start;
  }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.secondary { background: #2a2a4e; color: #e0e0e0; }
  button.danger { background: #f44336; color: #fff; }

  .qr-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #2a2a4e;
    text-align: center;
  }

  .qr-instruction {
    font-size: 13px;
    color: #aaa;
    margin-bottom: 16px;
  }

  .qr-wrapper {
    display: inline-block;
    background: #fff;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
</style>
