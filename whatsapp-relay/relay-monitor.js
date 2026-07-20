import { createRequire } from 'module';
import { readFileSync, writeFileSync, existsSync } from 'fs';
const require = createRequire(import.meta.url);

let puppeteer;
try {
  puppeteer = await import('puppeteer-core');
} catch {
  puppeteer = require('puppeteer-core');
}
const pptr = puppeteer.default || puppeteer;

const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
const SOURCE_GROUPS = (process.env.SOURCE_GROUPS || '').split(',').filter(Boolean);
const DESTINATION_GROUP = process.env.DESTINATION_GROUP || '';
const MARKUP = parseInt(process.env.MARKUP || '1000', 10);
const PROCESSED_FILE = '/home/pi/ProductFlow/whatsapp-relay/processed.json';

let processedSet = new Set();
if (existsSync(PROCESSED_FILE)) {
  try { processedSet = new Set(JSON.parse(readFileSync(PROCESSED_FILE, 'utf8'))); } catch {}
}

function saveProcessed() {
  const arr = [...processedSet];
  if (arr.length > 2000) arr.splice(0, arr.length - 2000);
  writeFileSync(PROCESSED_FILE, JSON.stringify(arr));
}

function msgHash(text) {
  return text.replace(/\s+/g, ' ').trim().substring(0, 80);
}

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

async function navigateToGroup(page, groupName) {
  await page.evaluate(async (name) => {
    const searchBox = document.querySelector('[data-tab="3"], [data-testid="chat-list-search"]');
    if (!searchBox) throw new Error('Search box not found');
    searchBox.focus();
    searchBox.textContent = '';
    document.execCommand('insertText', false, name);
    await new Promise(r => setTimeout(r, 1500));
    const chat = document.querySelector('[data-testid="chat-list-item"], [role="listitem"]');
    if (chat) chat.click();
    await new Promise(r => setTimeout(r, 1000));
  }, groupName);
}

async function captureVisibleMessages(page) {
  return await page.evaluate(() => {
    const msgs = [];
    const panels = document.querySelectorAll('[data-testid="msg-container"]');
    panels.forEach(panel => {
      const textEl = panel.querySelector('[data-testid="message-text"], .selectable-text');
      const inbound = panel.querySelector('.message-in');
      const timeEl = panel.querySelector('[data-testid="msg-meta"] span, span._ao3q');
      if (textEl && inbound) {
        msgs.push({
          text: textEl.textContent.trim(),
          time: timeEl ? timeEl.textContent.trim() : '',
        });
      }
    });
    return msgs;
  });
}

async function scrollUpAndCapture(page, scrolls = 5) {
  let allMsgs = [];
  for (let i = 0; i < scrolls; i++) {
    const msgs = await captureVisibleMessages(page);
    allMsgs = [...msgs, ...allMsgs];
    await page.evaluate(() => {
      const container = document.querySelector('[data-testid="msg-list"]');
      if (container) container.scrollTop = 0;
    });
    await new Promise(r => setTimeout(r, 800));
  }
  return allMsgs;
}

async function sendToDestination(page, text) {
  if (!DESTINATION_GROUP) return;
  await navigateToGroup(page, DESTINATION_GROUP);
  await new Promise(r => setTimeout(r, 1000));
  await page.evaluate(async (msg) => {
    const input = document.querySelector('[contenteditable="true"][data-tab="10"]');
    if (!input) throw new Error('No chat input found');
    input.focus();
    input.textContent = msg;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(r => setTimeout(r, 200));
    const sendBtn = document.querySelector('[data-icon="send"]');
    if (sendBtn) sendBtn.click();
  }, text);
  await new Promise(r => setTimeout(r, 1000));
  console.log(`Sent to ${DESTINATION_GROUP}: ${text.substring(0, 50)}...`);
}

async function catchUpPending(page) {
  if (SOURCE_GROUPS.length === 0) {
    console.log('No SOURCE_GROUPS configured, skipping catch-up');
    return;
  }

  console.log('=== Catching up on pending messages ===');
  for (const group of SOURCE_GROUPS) {
    console.log(`Opening source group: ${group}`);
    try {
      await navigateToGroup(page, group);
      await new Promise(r => setTimeout(r, 2000));

      console.log('Scrolling up to load recent messages...');
      const messages = await scrollUpAndCapture(page, 8);
      console.log(`Found ${messages.length} messages in ${group}`);

      let newCount = 0;
      for (const msg of messages) {
        if (msg.text.length < 10) continue;
        const hash = msgHash(msg.text);
        if (processedSet.has(hash)) continue;

        console.log(`Catch-up: ${msg.text.substring(0, 60)}...`);
        const rewritten = await rewriteCaption(msg.text);
        processedSet.add(hash);
        newCount++;

        if (rewritten !== msg.text && DESTINATION_GROUP) {
          await sendToDestination(page, rewritten);
          await new Promise(r => setTimeout(r, 2000));
        }
      }
      saveProcessed();
      console.log(`Processed ${newCount} new messages from ${group}`);
    } catch (e) {
      console.error(`Catch-up failed for ${group}:`, e.message);
    }
  }
  console.log('=== Catch-up complete ===');
}

async function main() {
  console.log('Starting ProductFlow Relay Monitor...');
  console.log(`Source groups: ${SOURCE_GROUPS.length ? SOURCE_GROUPS.join(', ') : 'ALL'}`);
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
  let connected = false;
  for (let i = 0; i < 60 && !connected; i++) {
    await page.screenshot({ path: '/tmp/whatsapp-qr.png' });
    console.log(`Screenshot saved — attempt ${i + 1}/60`);

    const chatList = await page.$('div[aria-label="Chat list"], [data-testid="chat-list"], [data-testid="chat-list-search"]');
    if (chatList) {
      connected = true;
      console.log('WhatsApp Web connected!');
      break;
    }
    await new Promise(r => setTimeout(r, 5000));
  }

  if (!connected) {
    console.error('Failed to connect to WhatsApp Web after 5 minutes');
    await browser.close();
    process.exit(1);
  }

  await catchUpPending(page);

  console.log('Starting live monitoring...');
  setInterval(async () => {
    try {
      for (const group of SOURCE_GROUPS) {
        await navigateToGroup(page, group);
        await new Promise(r => setTimeout(r, 2000));

        const messages = await captureVisibleMessages(page);
        for (const msg of messages) {
          if (msg.text.length < 10) continue;
          const hash = msgHash(msg.text);
          if (processedSet.has(hash)) continue;

          console.log(`Live: ${msg.text.substring(0, 60)}...`);
          const rewritten = await rewriteCaption(msg.text);
          processedSet.add(hash);

          if (rewritten !== msg.text && DESTINATION_GROUP) {
            await sendToDestination(page, rewritten);
            await new Promise(r => setTimeout(r, 2000));
          }
        }
        saveProcessed();
      }
    } catch (e) {
      console.error('Monitor loop error:', e.message);
    }
  }, 30000);

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
