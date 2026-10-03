from __future__ import annotations

import hashlib
import json
import os
import queue
import threading
import urllib.request
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox


APP_DIR = Path(__file__).resolve().parent
MODEL_DIR = APP_DIR / "models"
MODEL_NAME = "gemma-4-E2B-it-Q4_0.gguf"
MODEL_URL = "https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF/resolve/main/" + MODEL_NAME
MODEL_SHA256 = "8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52"
CHUNK_SIZE = 32 * 1024 * 1024

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_model(progress, status):
    """Resumable, parallel HTTP range download; each completed chunk is kept for restart."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    target = MODEL_DIR / MODEL_NAME
    if target.exists():
        status("Checking existing model SHA-256…")
        if sha256_file(target) == MODEL_SHA256:
            progress(1.0)
            status("Model verified and ready.")
            return target
        target.unlink()

    request = urllib.request.Request(MODEL_URL, method="HEAD", headers={"User-Agent": "HyperCoder/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length", "0"))
        accepts_ranges = response.headers.get("Accept-Ranges", "").lower() == "bytes"
    if not total:
        raise RuntimeError("The model host did not provide a file size; download cannot safely resume.")

    chunks = (total + CHUNK_SIZE - 1) // CHUNK_SIZE
    chunk_dir = MODEL_DIR / (MODEL_NAME + ".parts")
    chunk_dir.mkdir(exist_ok=True)
    done = set()
    done_lock = threading.Lock()

    def fetch(index):
        start = index * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, total) - 1
        part = chunk_dir / f"{index:05d}.part"
        expected = end - start + 1
        if part.exists() and part.stat().st_size == expected:
            with done_lock:
                done.add(index)
                progress(len(done) / chunks)
            return
        if not accepts_ranges and chunks > 1:
            raise RuntimeError("Server does not support resumable range downloads.")
        req = urllib.request.Request(MODEL_URL, headers={"Range": f"bytes={start}-{end}", "User-Agent": "HyperCoder/1.0"})
        with urllib.request.urlopen(req, timeout=180) as response:
            if chunks > 1 and response.status != 206:
                raise RuntimeError("Server did not honor byte-range request; refusing unsafe chunk assembly.")
            payload = response.read()
        if len(payload) != expected:
            raise RuntimeError(f"Chunk {index + 1} had the wrong size; retry the download.")
        temp = part.with_suffix(".tmp")
        temp.write_bytes(payload)
        temp.replace(part)
        with done_lock:
            done.add(index)
            progress(len(done) / chunks)

    # Keep concurrency moderate to avoid overloading connections or memory.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, i) for i in range(chunks)]
        for future in as_completed(futures):
            future.result()

    temp_target = target.with_suffix(".download")
    with temp_target.open("wb") as output:
        for index in range(chunks):
            with (chunk_dir / f"{index:05d}.part").open("rb") as part:
                while block := part.read(8 * 1024 * 1024):
                    output.write(block)
    status("Validating SHA-256…")
    actual = sha256_file(temp_target)
    if actual.lower() != MODEL_SHA256:
        temp_target.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch. Expected {MODEL_SHA256}; got {actual}. Download was rejected.")
    temp_target.replace(target)
    for part in chunk_dir.glob("*.part"):
        part.unlink(missing_ok=True)
    chunk_dir.rmdir()
    status("Download complete; SHA-256 verified.")
    return target


class HyperCoder(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HYPER / local intelligence")
        self.geometry("1180x800")
        self.minsize(900, 640)
        self.configure(fg_color="#0b1018")
        self.events = queue.Queue()
        self.model = None
        self.messages = []
        self.busy = False
        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color="#101722")
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="✦  HYPER", font=ctk.CTkFont(size=24, weight="bold"), text_color="#e8f1ff").pack(anchor="w", padx=24, pady=(28, 2))
        ctk.CTkLabel(side, text="LOCAL INTELLIGENCE LAB", font=ctk.CTkFont(size=10, weight="bold"), text_color="#74849a").pack(anchor="w", padx=26, pady=(0, 28))
        self.model_status = ctk.CTkLabel(side, text="●  Model not loaded", text_color="#ffbf69", anchor="w")
        self.model_status.pack(fill="x", padx=22, pady=(0, 10))
        self.download_button = ctk.CTkButton(side, text="Download Gemma 4 · 2.84 GB", height=42, command=self.start_download)
        self.download_button.pack(fill="x", padx=20, pady=5)
        self.progress = ctk.CTkProgressBar(side, progress_color="#56c8ff")
        self.progress.pack(fill="x", padx=22, pady=(8, 3)); self.progress.set(0)
        self.status = ctk.CTkLabel(side, text="Ready when you are", text_color="#91a0b4", font=ctk.CTkFont(size=11), wraplength=220)
        self.status.pack(fill="x", padx=22, pady=(2, 18))
        self.load_button = ctk.CTkButton(side, text="Load local model", fg_color="#273648", hover_color="#344b64", command=self.choose_model)
        self.load_button.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(side, text="RUNTIME CONTROLS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#74849a").pack(anchor="w", padx=22, pady=(28, 8))
        self.context_var = ctk.StringVar(value="8192")
        self._option(side, "Context length", self.context_var, ["2048", "4096", "8192", "16384", "32768"])
        self.threads_var = ctk.StringVar(value=str(max(2, (os.cpu_count() or 8) - 2)))
        self._option(side, "CPU threads", self.threads_var, [str(n) for n in (2, 4, 6, 8, 12, 16)])
        self.gpu_var = ctk.StringVar(value="0")
        self._option(side, "GPU layers", self.gpu_var, ["0", "10", "20", "All"])
        self.temp_var = ctk.StringVar(value="0.7")
        self._option(side, "Temperature", self.temp_var, ["0.2", "0.5", "0.7", "0.9", "1.0"])
        ctk.CTkLabel(side, text="Quant: Q4_0  ·  Runtime: llama.cpp\nEverything runs locally on this PC.", justify="left", text_color="#728198", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=22, side="bottom", pady=22)

        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#0b1018")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1); main.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 8))
        ctk.CTkLabel(header, text="Your private AI workspace", font=ctk.CTkFont(size=22, weight="bold"), text_color="#e7effa").pack(anchor="w")
        ctk.CTkLabel(header, text="Gemma 4 E2B · quantized for local inference", font=ctk.CTkFont(size=12), text_color="#8494aa").pack(anchor="w", pady=(3, 0))
        self.chat = ctk.CTkTextbox(main, corner_radius=16, border_width=1, border_color="#1d2a3a", fg_color="#0e1520", text_color="#d9e3ef", font=ctk.CTkFont(size=14), wrap="word")
        self.chat.grid(row=1, column=0, sticky="nsew", padx=26, pady=14)
        self.chat.insert("end", "HYPER CODER\nYour local model studio is ready. Download the model or load a GGUF file, then start a conversation.\n\nTip: you can press Ctrl+Enter to send.\n")
        self.chat.configure(state="disabled")
        compose = ctk.CTkFrame(main, fg_color="#101722", corner_radius=16, border_width=1, border_color="#1d2a3a")
        compose.grid(row=2, column=0, sticky="ew", padx=26, pady=(0, 24)); compose.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkTextbox(compose, height=70, fg_color="transparent", border_width=0, text_color="#edf4ff", font=ctk.CTkFont(size=14), wrap="word")
        self.entry.grid(row=0, column=0, sticky="ew", padx=(14, 4), pady=9); self.entry.bind("<Control-Return>", self._send_key)
        self.send_button = ctk.CTkButton(compose, text="Send  ↗", width=92, height=38, command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=12, pady=12, sticky="s")

    def _option(self, parent, label, variable, values):
        row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", padx=22, pady=5)
        ctk.CTkLabel(row, text=label, text_color="#b5c1d0", font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkOptionMenu(row, variable=variable, values=values, height=30).pack(fill="x", pady=(4, 0))

    def _append(self, text):
        self.chat.configure(state="normal"); self.chat.insert("end", text); self.chat.see("end"); self.chat.configure(state="disabled")

    def _run_bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _ui(self, callback, *args):
        self.events.put((callback, args))

    def _poll_events(self):
        try:
            while True:
                callback, args = self.events.get_nowait(); callback(*args)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def start_download(self):
        self.download_button.configure(state="disabled")
        self.status.configure(text="Preparing resumable download…")
        def work():
            try:
                path = download_model(lambda f: self._ui(self.progress.set, f), lambda s: self._ui(self.status.configure, text=s))
                self._ui(self._download_done, path)
            except Exception as exc:
                self._ui(self._download_error, str(exc))
        self._run_bg(work)

    def _download_done(self, path):
        self.download_button.configure(state="normal")
        self.model_status.configure(text="●  Verified model ready", text_color="#65dda5")
        self.status.configure(text=f"Verified: {path.name}")
        self._load_path(path)

    def _download_error(self, error):
        self.download_button.configure(state="normal")
        self.status.configure(text="Download paused or failed. Partial chunks are retained.")
        messagebox.showerror("Model download", error)

    def choose_model(self):
        path = filedialog.askopenfilename(title="Choose GGUF model", filetypes=[("GGUF models", "*.gguf"), ("All files", "*.*")])
        if path:
            self._load_path(Path(path))

    def _load_path(self, path):
        if self.busy: return
        self.busy = True; self.load_button.configure(state="disabled"); self.status.configure(text="Loading model; first load can take a moment…")
        context_size = int(self.context_var.get())
        cpu_threads = int(self.threads_var.get())
        gpu = self.gpu_var.get()
        layers = -1 if gpu == "All" else int(gpu)
        def work():
            try:
                from llama_cpp import Llama
                model = Llama(model_path=str(path), n_ctx=context_size, n_threads=cpu_threads, n_gpu_layers=layers, verbose=False)
                self._ui(self._model_loaded, model, path)
            except Exception as exc:
                self._ui(self._load_error, str(exc))
        self._run_bg(work)

    def _model_loaded(self, model, path):
        self.model = model; self.busy = False; self.load_button.configure(state="normal")
        self.model_status.configure(text="●  Gemma loaded", text_color="#65dda5"); self.status.configure(text=f"Ready · {path.name}")
        self._append("\nSYSTEM  Model loaded and ready.\n\n")

    def _load_error(self, error):
        self.busy = False; self.load_button.configure(state="normal"); self.status.configure(text="Could not load model")
        messagebox.showerror("Model loading", error)

    def _send_key(self, _event):
        self.send_message(); return "break"

    def send_message(self):
        if self.busy: return
        prompt = self.entry.get("1.0", "end").strip()
        if not prompt: return
        if self.model is None:
            messagebox.showinfo("Load a model", "Download or load a GGUF model before chatting."); return
        self.entry.delete("1.0", "end"); self._append(f"\nYOU\n{prompt}\n\nHYPER\n")
        self.messages.append({"role": "user", "content": prompt})
        self.busy = True; self.send_button.configure(state="disabled"); self.status.configure(text="Generating…")
        def work():
            try:
                response = self.model.create_chat_completion(messages=self.messages, temperature=float(self.temp_var.get()), max_tokens=2048)
                text = response["choices"][0]["message"]["content"]
                self.messages.append({"role": "assistant", "content": text})
                self._ui(self._reply_done, text)
            except Exception as exc:
                self._ui(self._reply_error, str(exc))
        self._run_bg(work)

    def _reply_done(self, text):
        self._append(text + "\n"); self.busy = False; self.send_button.configure(state="normal"); self.status.configure(text="Ready")

    def _reply_error(self, error):
        self.busy = False; self.send_button.configure(state="normal"); self.status.configure(text="Generation failed")
        self._append(f"[Error: {error}]\n")


if __name__ == "__main__":
    HyperCoder().mainloop()
