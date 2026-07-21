<script lang="ts">
  import { page } from '$app/stores';
</script>

<nav class="sidebar">
  <div class="logo">ProductFlow AI</div>
  <div class="nav-items">
    <a href="/" class="nav-item" class:active={$page.url.pathname === '/'}>
      <span class="icon">🏠</span> Home
    </a>
    <a href="/whatsapp" class="nav-item" class:active={$page.url.pathname.startsWith('/whatsapp')}>
      <span class="icon">🔗</span> Connections
    </a>
    <a href="/groups" class="nav-item" class:active={$page.url.pathname.startsWith('/groups')}>
      <span class="icon">👥</span> Groups
    </a>
    <a href="/relay" class="nav-item" class:active={$page.url.pathname.startsWith('/relay')}>
      <span class="icon">📡</span> Relay
    </a>
  </div>
  <div class="footer">
    <span class="badge">v1.0.0</span>
  </div>
</nav>

<style>
  .sidebar {
    width: 220px;
    min-height: 100vh;
    background: #1a1a2e;
    color: #e0e0e0;
    display: flex;
    flex-direction: column;
    padding: 0;
  }
  .logo {
    padding: 20px;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    border-bottom: 1px solid #2a2a4e;
  }
  .nav-items {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 8px 0;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    color: #b0b0c8;
    text-decoration: none;
    font-size: 14px;
    transition: background 0.2s;
  }
  .nav-item:hover {
    background: #2a2a4e;
    color: #fff;
  }
  .nav-item.active {
    background: #16213e;
    color: #4fc3f7;
    border-right: 3px solid #4fc3f7;
  }
  .icon { font-size: 16px; }
  .footer {
    padding: 12px 20px;
    border-top: 1px solid #2a2a4e;
    text-align: center;
  }
  .badge {
    font-size: 11px;
    color: #666;
  }
</style>
