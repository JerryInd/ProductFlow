<script lang="ts">
  import { onMount } from 'svelte';
  import QRCode from 'qrcode';

  let { data = '' }: { data: string } = $props();
  let canvas: HTMLCanvasElement;

  onMount(() => {
    if (data && canvas) {
      renderQR(data);
    }
  });

  $effect(() => {
    if (data && canvas) {
      renderQR(data);
    }
  });

  async function renderQR(text: string) {
    try {
      await QRCode.toCanvas(canvas, text, {
        width: 200,
        margin: 1,
        color: { dark: '#000000', light: '#ffffff' }
      });
    } catch (e) {
      console.error('QR render failed:', e);
    }
  }
</script>

<canvas bind:this={canvas} width="200" height="200"></canvas>
