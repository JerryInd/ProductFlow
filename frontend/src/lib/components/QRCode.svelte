<script lang="ts">
  let { src = '' }: { src: string } = $props();
</script>

{#if src}
  <img src={src} alt="QR Code" width="256" height="256" style="image-rendering: pixelated;" />
{/if}
