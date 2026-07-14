<script lang="ts">
  import { onMount } from 'svelte';
  import { getWhatsAppStatus, getQR, connectWA, disconnectWA, getTelegramStatus, connectTelegram, disconnectTelegram } from '$lib/api';
  import QRCode from '$lib/components/QRCode.svelte';

  let wsStatus = $state('disconnected');
  let wsPhone = $state<string | null>(null);
  let qrCode = $state('');
  let wsLoading = $state(false);
  let wsPolling: ReturnType<typeof setInterval> | null = null;

  let tgStatus = $state('disconnected');
  let tgUsername = $state<string | null>(null);
  let tgName = $state<string | null>(null);
  let tgToken = $state('');
  let tgLoading = $state(false);
  let tgError = $state('');

  onMount(() => {
    (async () => {
      const [ws, tg] = await Promise.all([getWhatsAppStatus(), getTelegramStatus()]);
      wsStatus = ws.status;
      wsPhone = ws.phone_number;
      tgStatus = tg.status;
      tgUsername = tg.bot_username;
      tgName = tg.bot_name;
    })();
    return () => { if (wsPolling) clearInterval(wsPolling); };
  });

  async function handleGetQR() {
    wsLoading = true;
    qrCode = '';
    try {
      const resp = await getQR();
      qrCode = resp.qr;
      wsPolling = setInterval(async () => {
        try {
          const s = await getWhatsAppStatus();
          if (s.status === 'connected') {
            wsStatus = 'connected';
            wsPhone = s.phone_number;
            if (wsPolling) clearInterval(wsPolling);
            qrCode = '';
          }
        } catch (_) {}
      }, 3000);
    } catch (e) {
      console.error(e);
    }
    wsLoading = false;
  }

  async function handleWSConnect() {
    wsLoading = true;
    try {
      await connectWA();
      const s = await getWhatsAppStatus();
      wsStatus = s.status;
      wsPhone = s.phone_number;
    } catch (e) {
      console.error(e);
    }
    wsLoading = false;
  }

  async function handleWSDisconnect() {
    wsLoading = true;
    try {
      await disconnectWA();
      wsStatus = 'disconnected';
      wsPhone = null;
      qrCode = '';
      if (wsPolling) clearInterval(wsPolling);
    } catch (e) {
      console.error(e);
    }
    wsLoading = false;
  }

  async function handleTGConnect() {
    if (!tgToken.trim()) return;
    tgLoading = true;
    tgError = '';
    try {
      const resp = await connectTelegram(tgToken.trim());
      tgStatus = 'connected';
      tgUsername = resp.bot_username;
      tgName = resp.bot_name;
      tgToken = '';
    } catch (e: any) {
      tgError = e.message || 'Connection failed';
    }
    tgLoading = false;
  }

  async function handleTGDisconnect() {
    tgLoading = true;
    try {
      await disconnectTelegram();
      tgStatus = 'disconnected';
      tgUsername = null;
      tgName = null;
    } catch (e) {
      console.error(e);
    }
    tgLoading = false;
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
        <p class="subtitle">Baileys bridge connection</p>
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
      {#if wsStatus === 'disconnected'}
        {#if !qrCode}
          <button onclick={handleGetQR} disabled={wsLoading}>
            {wsLoading ? 'Generating...' : 'Login'}
          </button>
        {:else}
          <button class="secondary" onclick={() => { qrCode = ''; if (wsPolling) clearInterval(wsPolling); }}>
            Cancel
          </button>
        {/if}
      {:else}
        <button class="danger" onclick={handleWSDisconnect} disabled={wsLoading}>
          Disconnect
        </button>
      {/if}
    </div>

    {#if qrCode}
      <div class="qr-section">
        <p class="qr-instruction">Scan this QR code with WhatsApp</p>
        <div class="qr-wrapper">
          <QRCode data={qrCode} />
        </div>
        <button onclick={handleWSConnect} disabled={wsLoading}>
          I've Scanned — Connect
        </button>
      </div>
    {/if}
  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-icon telegram">TG</div>
      <div>
        <h2>Telegram</h2>
        <p class="subtitle">Telegram bot connection</p>
      </div>
    </div>

    <div class="status-row">
      <span class="status-dot" class:connected={tgStatus === 'connected'}></span>
      <span class="status-text">{tgStatus}</span>
      {#if tgUsername}
        <span class="phone">@{tgUsername}</span>
      {/if}
    </div>

    {#if tgStatus === 'connected'}
      <div class="tg-info">
        <p><strong>{tgName}</strong> (@{tgUsername})</p>
        <p class="tg-hint">Add this bot to your Telegram groups and set them as pipeline sources.</p>
      </div>
    {/if}

    <div class="card-actions">
      {#if tgStatus === 'disconnected'}
        <div class="tg-form">
          <input
            type="text"
            placeholder="Bot token from @BotFather"
            bind:value={tgToken}
            disabled={tgLoading}
          />
          <button onclick={handleTGConnect} disabled={tgLoading || !tgToken.trim()}>
            {tgLoading ? 'Connecting...' : 'Connect'}
          </button>
        </div>
        {#if tgError}
          <p class="tg-error">{tgError}</p>
        {/if}
        <p class="tg-hint">
          Get a bot token from <strong>@BotFather</strong> on Telegram → /newbot → copy the token
        </p>
      {:else}
        <button class="danger" onclick={handleTGDisconnect} disabled={tgLoading}>
          Disconnect
        </button>
      {/if}
    </div>
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
  .card-icon.telegram { background: #0088cc; color: #fff; }

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

  .tg-form {
    display: flex;
    gap: 8px;
  }

  .tg-form input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #333;
    border-radius: 6px;
    background: #12122a;
    color: #e0e0e0;
    font-size: 13px;
    font-family: monospace;
  }
  .tg-form input:focus { outline: none; border-color: #4fc3f7; }

  .tg-info {
    padding: 12px;
    background: #12122a;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 13px;
    color: #e0e0e0;
  }
  .tg-info p { margin: 0 0 4px; }

  .tg-error {
    color: #f44336;
    font-size: 12px;
    margin: 0;
  }

  .tg-hint {
    font-size: 11px;
    color: #666;
    margin: 0;
  }
</style>
