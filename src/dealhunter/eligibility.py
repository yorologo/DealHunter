class EligibilityEngine:
    """
    Canonical logic for Provider and Membership Eligibility.
    Centralizes the rules for whether an offer should be shown and whether it can compete
    in rankings based on user configuration.
    """
    def __init__(self, config):
        self.config = config
        
        # 1. Parse Providers
        self.providers_config = self.config.get("providers", {})
        
        # 2. Parse Memberships
        self.memberships_config = self.config.get("memberships", {})
        
        # 3. Parse Comparison Policy
        self.comparison_policy = self.config.get("comparison", {}).get("inactive_membership_offers", "show_but_exclude")

    def is_provider_enabled(self, provider):
        """Check if a specific provider is enabled."""
        p_conf = self.providers_config.get(provider, {})
        return p_conf.get("enabled", True)

    def get_enabled_providers(self):
        """Return a list of enabled providers."""
        # Our defaults contain rappi and uber_eats
        enabled = []
        for p in ["rappi", "uber_eats"]:
            if self.is_provider_enabled(p):
                enabled.append(p)
        return enabled

    def get_membership_status(self, membership):
        """Return the status of a given membership (active, inactive, unknown)."""
        m_conf = self.memberships_config.get(membership, {})
        return m_conf.get("status", "unknown")

    def map_offer_to_membership(self, provider, has_pro_offer):
        """
        Determine which membership (if any) an offer requires.
        Rappi pro_offer -> rappi_pro
        Uber Eats pro_offer -> uber_one
        """
        if has_pro_offer:
            if provider == "rappi":
                return "rappi_pro"
            elif provider == "uber_eats":
                return "uber_one"
        return "NONE"

    def evaluate(self, provider, has_pro_offer):
        """
        Evaluate eligibility for an offer.
        
        Returns:
            dict: {
                "visible": bool,               # Should it be shown in UI/results?
                "ranking_eligible": bool,      # Can it be considered the "best deal"?
                "reason": str                  # Human readable reason
            }
        """
        if not self.is_provider_enabled(provider):
            return {
                "visible": False,
                "ranking_eligible": False,
                "reason": f"Provider {provider} is disabled."
            }

        required_membership = self.map_offer_to_membership(provider, has_pro_offer)
        
        if required_membership == "NONE":
            return {
                "visible": True,
                "ranking_eligible": True,
                "reason": "Public offer."
            }

        status = self.get_membership_status(required_membership)
        
        if status == "active":
            return {
                "visible": True,
                "ranking_eligible": True,
                "reason": f"Requires {required_membership} (active)."
            }
            
        # If status is inactive or unknown, apply comparison policy
        if self.comparison_policy == "exclude":
            return {
                "visible": False,
                "ranking_eligible": False,
                "reason": f"Requires {required_membership} ({status}), policy is exclude."
            }
        elif self.comparison_policy == "show_but_exclude":
            return {
                "visible": True,
                "ranking_eligible": False,
                "reason": f"Requires {required_membership} ({status}), policy is show_but_exclude."
            }
        elif self.comparison_policy == "include":
            return {
                "visible": True,
                "ranking_eligible": True,
                "reason": f"Requires {required_membership} ({status}), policy is include."
            }
            
        # Fallback conservative
        return {
            "visible": False,
            "ranking_eligible": False,
            "reason": "Unknown comparison policy."
        }

    def get_sql_visibility_condition(self, provider_col="p.provider", has_pro_col="o.has_pro_offer"):
        """
        Return a SQL WHERE clause fragment and params that filters out non-visible offers.
        Used by Query Layer to push visibility filtering to the database.
        """
        enabled_providers = self.get_enabled_providers()
        if not enabled_providers:
            return "1=0", [] # Nothing enabled, return empty
            
        params = []
        
        # 1. Provider must be enabled
        prov_placeholders = ",".join(["?"] * len(enabled_providers))
        base_cond = f"{provider_col} IN ({prov_placeholders})"
        params.extend(enabled_providers)
        
        # 2. If policy is 'exclude', we must exclude offers requiring inactive/unknown memberships
        if self.comparison_policy == "exclude":
            exclude_conds = []
            
            rappi_status = self.get_membership_status("rappi_pro")
            if rappi_status != "active":
                # Exclude Rappi pro offers
                exclude_conds.append(f"NOT ({provider_col} = 'rappi' AND {has_pro_col} = 1)")
                
            uber_status = self.get_membership_status("uber_one")
            if uber_status != "active":
                # Exclude Uber pro offers
                exclude_conds.append(f"NOT ({provider_col} = 'uber_eats' AND {has_pro_col} = 1)")
                
            if exclude_conds:
                policy_cond = " AND ".join(exclude_conds)
                return f"({base_cond} AND {policy_cond})", params
                
        # For 'show_but_exclude' and 'include', the DB returns them, and python logic / ranking logic handles them.
        return base_cond, params
