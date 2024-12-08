import os
import ast
import torch
from config import HF_ENV
from transformers import AutoTokenizer, AutoModelForCausalLM

# Load model directly
hf_token = os.getenv(HF_ENV)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct",
                                          token = hf_token)
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B-Instruct",
                                             token = hf_token)

def personality_primative_instruct() -> str:    
    sys_gen ="""##sys: You are a non-playable character content generator. You create npcs for video games, generating
    names, jobs, personalities, hobbies, and interaction types. You inherit their environment from the map which is meant
    to influence their content. 
    
    Follow these rules:
    1. output a name, job, personality, and hobby related to their environment
    2. do not create dialogue
    3. generate in a jsonic format
    4. Use the following examples:
   
    Here are some examples of npcs you can generate:
    
    ##Input: enviroment: 'forest', env_name: 'Iron Oak'
     ========================================
    ##Output: {'name': 'helena', 'job': 'herbalist', 'personality': 'mysterious', 'hobby': collecting herbs}
    
    ##Input: enviroment: 'desert', env_name: 'Sandstone'
     ========================================
    ##Output: {'name': 'khalid', 'job': 'merchant', 'personality': 'charming', 'hobby': 'haggling'}

    ##Input: enviroment: 'mountain', env_name: 'Frostpeak'
     ========================================
    ##Output: {'name': 'greta', 'job': 'blacksmith', 'personality': 'gruff', 'hobby': 'forging'}

    ##Input: enviroment: 'city', env_name: 'Silverport'
     ========================================
    ##Output: {'name': 'julius', 'job': 'guard', 'personality': 'stoic', 'hobby': 'training'}

    ##Input: enviroment: 'swamp', env_name: 'Mosswood'
     ========================================
    ##Output: {'name': 'elara', 'job': 'alchemist', 'personality': 'eccentric', 'hobby': 'experimenting'}
"""

    return sys_gen

def generate_personality_primative(environment: dict) -> dict:
    """
    Expects input of {"environment": {"name": "shadowleaf", "type": "forest}}
    """
    
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    prompt = [personality_primative_instruct()]
    prompt.append(f"##Input: enviroment: '{env}', env_name: '{env_name}'")
    prompt.append('##Output: ')

    inputs = tokenizer("\n========================================\n".join(prompt),
                return_tensors='pt',
                truncation=True,
                max_length=512)

    if torch.cuda.is_available():
        inputs = {k: v.to('cuda') for k, v in inputs.items()}
        
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=40,
            pad_token_id=tokenizer.eos_token_id,
            temperature=1
        )

    response = tokenizer.decode(outputs[0], 
                skip_special_tokens=True)
    
    try:            
        output = response.split(f"##Input: enviroment: '{env}', env_name: '{env_name}'")[-1]
        output = output.split("##Output:")
        output = output[-1].split("\n========================================\n")
        output =  ast.literal_eval(output[0])
        output["environment"] = env
        output["environment_name"] = env_name
        return output
    except Exception as e:
        return {"error": str(e)}
    
def conversation_primative(npc_personality_json) -> dict:
    
    name = npc_personality_json.get("name", "npc")
    job = npc_personality_json.get("job", "peasant")
    personality = npc_personality_json.get("personality", "dim")
    hobby = npc_personality_json.get("hobby", "strolling")
    environment = npc_personality_json.get("environment", "city")
    environment_name = npc_personality_json.get("environment_name", "Starter Town")
    
    
    instructions = f"""##sys: You are playing a video game character. You are {name}, a {job} in a 
    {environment} called {environment_name}.  This environment is in a fantasy setting, so limit 
    discussions to the environment, the npc's job, and the npc's hobbies. The npc's personality is 
    {personality}. The npc's hobbies are {hobby}.
        
        Always follow these rules:
        1. do not speak for the player
        2. do not Roleplay heavily
        3. do not break the fourth wall
        4. do not hallucinate
        5. converse with the NPC but maintain conversational context     
        6. Only generate one response at a time    
    """
    
    npc_personality_json["interaction_history"] = [instructions]
    
    return npc_personality_json


def generate_npc_convo(npc_personality_json: dict, delimiter ="\n========================================\n" ) -> dict:
    """
    Expects input like:
    {'name': 'lyra',
    'job': 'shaman',
    'personality': 'whispering',
    'hobby': 'communicating with spirits',
    'environment': 'forest',
    'environment_name': 'shadowleaf'}
    """
    
    character_details = conversation_primative(npc_personality_json)
    character_details['interaction_history'].append("##sys: You see the player approaching you, greet the player simply based on your personality")
    character_details['interaction_history'].append(f'##{npc_personality_json.get("name", "npc")}: ')
    
    inputs = tokenizer(delimiter.join(character_details['interaction_history']),
            return_tensors='pt',
            truncation=True,
            max_length=512)
    
    if torch.cuda.is_available():
        inputs = {k: v.to('cuda') for k, v in inputs.items()}
        
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            pad_token_id=tokenizer.eos_token_id,
            temperature=1
        )

    response = tokenizer.decode(outputs[:, inputs['input_ids'].shape[-1]:][0],
                                    skip_special_tokens=True)

    return response.split(delimiter)[0]