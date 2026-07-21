import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SESSION_DIR = join(__dirname, 'session');
const STATUS_FILE = join(__dirname, 'status.json');
const PROCESSED_FILE = join(__dirname, 'processed.json');
const PIPELINES_FILE = join(__dirname, 'pipelines.json');
const GROQ_API_KEY = process.env.GROQ_API_KEY || '';
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';

if (!existsSync(SESSION_DIR)) mkdirSync(SESSION_DIR, { recursive: true });

const logger = pino({ level: 'silent' });

let processedSet = new Set();
if (existsSync(PROCESSED_FILE)) {
  try { processedSet = new Set(JSON.parse(readFileSync(PROCESSED_FILE, 'utf8'))); } catch {}
}

function saveProcessed() {
  const arr = [...processedSet];
  if (arr.length > 5000) arr.splice(0, arr.length - 3000);
  writeFileSync(PROCESSED_FILE, JSON.stringify(arr));
}

function loadPipelines() {
  if (!existsSync(PIPELINES_FILE)) return [];
  try { return JSON.parse(readFileSync(PIPELINES_FILE, 'utf8')); } catch { return []; }
}

function loadPrompt(promptFile) {
  const fp = join(__dirname, promptFile || 'prompt.txt');
  if (existsSync(fp)) return readFileSync(fp, 'utf8').trim();
  return 'You are a WhatsApp product post editor. Add markup to the price. Remove links. Add footer. Return ONLY the final edited post.';
}

function msgHash(text) {
  return text.replace(/\s+/g, ' ').trim().substring(0, 80);
}

function writeStatus(overrides = {}) {
  const pipelines = loadPipelines();
  const base = {
    last_update: new Date().toISOString(),
    pipelines: pipelines.map(p => ({
      id: p.id, name: p.name, enabled: p.enabled,
      source_groups: p.source_groups, destination_group: p.destination_group, markup: p.markup,
    })),
    processed_count: processedSet.size,
    ...overrides,
  };
  writeFileSync(STATUS_FILE, JSON.stringify(base, null, 2));
}

async function rewriteCaption(caption, prompt) {
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
          { role: 'system', content: prompt },
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

async function main() {
  console.log('Starting ProductFlow Relay (Baileys)...');
  const pipelines = loadPipelines().filter(p => p.enabled);
  console.log(`Loaded ${pipelines.length} enabled pipelines`);

  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: true,
    logger,
    browser: ['ProductFlow Relay', 'Chrome', '130.0'],
    markOnlineOnConnect: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log('Scan QR code with your phone!');
      writeStatus({ connected: false, mode: 'waiting_for_qr' });
    }
    if (connection === 'close') {
      const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
      if (reason === DisconnectReason.loggedOut) {
        console.log('Logged out. Delete session/ folder and restart.');
        writeStatus({ connected: false, error: 'Logged out' });
        process.exit(1);
      }
      console.log(`Connection closed (${reason}). Reconnecting...`);
      writeStatus({ connected: false, mode: 'reconnecting' });
    }
    if (connection === 'open') {
      console.log('Connected to WhatsApp!');
      writeStatus({ connected: true, mode: 'live' });
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      if (!msg.message) continue;

      const chatId = msg.key.remoteJid;
      if (!chatId.endsWith('@g.us')) continue;

      const text = msg.message.conversation
        || msg.message.extendedTextMessage?.text
        || '';
      if (!text || text.length < 10) continue;

      const hash = msgHash(text);
      if (processedSet.has(hash)) continue;

      let groupName = '';
      try {
        const meta = await sock.groupMetadata(chatId);
        groupName = meta.subject || '';
      } catch {}

      const currentPipelines = loadPipelines().filter(p => p.enabled);
      for (const pipeline of currentPipelines) {
        const match = pipeline.source_groups?.some(g => {
          const gLower = g.toLowerCase().trim();
          return groupName.toLowerCase().includes(gLower)
            || gLower.includes(groupName.toLowerCase());
        });

        if (!match) continue;

        console.log(`[${pipeline.name}] ${groupName}: ${text.substring(0, 60)}...`);
        const prompt = loadPrompt(pipeline.prompt_file);
        const rewritten = await rewriteCaption(text, prompt);
        processedSet.add(hash);
        saveProcessed();

        if (rewritten !== text && pipeline.destination_group) {
          try {
            const destJid = pipeline.destination_group.endsWith('@g.us')
              ? pipeline.destination_group
              : `${pipeline.destination_group}@g.us`;
            await sock.sendMessage(destJid, { text: rewritten });
            console.log(`[${pipeline.name}] Sent to ${pipeline.destination_group}`);
          } catch (e) {
            console.error(`[${pipeline.name}] Send failed:`, e.message);
          }
        }
      }
      writeStatus({ connected: true, mode: 'live', last_scan: new Date().toISOString() });
    }
  });

  writeStatus({ connected: false, mode: 'starting' });
  console.log('Relay running. Press Ctrl+C to stop.');
  process.on('SIGINT', () => process.exit(0));
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
