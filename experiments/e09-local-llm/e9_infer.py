"""e9 Phase 1 inference driver (local llama.cpp).

Usage: python3 e9_infer.py <summaries.jsonl> <predictions.jsonl>
Reads each summary, asks the local Qwen model UP/DOWN via llama-cli, writes one
prediction per line. Idempotent: skips summaries already present in the output.
Set LLAMA_CLI and E9_MODEL to point at your llama-cli binary and GGUF file.

Errata (2026-11): the first version parsed stdout+stderr for the text after "ANSWER:",
but the prompt never contained "ANSWER:", and llama-cli echoes the prompt, which contains
"UP or DOWN". "UP" was checked first, so every call parsed as UP whatever the model said.
The 2026-10-19 result ("constant-UP predictor") measured that parser, not the model.
Now: the prompt is not echoed (--no-display-prompt), conversation mode is off (-no-cnv),
the output is constrained to UP|DOWN by a GBNF grammar, and only stdout is parsed.
"""
import json, os, re, subprocess, sys

LLAMA = os.environ.get("LLAMA_CLI", "llama-cli")
MODEL = os.environ.get("E9_MODEL", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
GRAMMAR = 'root ::= "UP" | "DOWN"'


def parse(generated):
    """First whole-word UP or DOWN in the generated text only; '?' if neither."""
    m = re.search(r"\b(UP|DOWN)\b", generated.upper())
    return m.group(1) if m else "?"


def ask(summary):
    out = subprocess.run(
        [LLAMA, "-m", MODEL, "-n", "4", "--temp", "0", "--no-display-prompt", "-no-cnv",
         "--grammar", GRAMMAR, "-p", summary],
        capture_output=True, text=True, timeout=120)
    return parse(out.stdout)  # stderr carries llama.cpp logs, never parse it


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
