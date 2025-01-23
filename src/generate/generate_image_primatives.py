import torch
from diffusers import FluxPipeline

flux_model_id = "black-forest-labs/FLUX.1-schnell"

pipe = FluxPipeline.from_pretrained(flux_model_id,
                                    torch_dtype=torch.bfloat16)

pipe.enable_model_cpu_offload()

def generate_npc_portraits(npc_database: dict, pipe):
    """
    This function is called after the npc database has been generated. It will take the npc database and generate a portrait for each npc based off the npc field
    `npc.description`. updates npc database
    """
    
    ## psuedo code for generating images
    ## prompts = []
    ## for npc in npc_database:
    ##   prompts.append(npc['description'])
    
    prompts = [{npc['id']: npc['description'] for npc in npc_database.values()}]
    batch_size = 4
    for i in range(0, len(prompts), batch_size):
        batch_prompts = prompts[i:i + batch_size]
        
        images = pipe(prompt = batch_prompts,        
             height = 256,
             width = 256,
             num_inference_steps= 12,
             max_sequence_length = 256,
             ).images
        
        
        
        
        
        
        