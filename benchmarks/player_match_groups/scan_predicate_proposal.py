"""Historical review proposal, superseded by the user-specified corpse scan rule.
The former target-death exemption was incorrect and must never be selected.
See docs/corpse-scan-rule-fix.md and werewolf.seer_intervention.
Historical JSON is retained only as evidence of the rejected interpretation.
"""
def candidate():
    raise RuntimeError("Superseded: dead targets must still yield scan results")
def run():
    return dict(superseded=True, app_selected=False,
                reason="User specified owner-only pre-acquisition exemption; targets include corpses")
if __name__ == '__main__':
    print(run())
