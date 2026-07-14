<script lang="ts">
  import { onMount } from 'svelte';

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

  function renderQR(text: string) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = 200;
    canvas.width = size;
    canvas.height = size;

    const modules = generateQRMatrix(text);
    const moduleCount = modules.length;
    const cellSize = size / moduleCount;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);

    ctx.fillStyle = '#000000';
    for (let row = 0; row < moduleCount; row++) {
      for (let col = 0; col < moduleCount; col++) {
        if (modules[row][col]) {
          ctx.fillRect(col * cellSize, row * cellSize, cellSize + 0.5, cellSize + 0.5);
        }
      }
    }
  }

  function generateQRMatrix(text: string): boolean[][] {
    const len = text.length;
    const type = len < 26 ? 2 : len < 48 ? 3 : len < 78 ? 4 : len < 128 ? 5 : 6;
    const size = 17 + type * 4;
    const modules: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
    const reserved: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

    placeFinderPatterns(modules, reserved, size);
    placeTimingPatterns(modules, reserved, size);
    reserveFormatArea(reserved, size);

    const dataBits = textToBits(text, type);
    placeData(modules, reserved, dataBits, size);

    const mask = 0;
    applyMask(modules, reserved, mask, size);
    placeFormatInfo(modules, mask, size);

    return modules;
  }

  function placeFinderPatterns(modules: boolean[][], reserved: boolean[][], size: number) {
    const pattern = [
      [1,1,1,1,1,1,1],
      [1,0,0,0,0,0,1],
      [1,0,1,1,1,0,1],
      [1,0,1,1,1,0,1],
      [1,0,1,1,1,0,1],
      [1,0,0,0,0,0,1],
      [1,1,1,1,1,1,1],
    ];
    for (const [r, c] of [[0,0],[0,size-7],[size-7,0]]) {
      for (let dr = 0; dr < 7; dr++) {
        for (let dc = 0; dc < 7; dc++) {
          modules[r+dr][c+dc] = pattern[dr][dc] === 1;
          reserved[r+dr][c+dc] = true;
        }
      }
    }
    for (let i = 0; i < 8; i++) {
      if (i < size) {
        reserved[7][i] = true;
        reserved[i][7] = true;
        if (size-8 >= 0) {
          reserved[size-1-i < size ? size-1-i : 0][7] = true;
          reserved[7][size-1-i < size ? size-1-i : 0] = true;
        }
      }
    }
  }

  function placeTimingPatterns(modules: boolean[][], reserved: boolean[][], size: number) {
    for (let i = 8; i < size - 8; i++) {
      modules[6][i] = i % 2 === 0;
      modules[i][6] = i % 2 === 0;
      reserved[6][i] = true;
      reserved[i][6] = true;
    }
  }

  function reserveFormatArea(reserved: boolean[][], size: number) {
    for (let i = 0; i < 9; i++) {
      reserved[8][i] = true;
      reserved[i][8] = true;
      if (size - 1 - i >= 0) {
        reserved[8][size - 1 - i] = true;
        reserved[size - 1 - i][8] = true;
      }
    }
    reserved[8][8] = true;
  }

  function textToBits(text: string, type: number): number[] {
    const bits: number[] = [];
    const mode = 4;
    bits.push(0, 1, 0, 0);
    const charCountBits = [0, 0, 8, 8, 8, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0];
    for (let i = charCountBits[type] - 1; i >= 0; i--) {
      bits.push((text.length >> i) & 1);
    }
    for (const ch of text) {
      const code = ch.charCodeAt(0);
      for (let i = 7; i >= 0; i--) {
        bits.push((code >> i) & 1);
      }
    }
    const totalBits = [0, 0, 152, 272, 440, 640, 864][type] || 152;
    bits.push(0, 0, 0, 0);
    while (bits.length < totalBits) {
      bits.push(1, 1, 1, 0, 1, 1, 0, 0);
    }
    return bits.slice(0, totalBits);
  }

  function placeData(modules: boolean[][], reserved: boolean[][], bits: number[], size: number) {
    let bitIndex = 0;
    let right = size - 1;
    let upward = true;
    while (right >= 0) {
      if (right === 6) right--;
      for (let i = 0; i < size; i++) {
        const row = upward ? size - 1 - i : i;
        for (let dx = 0; dx >= -1; dx--) {
          const col = right + dx;
          if (col < 0 || col >= size) continue;
          if (reserved[row][col]) continue;
          if (bitIndex < bits.length) {
            modules[row][col] = bits[bitIndex] === 1;
            bitIndex++;
          }
        }
      }
      upward = !upward;
      right -= 2;
    }
  }

  function applyMask(modules: boolean[][], reserved: boolean[][], mask: number, size: number) {
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (reserved[r][c]) continue;
        let invert = false;
        switch (mask) {
          case 0: invert = (r + c) % 2 === 0; break;
          case 1: invert = r % 2 === 0; break;
          case 2: invert = c % 3 === 0; break;
          case 3: invert = (r + c) % 3 === 0; break;
          case 4: invert = (Math.floor(r/2) + Math.floor(c/3)) % 2 === 0; break;
          case 5: invert = (r*c)%2 + (r*c)%3 === 0; break;
          case 6: invert = ((r*c)%2 + (r*c)%3) % 2 === 0; break;
          case 7: invert = ((r+c)%2 + (r*c)%3) % 2 === 0; break;
        }
        if (invert) modules[r][c] = !modules[r][c];
      }
    }
  }

  function placeFormatInfo(modules: boolean[][], mask: number, size: number) {
    const formatBits = [0,0,1,0,1,0,0,0,0,0,1,0,0,1,0];
    let bitIndex = 0;
    for (let i = 0; i < 6; i++) modules[8][i] = formatBits[bitIndex++] === 1;
    modules[8][7] = formatBits[bitIndex++] === 1;
    modules[8][8] = formatBits[bitIndex++] === 1;
    modules[7][8] = formatBits[bitIndex++] === 1;
    for (let i = 5; i >= 0; i--) modules[i][8] = formatBits[bitIndex++] === 1;
  }
</script>

<canvas bind:this={canvas} width="200" height="200" style="image-rendering: pixelated;"></canvas>
