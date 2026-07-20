import { createRequire } from 'module';
const require = createRequire(import.meta.url);

let puppeteer;
try {
  puppeteer = await import('puppeteer-core');
} catch {
  puppeteer = require('puppeteer-core');
}
const pptr = puppeteer.default || puppeteer;

const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';
const PI_URL = process.env.PI_URL || 'http://localhost:8000';
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
const MONITORED_GROUPS = (process.env.MONITORED_GROUPS || '').split(',').filter(Boolean);
const DESTINATION_GROUP = process.env.DESTINATION_GROUP || '';
const MARKUP = parseInt(process.env.MARKUP || '1000', 10);

const REWRITE_PROMPT = `You are a WhatsApp product post editor.

MARKUP = ${MARKUP}

TASK

Edit the supplied WhatsApp product post by following these rules exactly.

RULES

1. Find the MAIN SELLING PRICE.
   The main selling price is usually:
   - The only product price in the post.
   - The price after words like Price, Rs, Rate, Available, Available@, Only.
   - The primary selling price of the product.

2. Ignore prices related to:
   - Shipping, OG Box, Indian Box, Accessories, Dust Cover, Invoice, Extra Charges, Any optional add-ons.

3. Extract only the numeric value of the main selling price.

4. Remove commas from the number if present.

5. Add MARKUP to the extracted price.

6. Replace ONLY the main selling price with the calculated price.

7. Preserve the original price format.

8. Remove every line that contains any of the following:
   - http, https, www, Place Orders, Product Direct Link, Order Here, Buy Now, Checkout, Cart, Store Link

9. Remove any empty blank lines created after deleting text.

10. Append this footer exactly:

━━━━━━━━━━━━━━
🔥 Perfect Deals 🔥
Premium Quality Products
📦 Pan India Shipping

WhatsApp:
+918169858589
https://chat.whatsapp.com/Khx2ym45DSy1AXfp3XtY86

Posted by |NotJerry|
━━━━━━━━━━━━━━

11. Do NOT change: Product title, Brand name, Description, Features, Specifications, Size, Quality, Emojis, Hashtags, Formatting, Existing line breaks.

12. Return ONLY the final edited WhatsApp post.`;

async function rewriteCaption(caption) {
  if (!GROQ_API_KEY) return caption;
  try {
    const resp = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GROQ_API_KEY}`,
        'Content-Type': 'application/json',
        'User-Agent': 'ProductFlow/1.0',
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        messages: [
          { role: 'system', content: REWRITE_PROMPT },
          { role: 'user', content: caption },
        ],
        max_tokens: 512,
        temperature: 0.3,
      }),
    });
    const data = await resp.json();
    return data.choices?.[0]?.message?.content?.trim() || caption;
  } catch (e) {
    console.error('Rewrite failed:', e.message);
    return caption;
  }
}

async function sendToWhatsApp(page, groupId, text) {
  try {
    const chatId = groupId.replace('@g.us', '@g.us');
    await page.evaluate(async (jid, msg) => {
      const chatInput = document.querySelector('[contenteditable="true"][data-tab="10"]');
      if (!chatInput) throw new Error('No chat input found');

      const searchBox = document.querySelector('[contenteditable="true"][data-tab="3"]');
      if (searchBox) {
        searchBox.focus();
        searchBox.textContent = '';
        document.execCommand('insertText', false, jid);
        await new Promise(r => setTimeout(r, 1000));
        const chat = document.querySelector(`[data-id="${jid}"]`);
        if (chat) chat.click();
        await new Promise(r => setTimeout(r, 500));
      }

      const input = document.querySelector('[contenteditable="true"][data-tab="10"]');
      if (input) {
        input.focus();
        input.textContent = msg;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        await new Promise(r => setTimeout(r, 200));
        const sendBtn = document.querySelector('[data-icon="send"]');
        if (sendBtn) sendBtn.click();
      }
    }, chatId, text);
    console.log(`Sent to ${groupId}: ${text.substring(0, 50)}...`);
  } catch (e) {
    console.error(`Failed to send to ${groupId}:`, e.message);
  }
}

async function main() {
  console.log('Starting ProductFlow Relay Monitor...');
  console.log(`Monitoring groups: ${MONITORED_GROUPS.length ? MONITORED_GROUPS.join(', ') : 'ALL'}`);
  console.log(`Destination: ${DESTINATION_GROUP || 'none (rewrite only)'}`);

  const browser = await pptr.launch({
    executablePath: CHROMIUM_PATH,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
      '--disable-extensions',
    ],
  });

  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Opening WhatsApp Web...');
  await page.goto('https://web.whatsapp.com', { waitUntil: 'networkidle2', timeout: 120000 });

  console.log('Waiting for QR code or login...');
  console.log('(Take a screenshot every 5s — saving to /tmp/whatsapp-qr.png)');

  let connected = false;
  for (let i = 0; i < 60 && !connected; i++) {
    await page.screenshot({ path: '/tmp/whatsapp-qr.png' });
    console.log(`Screenshot saved (/tmp/whatsapp-qr.png) — attempt ${i + 1}/60`);

    const chatList = await page.$('div[aria-label="Chat list"], [data-testid="chat-list"], [data-testid="chat-list-search"]');
    if (chatList) {
      connected = true;
      console.log('WhatsApp Web connected!');
      break;
    }

    const qr = await page.$('canvas');
    if (qr) {
      console.log('QR code visible — scan it now at http://192.168.1.107:9999/whatsapp-qr.png');
    }

    await new Promise(r => setTimeout(r, 5000));
  }

  if (!connected) {
    console.error('Failed to connect to WhatsApp Web after 5 minutes');
    await browser.close();
    process.exit(1);
  }

  const processedMsgs = new Set();

  setInterval(async () => {
    try {
      const messages = await page.evaluate(() => {
        const msgs = [];
        const panels = document.querySelectorAll('[data-testid="msg-container"]');
        panels.forEach(panel => {
          const textEl = panel.querySelector('[data-testid="message-text"], .selectable-text');
          const inbound = panel.querySelector('.message-in');
          if (textEl && inbound) {
            msgs.push({
              text: textEl.textContent.trim(),
              inbound: true,
            });
          }
        });
        return msgs.slice(-5);
      });

      for (const msg of messages) {
        const hash = msg.text.substring(0, 50);
        if (processedMsgs.has(hash)) continue;
        processedMsgs.add(hash);

        if (MONITORED_GROUPS.length > 0) {
          const activeChat = await page.evaluate(() => {
            const header = document.querySelector('[data-testid="conversation-header"]');
            return header?.textContent || '';
          });
          const matchesGroup = MONITORED_GROUPS.some(g => activeChat.includes(g));
          if (!matchesGroup) continue;
        }

        if (msg.text.length < 10) continue;

        console.log(`Captured: ${msg.text.substring(0, 80)}...`);
        const rewritten = await rewriteCaption(msg.text);

        if (rewritten !== msg.text) {
          console.log(`Rewritten (${rewritten.length} chars)`);
        }

        if (DESTINATION_GROUP) {
          await sendToWhatsApp(page, DESTINATION_GROUP, rewritten);
        }
      }

      if (processedMsgs.size > 500) {
        const arr = [...processedMsgs];
        processedMsgs.clear();
        arr.slice(-200).forEach(h => processedMsgs.add(h));
      }
    } catch (e) {
      console.error('Monitor loop error:', e.message);
    }
  }, 10000);

  console.log('Monitor running. Press Ctrl+C to stop.');
  process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await browser.close();
    process.exit(0);
  });
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
