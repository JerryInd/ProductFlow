<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getWhatsAppStatus, getQR, connectWA, disconnectWA,
    getTelegramStatus, getTelegramQR, connectTelegramQR, connectTelegramBot, disconnectTelegram
  } from '$lib/api';
  import QRCode from '$lib/components/QRCode.svelte';

  let wsStatus = $state('disconnected');
  let wsPhone = $state<string | null>(null);
  let qrImage = $state('');
  let wsLoading = $state(false);
  let wsPolling: ReturnType<typeof setInterval> | null = null;

  let tgStatus = $state('disconnected');
  let tgMode = $state<string | null>(null);
  let tgUsername = $state<string | null>(null);
  let tgDisplayName = $state<string | null>(null);
  let tgToken = $state('');
  let tgLoading = $state(false);
  let tgError = $state('');
  let tgQrCode = $state('');
  let tgPolling: ReturnType<typeof setInterval> | null = null;

  onMount(() => {
    (async () => {
      const [ws, tg] = await Promise.all([getWhatsAppStatus(), getTelegramStatus()]);
      wsStatus = ws.status;
      wsPhone = ws.phone_number;
      tgStatus = tg.status;
      tgMode = tg.mode;
      tgUsername = tg.username;
      tgDisplayName = tg.display_name;
    })();
    return () => {
      if (wsPolling) clearInterval(wsPolling);
      if (tgPolling) clearInterval(tgPolling);
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

  async function handleTGQRConnect() {
    tgLoading = true;
    tgError = '';
    tgQrCode = '';
    try {
      await connectTelegramQR();
      tgPolling = setInterval(async () => {
        try {
          const s = await getTelegramStatus();
          if (s.status === 'connected') {
            tgStatus = 'connected';
            tgMode = s.mode;
            tgUsername = s.username;
            tgDisplayName = s.display_name;
            tgQrCode = '';
            if (tgPolling) clearInterval(tgPolling);
          } else if (s.status === 'qr_pending') {
            try {
              const qr = await getTelegramQR();
              tgQrCode = qr.qr;
            } catch (_) {}
          } else if (s.status === 'disconnected') {
            tgQrCode = '';
            if (tgPolling) clearInterval(tgPolling);
          }
        } catch (_) {}
      }, 2000);
    } catch (e: any) {
      tgError = e.message || 'Failed to start QR login';
    }
    tgLoading = false;
  }

  async function handleTGBotConnect() {
    if (!tgToken.trim()) return;
    tgLoading = true;
    tgError = '';
    try {
      const resp = await connectTelegramBot(tgToken.trim());
      tgStatus = 'connected';
      tgMode = 'bot';
      tgUsername = resp.username;
      tgDisplayName = resp.display_name;
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
      tgMode = null;
      tgUsername = null;
      tgDisplayName = null;
      tgQrCode = '';
      if (tgPolling) clearInterval(tgPolling);
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

  <div class="card">
    <div class="card-header">
      <div class="card-icon telegram">TG</div>
      <div>
        <h2>Telegram</h2>
        <p class="subtitle">
          {#if tgStatus === 'connected'}
            {tgMode === 'qr' ? 'Logged in via QR code' : 'Connected as bot'}
          {:else}
            QR code or bot token
          {/if}
        </p>
      </div>
    </div>

    <div class="status-row">
      <span class="status-dot" class:connected={tgStatus === 'connected'}></span>
      <span class="status-text">{tgStatus === 'qr_pending' ? 'waiting for scan' : tgStatus}</span>
      {#if tgUsername}
        <span class="phone">
          {#if tgMode === 'qr'}
            @{tgUsername}
          {:else}
            @{tgUsername}
          {/if}
        </span>
      {/if}
    </div>

    {#if tgStatus === 'connected'}
      <div class="tg-info">
        <p><strong>{tgDisplayName || tgUsername}</strong> (@{tgUsername})</p>
        <p class="tg-hint">
          {#if tgMode === 'qr'}
            Logged in as your Telegram account. Add groups as pipeline sources.
          {:else}
            Bot connected. Add the bot to your Telegram groups and set them as pipeline sources.
          {/if}
        </p>
      </div>
    {/if}

    <div class="card-actions">
      {#if tgStatus === 'disconnected' && !tgQrCode}
        <div class="tg-login-modes">
          <button class="tg-mode-btn" onclick={handleTGQRConnect} disabled={tgLoading}>
            {tgLoading ? 'Starting...' : 'Login with QR Code'}
          </button>
          <div class="tg-divider">or</div>
          <div class="tg-form">
            <input
              type="text"
              placeholder="Bot token from @BotFather"
              bind:value={tgToken}
              disabled={tgLoading}
            />
            <button onclick={handleTGBotConnect} disabled={tgLoading || !tgToken.trim()}>
              {tgLoading ? 'Connecting...' : 'Connect Bot'}
            </button>
          </div>
        </div>
      {:else if tgQrCode}
        <button class="secondary" onclick={() => { tgQrCode = ''; if (tgPolling) clearInterval(tgPolling); }}>
          Cancel
        </button>
      {:else if tgStatus === 'connected'}
        <button class="danger" onclick={handleTGDisconnect} disabled={tgLoading}>
          Disconnect
        </button>
      {/if}

      {#if tgError}
        <p class="tg-error">{tgError}</p>
      {/if}
    </div>

    {#if tgQrCode}
      <div class="qr-section">
        <p class="qr-instruction">Scan this QR code with Telegram</p>
        <div class="qr-instructions">
          <ol>
            <li>Open Telegram on your phone</li>
            <li>Go to Settings → Devices → Add Device</li>
            <li>Point your phone at this screen</li>
          </ol>
        </div>
        <div class="qr-wrapper">
          <QRCode data={tgQrCode} />
        </div>
      </div>
    {/if}

    {#if tgStatus === 'disconnected' && !tgQrCode}
      <div class="tg-hints">
        <p class="tg-hint">
          <strong>QR Code</strong> — Login as your Telegram account (can read all groups)
        </p>
        <p class="tg-hint">
          <strong>Bot Token</strong> — Get from <strong>@BotFather</strong> on Telegram → /newbot → copy token
        </p>
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

  .qr-instructions {
    text-align: left;
    margin-bottom: 16px;
  }
  .qr-instructions ol {
    margin: 0;
    padding-left: 20px;
    font-size: 12px;
    color: #999;
  }
  .qr-instructions li {
    margin-bottom: 4px;
  }

  .qr-wrapper {
    display: inline-block;
    background: #fff;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .tg-login-modes {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .tg-mode-btn {
    background: #0088cc;
    color: #fff;
    width: 100%;
    text-align: center;
  }

  .tg-divider {
    text-align: center;
    font-size: 12px;
    color: #666;
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

  .tg-hints {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #2a2a4e;
  }

  .tg-hint {
    font-size: 11px;
    color: #666;
    margin: 0 0 6px;
  }
</style>
