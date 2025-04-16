from app.prompts.tech_prompt import TechPrompt
from app.prompts.business_prompt import BusinessPrompt
from app.prompts.base_prompt import BasePrompt

def get_prompt_by_domain(domain: str) -> BasePrompt:
    if domain == "tech":
        return TechPrompt()
    elif domain == "business":
        return BusinessPrompt()
    else:
        raise ValueError(f"Unsupported domain: {domain}")
