import os
import time
import wave
import asyncio
import threading
import queue
from pathlib import Path
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, jsonify
import websockets
import subprocess
import sys




HOST_HTTP = "0.0.0.0"
PORT_HTTP = 8080

HOST_WS = "0.0.0.0"
PORT_WS = 8765
PATH_AUDIO = "/audio"
PATH_DEVICE = "/device"

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2

TEACHER_PASSWORD = "1234"
SECRET_KEY = "CHANGE_ME"

BASE = Path(__file__).resolve().parent
RECORDINGS_DIR = BASE / "recordings"
TMP_DIR = BASE / "tmp_pcm"
CLEAN_DIR = RECORDINGS_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
TEXTS_DIR = RECORDINGS_DIR / "texts"
SUMMARY_DIR = TEXTS_DIR / "summery"
SPEECH_DIR = TEXTS_DIR / "speech"

SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
SPEECH_DIR.mkdir(parents=True, exist_ok=True)


app = Flask(__name__, static_folder=str(BASE / "static"), template_folder=str(BASE / "templates"))
app.secret_key = SECRET_KEY

state = {"device_connected": False, "recording": False}
cmd_queue: "queue.Queue[str]" = queue.Queue()

def resolve_text_file(kind: str, wav_name: str) -> Path | None:
    base_dir = SUMMARY_DIR if kind == "summery" else SPEECH_DIR if kind == "speech" else None
    if base_dir is None:
        return None

    candidates = []
    candidates.append(base_dir / wav_name)
    candidates.append(base_dir / f"{wav_name}.txt")
    if wav_name.lower().endswith(".wav"):
        candidates.append(base_dir / (wav_name[:-4] + ".txt"))

    for p in candidates:
        if p.exists() and p.is_file():
            return p

    return None



def is_teacher():
    return session.get("teacher_ok") is True

def list_wavs(folder: Path, prefix: str = "", q: str = "", sort: str = "new"):
    q = (q or "").strip().lower()

    out = []
    for p in folder.glob("*.wav"):
        name = p.name
        if q and q not in name.lower():
            continue

        st = p.stat()
        out.append({
            "name": name,
            "url": f"{prefix}{name}",
            "ts": st.st_mtime,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            "size": f"{st.st_size//1024} KB",
        })

    if sort == "old":
        out.sort(key=lambda x: x["ts"])
    elif sort == "name":
        out.sort(key=lambda x: x["name"].lower())
    else:
        out.sort(key=lambda x: x["ts"], reverse=True)

    return out


@app.get("/run_speech")
def run_speech_page():
    return """
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>در حال بارگیری...</title>
  <style>
    body{font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
    .box{max-width:520px;width:92vw;border:1px solid #ddd;border-radius:12px;padding:18px}
    .t{font-weight:900;margin-bottom:10px}
    .m{color:#444;line-height:1.8}
    pre{background:#f7f7f7;border:1px solid #eee;border-radius:10px;padding:10px}
  </style>
</head>
<body>
  <div class="box">
    <div class="t">در حال بارگیری…</div>
    <div class="m">پردازش در حال اجراست. لطفاً این صفحه را نبندید.</div>
  </div>

  <script>
    (async () => {
      const box = document.querySelector('.box');
      const msg = document.createElement('pre');
      msg.style.whiteSpace = 'pre-wrap';
      msg.style.marginTop = '12px';
      msg.style.maxHeight = '70vh';
      msg.style.overflow = 'auto';
      box.appendChild(msg);

      try {
        const res = await fetch('/api/run_speech', { method: 'POST' });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || !data.ok) {
          msg.textContent =
            "خطا در اجرای speech.py\\n\\n" +
            (data.error ? ("ERROR: " + data.error + "\\n\\n") : "") +
            (data.stderr ? ("STDERR:\\n" + data.stderr + "\\n\\n") : "") +
            (data.stdout ? ("STDOUT:\\n" + data.stdout) : "");
          return;
        }

        window.close();
      } catch (e) {
        msg.textContent = "خطا: " + (e?.message || e);
      }
    })();
  </script>
</body>
</html>
"""


@app.post("/api/run_speech")
def api_run_speech():
    try:
        script_path = str((BASE / "speech.py").resolve())

        p = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=str(BASE),
        )

        return jsonify({
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout or "",
            "stderr": p.stderr or "",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



@app.get("/api/text/<kind>")
def api_text(kind):
    wav_name = request.args.get("file", "")
    if not wav_name:
        return jsonify({"ok": False, "error": "missing file"}), 400

    p = resolve_text_file(kind, wav_name)
    if p is None:
        return jsonify({"ok": False, "error": "not found"}), 404

    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "text": txt, "name": p.name})

@app.get("/")
def home():
    return render_template("home.html")

@app.get("/student")
def student():
    q = request.args.get("q", "")
    sort = request.args.get("sort", "new")

    left_files = list_wavs(RECORDINGS_DIR, prefix="", q=q, sort=sort)
    right_files = list_wavs(CLEAN_DIR, prefix="clean/", q=q, sort=sort)

    return render_template(
        "student.html",
        q=q,
        sort=sort,
        left_files=left_files,
        right_files=right_files,
    )


@app.get("/recordings/<path:filename>")
def serve_recording(filename):
    full = RECORDINGS_DIR / filename
    if not full.exists():
        abort(404)
    return send_from_directory(str(RECORDINGS_DIR), filename)

@app.route("/teacher", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        if (request.form.get("password") or "") == TEACHER_PASSWORD:
            session["teacher_ok"] = True
            return redirect("/teacher/panel")
    return render_template("teacher_login.html")

@app.get("/teacher/panel")
def teacher_panel():
    if not is_teacher():
        return redirect("/teacher")
    return render_template("teacher_panel.html")

@app.get("/teacher/logout")
def teacher_logout():
    session.clear()
    return redirect("/")

@app.post("/api/start")
def api_start():
    if not is_teacher():
        return jsonify(ok=False), 401
    if not state["device_connected"]:
        return jsonify(ok=False, error="device disconnected"), 503
    cmd_queue.put("START")
    state["recording"] = True
    return jsonify(ok=True)

@app.post("/api/stop")
def api_stop():
    if not is_teacher():
        return jsonify(ok=False), 401
    if not state["device_connected"]:
        return jsonify(ok=False, error="device disconnected"), 503
    cmd_queue.put("STOP")
    state["recording"] = False
    return jsonify(ok=True)

@app.get("/api/status")
def api_status():
    return jsonify(state)

def ts():
    return time.strftime("%Y%m%d_%H%M%S")

def finalize_pcm_to_wav(pcm_path: Path):
    if not pcm_path or not pcm_path.exists() or pcm_path.stat().st_size == 0:
        return None

    wav_path = RECORDINGS_DIR / (pcm_path.stem + ".wav")
    pcm = pcm_path.read_bytes()

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)

    return wav_path

async def audio_handler(ws):
    f = None
    pcm_path = None

    async def close_take():
        nonlocal f, pcm_path
        if f:
            try:
                f.close()
            except Exception:
                pass
            wav = finalize_pcm_to_wav(pcm_path)
            print("[AUDIO] finalized:", wav.name if wav else None)
        f = None
        pcm_path = None

    try:
        async for msg in ws:
            if isinstance(msg, str):
                cmd = msg.strip().upper()
                if cmd == "START":
                    await close_take()
                    pcm_path = TMP_DIR / f"{ts()}.pcm"
                    f = open(pcm_path, "wb")
                    print("[AUDIO] START ->", pcm_path.name)
                elif cmd == "STOP":
                    print("[AUDIO] STOP")
                    await close_take()
                continue

            if f:
                f.write(msg)

    except Exception as e:
        print("[AUDIO] ERROR:", type(e), e)
    finally:
        await close_take()
        print("[AUDIO] DISCONNECTED")

async def device_handler(ws):
    print("[DEVICE] CONNECTED")
    state["device_connected"] = True

    async def sender():
        while True:
            cmd = await asyncio.to_thread(cmd_queue.get)
            try:
                await ws.send(cmd)
                print("[DEVICE] SEND:", cmd)
            except Exception:
                break

    send_task = asyncio.create_task(sender())

    try:
        async for msg in ws:
            if isinstance(msg, str):
                txt = msg.strip()
                if txt == "REC:ON":
                    state["recording"] = True
                elif txt == "REC:OFF":
                    state["recording"] = False

    except Exception as e:
        print("[DEVICE] ERROR:", type(e), e)
    finally:
        send_task.cancel()
        state["device_connected"] = False
        state["recording"] = False
        print("[DEVICE] DISCONNECTED")

def get_ws_path(ws):
    p = getattr(ws, "path", None)
    if p:
        return p
    req = getattr(ws, "request", None)
    if req is not None:
        return getattr(req, "path", None)
    return None

async def ws_router(ws):
    path = get_ws_path(ws)
    if path == PATH_AUDIO:
        await audio_handler(ws)
    elif path == PATH_DEVICE:
        await device_handler(ws)
    else:
        await ws.close(code=1008, reason="Invalid path")

def ws_thread():
    async def runner():
        async with websockets.serve(
            ws_router,
            HOST_WS,
            PORT_WS,
            max_size=None,
            ping_interval=None,
            ping_timeout=None
        ):
            print(f"WS AUDIO  ws://{HOST_WS}:{PORT_WS}{PATH_AUDIO}")
            print(f"WS DEVICE ws://{HOST_WS}:{PORT_WS}{PATH_DEVICE}")
            await asyncio.Future()

    asyncio.run(runner())

if __name__ == "__main__":
    threading.Thread(target=ws_thread, daemon=True).start()
    print(f"HTTP http://{HOST_HTTP}:{PORT_HTTP}")
    app.run(host=HOST_HTTP, port=PORT_HTTP, debug=False)
