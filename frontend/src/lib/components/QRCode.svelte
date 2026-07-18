<script lang="ts">
  import { onMount } from 'svelte';
  import QRCode from 'qrcode';

  let { data = '' }: { data: string } = $props();
  let imgSrc = $state('');

  onMount(() => {
    if (data) renderQR(data);
  });

  $effect(() => {
    if (data) renderQR(data);
  });

  async function renderQR(text: string) {
    try {
      imgSrc = await QRCode.toDataURL(text, {
        width: 300,
        margin: 3,
        errorCorrectionLevel: 'L',
      });
    } catch (e) {
      console.error('QR render failed:', e);
    }
  }
</script>

{#if imgSrc}
  <img src={imgSrc} alt="QR Code" width="300" height="300" />
{/if}
