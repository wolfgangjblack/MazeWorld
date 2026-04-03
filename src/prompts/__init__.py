from src.prompts.base import PromptSet


def get_prompt_set() -> PromptSet:
    from config import LLM_BACKEND

    if LLM_BACKEND == "api":
        from src.prompts.claude_prompts import ClaudePromptSet
        return ClaudePromptSet()
    from src.prompts.llama_prompts import LlamaPromptSet
    return LlamaPromptSet()
