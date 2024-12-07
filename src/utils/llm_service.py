import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from config import LLM_MODEL_PATH, HF_ENV

hf_token = os.getenv(HF_ENV)
tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_PATH, token=hf_token)

if torch.cuda.is_available():
    device = torch.device('cuda')
elif torch.backends.mps.is_available():
    device = torch.device('mps')
else:
    device = torch.device('cpu')

model.to(device)

def generate_npc_response(npc, player_input: str) -> str:
    history = npc.construct_chat_history(player_input)
    inputs = tokenizer("\n#################\n".join(history),
                       return_tensors='pt',
                       truncation=True,
                       max_length=1024)

    if torch.cuda.is_available():
        inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            pad_token_id=tokenizer.eos_token_id,
            temperature=1.0
        )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    npc.interaction_history[-1] = response.split("\n#################\n")[-1]

    if npc.is_appropriate(response):
        return f"{npc.name}:{response.split(':')[-1]}"
    else:
        return npc.get_fallback_response()
