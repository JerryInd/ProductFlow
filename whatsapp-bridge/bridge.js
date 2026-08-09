import { makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from "@whiskeysockets/baileys";
import { createServer } from "http";
import qrcode from "qrcode-terminal";
import QRCodeLib from "qrcode";
import sharp from "sharp";
import { existsSync, mkdirSync, writeFileSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SESSION_DIR = join(__dirname, "..", "sessions");
const MEDIA_DIR = join(__dirname, "..", "media-cache");
const API_BASE = process.env.API_BASE || "http://localhost:8000";
const MAX_RETRIES = 5;
const PROCESSED_FILE = join(__dirname, "processed.json");

const BRIDGE_PORT = process.env.BRIDGE_PORT || 8001;
const STATUS_FILE = join(__dirname, "relay-status.json");

if (!existsSync(SESSION_DIR)) mkdirSync(SESSION_DIR, { recursive: true });
if (!existsSync(MEDIA_DIR)) mkdirSync(MEDIA_DIR, { recursive: true });

let processedSet = new Set();
if (existsSync(PROCESSED_FILE)) {
  try { processedSet = new Set(JSON.parse(readFileSync(PROCESSED_FILE, "utf8"))); } catch {}
}

function saveProcessed() {
  const arr = [...processedSet];
  if (arr.length > 5000) arr.splice(0, arr.length - 3000);
  writeFileSync(PROCESSED_FILE, JSON.stringify(arr));
}

function msgHash(text) {
  return text.replace(/\s+/g, " ").trim().substring(0, 80);
}

async function resizeImage(buffer, maxBytes = 4.5 * 1024 * 1024) {
  if (buffer.length <= maxBytes) return buffer;
  try {
    const img = sharp(buffer);
    const meta = await img.metadata();
    let w = meta.width;
    let h = meta.height;
    const ratio = Math.sqrt(maxBytes / buffer.length) * 0.9;
    w = Math.round(w * ratio);
    h = Math.round(h * ratio);
    return await img.resize(w, h).jpeg({ quality: 80 }).toBuffer();
  } catch (e) {
    console.error("[Relay] resize failed:", e.message);
    return buffer;
  }
}

function writeRelayStatus(overrides = {}) {
  const base = {
    last_update: new Date().toISOString(),
    ...overrides,
  };
  try {
    writeFileSync(STATUS_FILE, JSON.stringify(base, null, 2));
    console.log("[Relay] Status written:", STATUS_FILE);
  } catch (e) {
    console.error("[Relay] Failed to write status:", e.message);
  }
}

let sock = null;
let currentQR = null;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function randomDelay(min = 15000, max = 30000) {
  const ms = Math.floor(Math.random() * (max - min + 1)) + min;
  console.log(`[Relay] Random delay: ${(ms / 1000).toFixed(1)}s`);
  return sleep(ms);
}

let globalSendCount = 0;
let hourlySendCount = 0;
let hourlyResetTime = Date.now();
const MAX_PER_HOUR = 150;

async function apiPost(path, body) {
  for (let i = 0; i < MAX_RETRIES; i++) {
    try {
      const res = await fetch(`${API_BASE}/api/whatsapp${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) return;
    } catch {}
    await sleep(Math.min(1000 * 2 ** i, 10000));
  }
}

async function relayProcess(text, groupName, groupId) {
  try {
    const res = await fetch(`${API_BASE}/api/relay/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, group_name: groupName, group_id: groupId }),
      signal: AbortSignal.timeout(30000),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Relay process failed:", e.message);
  }
  return null;
}

async function saveToRetryQueue(item) {
  try {
    const res = await fetch(`${API_BASE}/api/relay/queue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) console.log("[Relay] Saved to retry queue");
  } catch (e) {
    console.error("[Relay] Failed to save to retry queue:", e.message);
  }
}

async function processRelay(m, groupId) {
  const msg = m.message;
  if (!msg) return;

  // Hourly rate limit
  if (Date.now() - hourlyResetTime > 3600000) {
    hourlySendCount = 0;
    hourlyResetTime = Date.now();
  }
  if (hourlySendCount >= MAX_PER_HOUR) {
    console.log(`[Relay] Hourly limit reached (${MAX_PER_HOUR}), skipping`);
    return;
  }

  const text = msg.conversation
    || msg.extendedTextMessage?.text
    || msg.imageMessage?.caption
    || msg.videoMessage?.caption
    || "";
  const hasMedia = !!(msg.imageMessage || msg.videoMessage);
  const hasCaption = !!(msg.imageMessage?.caption || msg.videoMessage?.caption);

  if (!text && !hasMedia) return;

  const relayText = text || "(media)";
  console.log(`[Relay] Processing: group=${groupId} text="${relayText.slice(0, 50)}" media=${hasMedia}`);

  let groupName = "";
  try {
    const meta = await Promise.race([
      sock.groupMetadata(groupId),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), 10000)),
    ]);
    groupName = meta.subject || "";
    console.log(`[Relay] Group name: ${groupName}`);
  } catch (e) {
    console.error("[Relay] groupMetadata failed:", e.message);
    groupName = groupId;
  }

  let result;
  try {
    result = await relayProcess(relayText, groupName, groupId);
    console.log("[Relay] API response:", JSON.stringify(result).slice(0, 200));
  } catch (e) {
    console.error("[Relay] API call failed:", e.message);
    return;
  }
  if (!result || !result.matched) {
    console.log("[Relay] No pipeline matched");
    return;
  }

  let sendCount = 0;
  for (const pipeline of result.pipelines) {
    const destIds = pipeline.dest_group_ids || [];
    if (destIds.length === 0) {
      console.log(`[Relay] ${pipeline.name}: no destination group configured`);
      continue;
    }
    for (const destJid of destIds) {
      try {
        if (hasMedia) {
          let mediaBuffer = null;
          for (let attempt = 0; attempt < 3; attempt++) {
            try {
              mediaBuffer = await downloadMediaMessage(m, "buffer", {});
              break;
            } catch (e) {
              console.error(`[Relay] Media download attempt ${attempt + 1} failed:`, e.message);
              if (attempt < 2) await new Promise(r => setTimeout(r, 2000));
            }
          }
          if (mediaBuffer) {
            try {
              if (sendCount > 0) await randomDelay(15000, 30000);
              if (globalSendCount > 0 && globalSendCount % 10 === 0) {
                const pauseMs = Math.floor(Math.random() * 180000) + 120000;
                console.log(`[Relay] Long pause after 10 messages: ${(pauseMs / 1000).toFixed(0)}s`);
                await sleep(pauseMs);
              }
              const caption = pipeline.rewritten || undefined;
              if (msg.imageMessage) {
                const resized = await resizeImage(mediaBuffer);
                await sock.sendMessage(destJid, { image: resized, ...(caption ? { caption } : {}) });
              } else if (msg.videoMessage) {
                await sock.sendMessage(destJid, { video: mediaBuffer, ...(caption ? { caption } : {}) });
              }
              sendCount++;
              globalSendCount++;
              hourlySendCount++;
              console.log(`[Relay] ${pipeline.name}: sent media to ${destJid}${caption ? ' with caption' : ''}`);
            } catch (e) {
              console.error(`[Relay] ${pipeline.name}: media send failed:`, e.message);
              if (e.message?.includes("429") || e.message?.includes("rate") || e.message?.includes("420")) {
                console.log(`[Relay] Rate limited, waiting 30s before retry...`);
                await new Promise(r => setTimeout(r, 30000));
                try {
                  const caption = pipeline.rewritten || undefined;
                  if (msg.imageMessage) {
                    const resized = await resizeImage(mediaBuffer);
                    await sock.sendMessage(destJid, { image: resized, ...(caption ? { caption } : {}) });
                  } else if (msg.videoMessage) {
                    await sock.sendMessage(destJid, { video: mediaBuffer, ...(caption ? { caption } : {}) });
                  }
                  sendCount++;
                  globalSendCount++;
                  hourlySendCount++;
                  console.log(`[Relay] ${pipeline.name}: retry sent media to ${destJid}`);
                } catch (e2) {
                  console.error(`[Relay] ${pipeline.name}: retry also failed:`, e2.message);
                  await saveToRetryQueue({
                    text: relayText,
                    group_name: groupName,
                    group_id: groupId,
                    has_media: hasMedia,
                    caption: pipeline.rewritten || "",
                    dest_group_ids: [destJid],
                    pipeline_name: pipeline.name,
                    error: e2.message,
                  });
                }
              }
            }
          } else {
            console.error(`[Relay] ${pipeline.name}: media download failed after 3 attempts`);
            await saveToRetryQueue({
              text: relayText,
              group_name: groupName,
              group_id: groupId,
              has_media: true,
              caption: pipeline.rewritten || "",
              dest_group_ids: [destJid],
              pipeline_name: pipeline.name,
              error: "Media download failed after 3 attempts",
            });
          }
        } else {
          if (sendCount > 0) await randomDelay(15000, 30000);
          if (globalSendCount > 0 && globalSendCount % 10 === 0) {
            const pauseMs = Math.floor(Math.random() * 180000) + 120000;
            console.log(`[Relay] Long pause after 10 messages: ${(pauseMs / 1000).toFixed(0)}s`);
            await sleep(pauseMs);
          }
          await sock.sendMessage(destJid, { text: pipeline.rewritten });
          sendCount++;
          globalSendCount++;
          hourlySendCount++;
          console.log(`[Relay] ${pipeline.name}: sent text to ${destJid}`);
        }
      } catch (e) {
        console.error(`[Relay] ${pipeline.name}: send to ${destJid} failed:`, e.message);
        await saveToRetryQueue({
          text: relayText,
          group_name: groupName,
          group_id: groupId,
          has_media: hasMedia,
          caption: pipeline.rewritten || "",
          dest_group_ids: [destJid],
          pipeline_name: pipeline.name,
          error: e.message,
        });
      }
    }
  }
  writeRelayStatus({ connected: true, mode: "live", processed_count: processedSet.size, last_scan: new Date().toISOString() });
}

async function startBot() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    auth: state,
    browser: ["ProductFlow AI", "Chrome", "120.0.0"],
    syncFullHistory: false,
    markOnlineOnConnect: false,
    maxMsgRetryCount: 2,
    connectTimeoutMs: 60000,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      currentQR = qr;
      qrcode.generate(qr, { small: true });
      try {
        const qrImage = await QRCodeLib.toDataURL(qr, { errorCorrectionLevel: 'L', margin: 2, width: 300 });
        await apiPost("/qr", { qr, qr_image: qrImage });
      } catch (e) {
        console.error("QR image generation failed:", e.message);
        await apiPost("/qr", { qr });
      }
    }
    if (connection === "open") {
      const phone = sock.user?.id?.split(":")[0] || null;
      console.log("WhatsApp connected:", phone);
      await apiPost("/status", { status: "connected", phone_number: phone });
      writeRelayStatus({ connected: true, mode: "live" });
    }
    if (connection === "close") {
      const reason = lastDisconnect?.error?.output?.statusCode;
      if (reason === DisconnectReason.loggedOut) {
        console.log("Logged out, clearing session...");
        const { rmSync } = await import("fs");
        rmSync(SESSION_DIR, { recursive: true, force: true });
      }
      writeRelayStatus({ connected: false, mode: "reconnecting" });
      const delay = reason === DisconnectReason.restartRequired ? 1000 : 5000;
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(startBot, delay);
    }
  });

  sock.ev.on("messages.upsert", async (msg) => {
    for (const m of msg.messages) {
      if (!m.key || m.key.fromMe) continue;
      const groupId = m.key.remoteJid;
      if (!groupId?.endsWith("@g.us")) continue;
      try {
        await processRelay(m, groupId);
      } catch (e) {
        console.error("[Relay] Error:", e.message);
      }
    }
  });
}

async function processMessage(m, groupId) {
  const msg = m.message;
  if (!msg) return;

  const msgId = m.key.id;
  if (!msgId) return;

  const isImage = !!msg.imageMessage;
  const isVideo = !!msg.videoMessage;
  const text =
    msg.conversation ||
    msg.extendedTextMessage?.text ||
    msg.imageMessage?.caption ||
    msg.videoMessage?.caption ||
    "";

  let type = "text";
  let mediaPath = "";

  if (isImage || isVideo) {
    type = isImage ? "image" : "video";
    try {
      const buffer = await downloadMediaMessage(m, "buffer", {});
      const ext = isImage ? ".jpg" : ".mp4";
      const filename = `${Date.now()}-${msgId}${ext}`;
      const filepath = join(MEDIA_DIR, filename);
      writeFileSync(filepath, buffer);
      mediaPath = filepath;
      console.log(`Downloaded ${type}: ${filename}`);
    } catch (err) {
      console.error(`Failed to download ${type}:`, err.message);
      type = "other";
    }
  } else if (!text) {
    type = "other";
  }

  const payload = {
    id: msgId,
    type,
    text,
    media_path: mediaPath,
    from_: groupId,
    timestamp: m.messageTimestamp || Math.floor(Date.now() / 1000),
  };

  await apiPost("/message", payload);
}

startBot();
writeRelayStatus({ connected: false, mode: "starting" });

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === "GET" && url.pathname === "/groups") {
    if (!sock) {
      res.writeHead(400);
      res.end(JSON.stringify({ ok: false, error: "not connected" }));
      return;
    }
    try {
      const result = await sock.groupFetchAllParticipating();
      const groups = Object.entries(result).map(([gid, meta]) => ({
        group_id: gid,
        group_name: meta.subject || gid,
        member_count: meta.participants?.length || 0,
      }));
      res.writeHead(200);
      res.end(JSON.stringify({ ok: true, groups }));
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  if (req.method === "GET" && url.pathname === "/qr-image") {
    if (!currentQR) {
      res.writeHead(404);
      res.end(JSON.stringify({ ok: false, error: "no QR available" }));
      return;
    }
    try {
      const pngBuffer = await QRCodeLib.toBuffer(currentQR, { errorCorrectionLevel: 'L', margin: 2, width: 300 });
      res.writeHead(200, { "Content-Type": "image/png" });
      res.end(pngBuffer);
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  if (req.method === "GET" && url.pathname === "/chats") {
    if (!sock) {
      res.writeHead(400);
      res.end(JSON.stringify({ ok: false, error: "not connected" }));
      return;
    }
    try {
      const chats = (sock.store?.chats?.all() || [])
        .filter(c => !c.id?.endsWith("@g.us"))
        .sort((a, b) => (b.conversationTimestamp || 0) - (a.conversationTimestamp || 0))
        .slice(0, 50)
        .map(c => ({
          jid: c.id,
          name: c.name || c.notify || c.id?.split("@")[0] || "",
          lastMessage: c.messages?.[c.messages.length - 1]?.message?.conversation || "",
          timestamp: c.conversationTimestamp || 0,
        }));
      res.writeHead(200);
      res.end(JSON.stringify({ ok: true, chats }));
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/join-invite") {
    if (!sock) {
      res.writeHead(400);
      res.end(JSON.stringify({ ok: false, error: "not connected" }));
      return;
    }
    let b = "";
    for await (const chunk of req) b += chunk;
    let d;
    try { d = JSON.parse(b); } catch { res.writeHead(400); res.end("Invalid JSON"); return; }
    const code = d.code;
    if (!code) { res.writeHead(400); res.end(JSON.stringify({ ok: false, error: "no code" })); return; }
    try {
      const result = await sock.groupAcceptInvite(code);
      res.writeHead(200);
      res.end(JSON.stringify({ ok: true, group_id: result }));
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  if (req.method !== "POST") {
    res.writeHead(405);
    res.end("Method not allowed");
    return;
  }

  let body = "";
  for await (const chunk of req) body += chunk;

  let data;
  try {
    data = JSON.parse(body);
  } catch {
    res.writeHead(400);
    res.end("Invalid JSON");
    return;
  }

  const { group_id, text, media_path, caption } = data;

  if (!group_id || !sock) {
    res.writeHead(400);
    res.end(JSON.stringify({ ok: false, error: "no socket or group_id" }));
    return;
  }

  try {
    if (media_path && existsSync(media_path)) {
      const buffer = readFileSync(media_path);
      const isVideo = media_path.endsWith(".mp4");
      const mimetype = isVideo ? "video/mp4" : "image/jpeg";
      const msg = {
        image: isVideo ? undefined : buffer,
        video: isVideo ? buffer : undefined,
        caption: caption || text || "",
        mimetype,
      };
      if (!isVideo) delete msg.video;
      if (isVideo) delete msg.image;
      await sock.sendMessage(group_id, msg);
    } else {
      await sock.sendMessage(group_id, { text: text || "" });
    }
    console.log(`Sent to ${group_id}: ${text || media_path}`);
    res.writeHead(200);
    res.end(JSON.stringify({ ok: true }));
  } catch (err) {
    console.error("Send failed:", err.message);
    res.writeHead(500);
    res.end(JSON.stringify({ ok: false, error: err.message }));
  }
});

server.listen(BRIDGE_PORT, () => {
  console.log(`Bridge API listening on port ${BRIDGE_PORT}`);
});

process.on("SIGINT", async () => {
  if (sock) {
    sock.end(undefined);
    await sleep(500);
  }
  process.exit(0);
});

process.on("SIGTERM", () => process.exit(0));
