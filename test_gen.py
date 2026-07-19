from generator.script import _F1_PROMPT, _F3_PROMPT

research_f1 = {"text": "Tardigrades", "source": "Reddit"}
niche = "mind-blowing facts"
avoid_clause = "Do NOT cover tardigrades"

facts = research_f1.get("key_facts", [])
key_facts_str = "".join([f"  • {f}\n" for f in facts]) if facts else "  • Use verified supporting facts\n"
prompt_f1 = _F1_PROMPT.format(
    niche=niche,
    research_topic=research_f1["text"],
    key_facts=key_facts_str,
    hook_angle=research_f1.get("source", "Start with the most surprising fact"),
    avoid_clause=avoid_clause,
)
print("F1 PROMPT SUCCESS")

research_f3 = {"dilemma_seed": "lying"}
prompt_f3 = _F3_PROMPT.format(
    dilemma_seed=research_f3.get("dilemma_seed", "Your best friend asks you to lie for them."),
    value_a=research_f3.get("value_a", "loyalty"),
    value_b=research_f3.get("value_b", "honesty"),
    option_a=research_f3.get("option_a", "Keep the secret."),
    option_b=research_f3.get("option_b", "Tell the truth."),
    closing_question=research_f3.get("closing_question", "What would you do?"),
)
print("F3 PROMPT SUCCESS")
