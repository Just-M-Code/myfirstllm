# Hyper Coder: project notes

## What we built

A Windows 11 desktop chat app that downloads and verifies a local Gemma 4 E2B Instruct GGUF model, loads it with llama.cpp, and chats through a CustomTkinter interface. The app, setup scripts, dependencies, and usage steps are in this folder.

## Setup completed

- Installed Python 3.12.10 and created `.venv` in the project folder.
- Installed `customtkinter` 6.0.0 and built and installed `llama-cpp-python` 0.3.36.
- Installed Visual Studio Build Tools with the C++ workload and the Windows 11 SDK. The installer asked for a Windows restart to finish installation.
- Downloaded `models/gemma-4-E2B-it-Q4_0.gguf` (2,841,481,184 bytes) from `ggml-org/gemma-4-E2B-it-GGUF`.
- Verified its SHA-256 locally against the repository's published value:

  ```text
  8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52
  ```

The UI and a model inference were not launched as part of setup. The installed `llama-cpp-python` backend uses CPU by default. GPU offload needs a compatible CUDA or Vulkan build and driver.

## How the pieces fit together

| Component | Role |
| --- | --- |
| Python virtual environment (`.venv`) | Keeps this project's Python packages separate from other projects and system Python. |
| `customtkinter` | Provides the dark desktop UI: model controls, progress, settings, chat history, and prompt box. |
| `llama-cpp-python` | Python bindings for llama.cpp; loads GGUF weights and runs local inference from Python. |
| llama.cpp / C++ toolchain | The native inference engine. On this Windows/Python combination pip built the binding from C++ source using MSVC, CMake, Build Tools, and the Windows SDK. |
| GGUF model | Quantized model format read by llama.cpp. Q4_0 reduces storage and memory use relative to full precision. |
| Resumable downloader | Splits the remote file into HTTP byte ranges, downloads chunks concurrently, retains completed chunks after interruptions, assembles them in order, and rejects the result unless SHA-256 matches. |
| Background workers + UI event queue | Runs downloads and inference outside Tk's UI thread. Worker results are passed back through a queue so UI widgets are updated on the main thread. |
| `setup.ps1` / `run.ps1` | Creates the virtual environment and dependencies, then starts the app. `requirements.txt` records Python package requirements. |

## Run it

In PowerShell, from this project directory:

```powershell
& (Join-Path $PWD 'setup.ps1')
& (Join-Path $PWD 'run.ps1')
```

Setup is already present, so for normal use just run `run.ps1`. In the app, download or choose a GGUF file, then load it. Settings include context length, CPU threads, GPU layers, and temperature. Model files and the virtual environment are ignored by `.gitignore`.

## Prompt used for the initial build

The original request was to install llama-cpp-python and CustomTkinter on Windows 11, create a virtual environment, download a 4-bit Gemma 4 E2B model, retrieve and validate its SHA-256, and put the result into a polished CustomTkinter chat app with chunked downloading and advanced model loading.

## Techniques behind that prompt

- **Name the platform and runtime:** Windows 11, Python, and the desired libraries constrain installation and packaging choices.
- **Describe the complete user outcome:** ask for an app that downloads, validates, loads, and chats, rather than asking for isolated snippets.
- **Make integrity measurable:** request a published SHA-256 and local validation so a successful transfer is not mistaken for a trustworthy model file.
- **Ask for failure-tolerant behavior:** chunking and resumability handle large files and interrupted connections.
- **List meaningful controls:** context size, CPU threads, GPU layers, and sampling temperature give users practical model-loading and inference options.
- **Keep the platform limits visible:** Windows native builds may require MSVC and the Windows SDK; GPU offload requires a matching runtime and driver.

## Reusable prompt

> Build a polished **[platform]** desktop app using **[UI framework]** and **[inference/runtime library]**. Create an isolated environment and provide repeatable setup and launch scripts. Include a downloader for **[model name, repository, exact file, quantization]** that supports resumable chunked downloads, displays progress, and verifies the downloaded file against the publisher's SHA-256 before loading. Add controls for context length, CPU threads, GPU offload, and sampling settings; run downloads and inference off the UI thread and marshal UI updates safely. Include a chat history and responsive prompt/send area. Document prerequisites, platform-specific build tools, hardware limits, model license/source, exact checksum, setup, launch, and recovery steps. Implement the files in the project and report what was actually installed and verified, plus anything not exercised.

Replace bracketed fields with exact targets before reusing. Pin a specific model file and checksum source; quant names such as Q4_0 and Q4_K_M are different variants.
