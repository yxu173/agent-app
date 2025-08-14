# Lazy imports to avoid dependency issues
def get_finance_researcher_team(*args, **kwargs):
    from .finance_researcher import get_finance_researcher_team as _get_finance_researcher_team
    return _get_finance_researcher_team(*args, **kwargs)

def get_multi_language_team(*args, **kwargs):
    from .multi_language import get_multi_language_team as _get_multi_language_team
    return _get_multi_language_team(*args, **kwargs)

def get_enova_deep_research_team(*args, **kwargs):
    from .enova_deep_research import get_enova_deep_research_team as _get_enova_deep_research_team
    return _get_enova_deep_research_team(*args, **kwargs)

__all__ = [
    "get_finance_researcher_team",
    "get_multi_language_team", 
    "get_enova_deep_research_team",
]
