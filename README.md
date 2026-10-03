# Hyper Coder: local Gemma chat for Windows 11

A CustomTkinter desktop app for downloading, verifying, loading, and chatting with a local GGUF model through `llama-cpp-python`.

## Install

1. Install Python 3.10-3.12 for Windows. A source build of `llama-cpp-python` also needs Visual Studio Build Tools with the **Desktop development with C++** workload and the Windows 11 SDK.
2. Open PowerShell in this folder. If local scripts are blocked, run `Set-ExecutionPolicy -Scope Process Bypass`.
3. Run `& (Join-Path $PWD 'setup.ps1')`, then `& (Join-Path $PWD 'run.ps1')`.
4. Click **Download Gemma 4**. The downloader uses parallel byte ranges, resumes retained chunks after interruption, assembles the file, then validates SHA-256 before accepting it.

The default model is `ggml-org/gemma-4-E2B-it-GGUF` / `gemma-4-E2B-it-Q4_0.gguf` (Q4_0, about 2.84 GB). Published SHA-256: `8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52`. The app independently computes and checks that hash before loading.

`llama-cpp-python` installs its CPU backend by default. GPU offload requires an appropriately compiled CUDA or Vulkan backend and compatible drivers; setting GPU layers without that backend may fail. The app also lets you load another local `.gguf` file.

All inference is local. Model download traffic goes to Hugging Face. The Gemma GGUF repository reports Apache 2.0; check the model card and applicable source-model terms for your use.
