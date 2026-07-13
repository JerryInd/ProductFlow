<script lang="ts">
  import Sidebar from '$lib/components/Sidebar.svelte';
</script>

<div class="app-layout">
  <Sidebar />
  <main class="main-content">
    <slot />
  </main>
</div>

<style>
  .app-layout {
    display: flex;
    min-height: 100vh;
  }
  .main-content {
    flex: 1;
    padding: 24px 32px;
    background: #0f0f1a;
    overflow-y: auto;
  }
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
  }
  :global(*), :global(*::before), :global(*::after) {
    box-sizing: border-box;
  }
  :global(a) { color: #4fc3f7; text-decoration: none; }
  :global(a:hover) { text-decoration: underline; }
</style>
