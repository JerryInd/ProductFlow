import { makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from "@whiskeysockets/baileys";
import { createServer } from "http";
import qrcode from "qrcode-terminal";
import { existsSync, mkdirSync, writeFileSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SESSION_DIR = join(__dirname, "..", "sessions");
const MEDIA_DIR = join(__dirname, "..", "media-cache");
const API_BASE = process.env.API_BASE || "http://localhost:8000";
const MAX_RETRIES = 5;

const BRIDGE_PORT = process.env.BRIDGE_PORT || 8001;

if (!existsSync(SESSION_DIR)) mkdirSync(SESSION_DIR, { recursive: true });
if (!existsSync(MEDIA_DIR)) mkdirSync(MEDIA_DIR, { recursive: true });

let sock = null;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

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
      qrcode.generate(qr, { small: true });
      await apiPost("/qr", { qr });
    }
    if (connection === "open") {
      const phone = sock.user?.id?.split(":")[0] || null;
      console.log("WhatsApp connected:", phone);
      await apiPost("/status", { status: "connected", phone_number: phone });
    }
    if (connection === "close") {
      const reason = lastDisconnect?.error?.output?.statusCode;
      if (reason === DisconnectReason.loggedOut) {
        console.log("Logged out, clearing session...");
        const { rmSync } = await import("fs");
        rmSync(SESSION_DIR, { recursive: true, force: true });
      }
      const delay = reason === DisconnectReason.restartRequired ? 1000 : 5000;
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(startBot, delay);
    }
  });

  sock.ev.on("messages.upsert", async (msg) => {
    if (msg.type !== "notify") return;
    const promises = [];
    for (const m of msg.messages) {
      if (!m.key || m.key.fromMe) continue;
      const groupId = m.key.remoteJid;
      if (!groupId?.endsWith("@g.us")) continue;
      promises.push(processMessage(m, groupId));
    }
    await Promise.allSettled(promises);
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
