
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Loading SmolLM2-360M-Instruct...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True,
)
model.eval()

knowledge = """
Outlook email synchronisation troubleshooting:
1. Check internet connectivity.
2. Check whether Outlook is in offline mode.
3. Restart Outlook and check service status if available.
4. Record error messages and when the issue began.
5. Do not delete mail profiles or data files without authorisation.
6. Escalate persistent problems to IT Support.
"""

question = "My emails are not appearing in Outlook. What should I try?"

messages = [
    {
        "role": "system",
        "content": (
            "You are an IT support assistant. Answer using only "
            "the supplied knowledge. Do not invent troubleshooting "
            "steps. If the knowledge is insufficient, recommend "
            "contacting IT Support."
        ),
    },
    {
        "role": "user",
        "content": (
            f"Knowledge:\n{knowledge}\n\n"
            f"Question: {question}\n\n"
            "Give a concise numbered list of troubleshooting steps. "
            "Preserve important safety warnings."
        ),
    },
]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = tokenizer(
    prompt,
    return_tensors="pt",
)

print("Generating answer...")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=120,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )

new_tokens = outputs[0][inputs["input_ids"].shape[1]:]

answer = tokenizer.decode(
    new_tokens,
    skip_special_tokens=True,
).strip()

print("\nQUESTION:")
print(question)

print("\nGENERATED ANSWER:")
print(answer)

del model
del tokenizer
del inputs
del outputs
