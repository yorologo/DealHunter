def build_sql(config):
    clauses = []
    
    # 1. Providers
    providers = config.get("providers", {})
    enabled_providers = [p for p, c in providers.items() if c.get("enabled", True)]
    if not enabled_providers:
        return "1=0" # Nothing enabled
        
    p_placeholders = ",".join(["?"] * len(enabled_providers))
    clauses.append(f"provider IN ({p_placeholders})")
    
    return " AND ".join(clauses), enabled_providers
    
print(build_sql({"providers": {"rappi": {"enabled": True}, "uber_eats": {"enabled": False}}}))
