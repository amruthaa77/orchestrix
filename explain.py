"""
Orchestrix explanation layer (Gemini API).
Takes the optimizer's recommendations and asks Gemini to EXPLAIN them in plain
language. Gemini never sets values. Every number in its answer is checked
against the optimizer's output; anything unmatched is flagged.

Setup (PowerShell):
    pip install google-genai
    $env:GEMINI_API_KEY = "your key from Google AI Studio"
    $env:GEMINI_MODEL   = "model name shown in AI Studio > Get code"
Run:
    python optimizer.py | python explain.py
Never paste your API key into code, screenshots, or the deck.
"""
import os, re, sys

PROMPT = """You are an SRE assistant. Below is the output of a deterministic Kubernetes
right-sizing engine. Explain each workload's recommendation to a platform engineer in
2-3 sentences: why the change is suggested, the risk, and how to roll back.
Rules: use ONLY numbers that appear in the engine output; do not invent or change any
value; if the engine says low confidence or bursty, say so plainly.

ENGINE OUTPUT:
{engine}
"""

NUM = re.compile(r"\d+(?:\.\d+)?")

def unverified_numbers(engine_text, answer_text):
    allowed = set(NUM.findall(engine_text))
    return sorted({n for n in NUM.findall(answer_text) if n not in allowed})

def main():
    engine = sys.stdin.read()
    key, model = os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_MODEL")
    if not engine.strip():
        sys.exit("No input. Run: python optimizer.py | python explain.py")
    if not key or not model:
        sys.exit("Set GEMINI_API_KEY and GEMINI_MODEL first (see top of file).")
    from google import genai
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(model=model, contents=PROMPT.format(engine=engine))
    answer = resp.text
    print("--- Gemini explanation (engine decides, Gemini explains) ---\n")
    print(answer)
    bad = unverified_numbers(engine, answer)
    if bad:
        print("\n[CHECK FAILED] Numbers not found in engine output:", ", ".join(bad))
    else:
        print("\n[CHECK PASSED] Every number matches the engine output.")

if __name__ == "__main__":
    main()