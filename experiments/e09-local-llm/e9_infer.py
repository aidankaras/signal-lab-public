"""e9 Phase 1 inference driver (runs ON the laptop, against local llama.cpp Vulkan).

Usage: python3 e9_infer.py <summaries.jsonl> <predictions.jsonl>
Reads each summary, asks the local Qwen model UP/DOWN via llama-cli, writes one
prediction per line. Idempotent: skips summaries already present in the output.
"""
import json, os, subprocess, sys

LLAMA = os.path.expanduser("~/llama.cpp/build-cpu/bin/llama-cli")
MODEL = os.path.expanduser("~/models/qwen2.5-1.5b-instruct-q4_k_m.gguf")


def ask(summary):
    out = subprocess.run(
        [LLAMA, "-m", MODEL, "-n", "8", "--temp", "0", "-p", summary],
        capture_output=True, text=True, timeout=120)
    txt = (out.stdout + out.stderr).upper()
    tail = txt.rsplit("ANSWER:", 1)[-1]  # skip echoed prompt containing 'UP OR DOWN'
    for w in ("UP", "DOWN"):
        if w in tail:
            return w
    return "?"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    done = set()
    if os.path.exists(dst):
        for l in open(dst):
            done.add(json.loads(l)["key"])
    out = open(dst, "a")
    n = ok = 0
    for l in open(src):
        r = json.loads(l)
        key = f"{r['ticker']}|{r['date']}"
        if key in done:
            continue
        pred = ask(r["summary"])
        out.write(json.dumps({"key": key, "pred": pred}) + "\n")
        out.flush()
        ok += pred != "?"
        n += 1
        if n % 25 == 0:
            print(f"{n} done, {ok} parsed", flush=True)
    print(f"finished: {n} new, {ok} parsed")


if __name__ == "__main__":
    main()
