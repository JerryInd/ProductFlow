<script lang="ts">
  import qrcode from 'qrcode';

  let { src = '', data = '' }: { src?: string; data?: string } = $props();
  let qrImage = $state('');

  $effect(() => {
    if (src) {
      qrImage = src;
    } else if (data) {
      qrcode.toDataURL(data, { errorCorrectionLevel: 'L', margin: 2, width: 300 }, (err: any, url: string) => {
        if (!err) qrImage = url;
      });
    } else {
      qrImage = '';
    }
  });
</script>

{#if qrImage}
  <img src={qrImage} alt="QR Code" width="256" height="256" style="image-rendering: pixelated;" />
{/if}
