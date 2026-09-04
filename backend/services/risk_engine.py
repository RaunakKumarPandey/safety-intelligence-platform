"""
Transparent, Configurable & Explainable SIF Risk Engine for SIH26165
---------------------------------------------------------------------
Expanded Oil & Gas Industry SIF Precursor Taxonomy & Risk Engine:
1. Evidence-Based Structured Corrective Action Generation with priority,
   immediate controls, verification steps, responsible safety roles,
   escalation conditions, and follow-up actions.
2. Comprehensive 11-Category Oil & Gas Precursor Taxonomy (OISD & IOGP Life-Saving Rules Aligned).
3. Contextual sentence-level negation & mitigation filtering (e.g. 'no gas leakage detected' vs 'gas leakage detected').
4. Compound Multi-Hazard Synergy Escalation logic.
5. Explainable Multi-Signal Risk Scoring with transparent mathematical attribution.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================================
# 1. CONFIGURATION & COMPONENT DATA STRUCTURES
# ============================================================================

@dataclass
class RiskScoringConfig:
    """Configurable weights, thresholds, and parameters for explainable risk scoring."""
    min_score: int = 0
    max_score: int = 100

    # Risk Tier thresholds (0-19 LOW, 20-49 MEDIUM, 50-74 HIGH, 75-100 CRITICAL)
    tier_critical_threshold: int = 75
    tier_high_threshold: int = 50
    tier_medium_threshold: int = 20

    # Multi-Hazard Synergy / Compounding Boost
    compound_hazard_boost: int = 10

    # Severity Level Contribution Mapping (Optional auxiliary integration)
    severity_level_weights: Dict[str, int] = field(default_factory=lambda: {
        "I": 0,
        "II": 5,
        "III": 10,
        "IV": 15,
        "V": 20
    })

    # Historical Precedent Thresholds
    historical_similarity_threshold: float = 20.0  # % match
    historical_catastrophic_boost: int = 5


@dataclass
class RiskComponent:
    """Individual explainable component contributing to the overall risk score."""
    factor: str
    label: str
    contribution: int
    category: str                        # e.g. "SIF Precursor", "Compound Interaction", "Severity Alignment"
    evidence: List[str]                  # Matched evidence strings or rationale

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CorrectiveAction:
    """Structured, evidence-based corrective action plan for detected SIF hazards."""
    action: str
    priority: str                       # "IMMEDIATE", "HIGH", "MEDIUM", "ROUTINE"
    reason: str                         # Direct linkage to detected evidence
    related_precursor: str              # Canonical name
    precursor_id: str                   # Taxonomy code (e.g. SIF-001)
    immediate_control: str              # Immediate containment / stop-work step
    verification_step: str              # Quantitative or physical verification
    responsible_safety_role: str        # Field safety role assigned
    escalation_condition: str           # When to escalate to installation manager
    follow_up_action: str               # Root-cause analysis / MOC / PTW signoff
    requires_human_approval: bool = True  # Safety officer approval gate

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 2. TAXONOMY SPECIFICATION WITH STRUCTURED ACTIONS
# ============================================================================

@dataclass
class PrecursorDefinition:
    precursor_id: str
    factor: str                          # Identifier key for backend/frontend
    name: str                            # Human-readable title
    description: str                     # Canonical semantic definition
    primary_keywords: List[str]          # High-relevance domain keywords
    semantic_patterns: List[str]         # Contextual regex patterns
    related_hazards: List[str]           # Associated industrial categories
    severity_contribution: int          # Risk score increment (0-100 scale)
    possible_consequence: str            # Worst-case scenario
    recommended_controls: List[str]      # Prescriptive hierarchy of controls

    # Evidence-Based Action Metadata
    action_priority: str                 # "IMMEDIATE", "HIGH", "MEDIUM"
    immediate_control: str               # Step 1: Immediate control
    verification_step: str               # Step 2: Physical verification
    responsible_safety_role: str         # Step 3: Responsible role
    escalation_condition: str            # Step 4: Escalation trigger
    follow_up_action: str                # Step 5: Follow-up action


# Standard SIF Taxonomy definitions (OISD & IOGP Life-Saving Rules Aligned)
SIF_TAXONOMY: Dict[str, PrecursorDefinition] = {

    "high_pressure": PrecursorDefinition(
        precursor_id="SIF-001",
        factor="high_pressure",
        name="High Pressure Exposure",
        description="Uncontrolled release of stored kinetic or hydraulic energy from high pressure pipelines, hydrojet pumps, vessels, wellhead lines, or pressure test manifolds.",
        primary_keywords=[
            "high pressure", "pressurized", "pressure line", "pressure pipeline",
            "pressure surge", "hydraulic pressure", "relief valve", "hydrojet",
            "burst disc", "psi", "bar pressure", "pressure gauge", "wellhead pressure",
            "casing pressure", "standpipe pressure", "choke manifold", "hydrotest"
        ],
        semantic_patterns=[
            r"\b(?:high|extreme|excessive|abnormal|uncontrolled)[- ]+pressure\b",
            r"\b(?:pressuriz|pressuris)ed\s+(?:line|pipe|pipeline|vessel|hose|system|tank|manifold|tubing)\b",
            r"\b(?:pressure|hydrostatic)\s+(?:test|testing|surge|spike|release|relief|buildup)\b",
            r"\b(?:hydrojet|waterjet|hydraulic)\s+(?:hose|pump|equipment|line|tool)\b",
            r"\b\d+\s*(?:psi|bar|kg/cm2)\b",
            r"\b(?:wellhead|casing|standpipe|annulus)\s+pressure\b",
        ],
        related_hazards=["Pressurized Systems", "Line Rupture", "Projectile Impact"],
        severity_contribution=25,
        possible_consequence="Catastrophic line rupture, projectile impact trauma, kinetic fluid injection.",
        recommended_controls=[
            "Depressurize and verify zero-energy line venting prior to breaking containment.",
            "Verify Double Block and Bleed (DBB) isolation and lock pressure relief paths.",
            "Enforce strict safety exclusion perimeter around active high-pressure testing zones per OISD-113."
        ],
        action_priority="IMMEDIATE",
        immediate_control="Halt affected high-pressure operations immediately; isolate and depressurize upstream lines.",
        verification_step="Verify zero stored energy via calibrated pressure gauges and check bleed-off valve open status.",
        responsible_safety_role="Process Safety Lead / Shift In-Charge",
        escalation_condition="Uncontrolled pressure spike, relief valve failure, or compromised line integrity.",
        follow_up_action="Perform ultrasonic thickness testing (UT) and record hydrotest certification in maintenance log."
    ),

    "leakage": PrecursorDefinition(
        precursor_id="SIF-002",
        factor="leakage",
        name="Hydrocarbon & Gas Leakage",
        description="Loss of primary containment of flammable hydrocarbons, natural gas, methane, crude oil, condensate, diesel, or volatile fuel vapors.",
        primary_keywords=[
            "leakage", "leak", "gas leak", "fluid leak", "oil spill", "hydrocarbon leak",
            "gas smell", "hissing", "condensate spill", "lel alarm", "pinhole leak",
            "flange leak", "valve leak", "gas escaping", "vapor cloud", "stuffing box leak"
        ],
        semantic_patterns=[
            r"\b(?:gas|hydrocarbon|condensate|methane|crude|fuel|diesel|oil|vapor|vapour)\s+(?:leak|leakage|leaking|smell|odor|odour|release|spill|spray|pooling|escaping|cloud|seep)\b",
            r"\b(?:leak|leakage|spill|seepage|drip)\s+(?:near|around|from|at|in)\s+(?:compressor|separator|wellhead|manifold|flange|valve|pipeline|tank|skid|pump)\b",
            r"\b(?:hydrocarbon|gas)\s+detector\s+(?:alarm|alert|triggered|beeping)\b",
            r"\b\d+%\s*lel\b",
            r"\bhissing\s+(?:noise|sound|from\s+flange|from\s+valve|from\s+pipe)\b",
        ],
        related_hazards=["Flammable Atmosphere", "Loss of Containment", "Vapor Cloud"],
        severity_contribution=20,
        possible_consequence="Vapor cloud explosion (VCE), flash fire, jet fire, atmospheric oxygen displacement.",
        recommended_controls=[
            "Isolate upstream emergency shutdown valves (SDVs) and activate emergency containment perimeter.",
            "Deploy continuous 4-gas atmospheric monitors and establish Zone 1 ignition control perimeter.",
            "Halt all hot-work activities immediately and execute gas dispersion ventilation."
        ],
        action_priority="IMMEDIATE",
        immediate_control="Isolate primary containment source; activate remote Emergency Shutdown (ESD) if accessible.",
        verification_step="Deploy calibrated 4-gas atmospheric monitors to verify 0% LEL and zero flammable gas concentration.",
        responsible_safety_role="Area HSE Officer / Control Room Operator",
        escalation_condition="Gas concentration exceeds 10% LEL, or leak cannot be isolated within 5 minutes.",
        follow_up_action="Replace failed gasket/seal, re-torque flange per API specifications, and log MOC record."
    ),

    "fire_gas": PrecursorDefinition(
        precursor_id="SIF-003",
        factor="fire_gas",
        name="Fire / Gas Hazard",
        description="Active flame, sparks, explosion hazard, combustible atmosphere, or uncontrolled flaring in proximity to volatile hydrocarbon processing zones.",
        primary_keywords=[
            "fire", "explosion", "gas", "flammable", "h2s", "methane", "flare", "spark",
            "ignition", "combustible", "flame", "backfire", "hot work in zone", "blast"
        ],
        semantic_patterns=[
            r"\b(?:fire|explosion|flash\s*fire|ignition|combustion|blast)\b",
            r"\b(?:flammable|combustible|explosive)\s+(?:gas|atmosphere|mixture|environment|zone)\b",
            r"\b(?:spark|hot\s+work|flame|torch|welding)\s+in\s+(?:zone|hazardous|hydrocarbon|wellhead|battery|tank\s+farm)\b",
            r"\b(?:flaring|flare\s+stack|separator\s+reflux|furnace\s+reflux|burner\s+puff)\b",
        ],
        related_hazards=["Thermal Radiation", "Blast Overpressure", "Combustion"],
        severity_contribution=25,
        possible_consequence="Major facility explosion, thermal radiation burns, structural collapse.",
        recommended_controls=[
            "Immediate activation of deluge/fire suppression systems and site evacuation alarm.",
            "Isolate fuel sources via remote Emergency Depressurization (EDP) and Emergency Shutdown (ESD).",
            "Maintain hot-work spark containment barriers and Continuous Gas Monitoring per OISD-GDN-115."
        ],
        action_priority="IMMEDIATE",
        immediate_control="Halt all hot-work operations; activate deluge/foam fire suppression systems and sound muster alarm.",
        verification_step="Inspect ignition perimeter and continuous gas detectors for residual vapor pockets.",
        responsible_safety_role="Installation Safety Manager / Fire & Safety Officer",
        escalation_condition="Visible ignition, flame front detection, or continuous gas alarm in Zone 1.",
        follow_up_action="Audit Permit to Work (PTW) hot-work containment barriers and conduct post-incident review."
    ),

    "toxic_chemical": PrecursorDefinition(
        precursor_id="SIF-004",
        factor="toxic_chemical",
        name="Toxic Gas (H2S) & Chemical Hazard",
        description="Atmospheric exposure to lethal Hydrogen Sulfide (H2S), corrosive drilling mud additives, acidizing chemicals, caustic wash, or toxic industrial chemical vapors.",
        primary_keywords=[
            "h2s", "hydrogen sulfide", "sour gas", "toxic gas", "chemical", "acid", "caustic",
            "corrosive", "ppm alarm", "mud chemical", "chemical burn", "poisonous", "biocide",
            "acidizing", "h2s release", "sour crude"
        ],
        semantic_patterns=[
            r"\b(?:h2s|hydrogen\s+sulfide|sour\s+gas|toxic\s+gas|poisonous\s+gas|sour\s+crude)\b",
            r"\b\d+\s*ppm\s+(?:alarm|detected|concentration|h2s|gas)\b",
            r"\b(?:chemical|caustic|acid|corrosive|biocide|acidizing)\s+(?:spill|splash|contact|leak|vapor|exposure|burn)\b",
            r"\b(?:scba|respirator|breathing\s+apparatus)\s+(?:missing|required|depleted|faulty)\b",
        ],
        related_hazards=["H2S Knockdown", "Chemical Toxicity", "Respiratory Failure"],
        severity_contribution=25,
        possible_consequence="Instantaneous H2S neurological knockdown, pulmonary edema, severe chemical burns.",
        recommended_controls=[
            "Mandate positive-pressure Self-Contained Breathing Apparatus (SCBA) before entering sour gas zones.",
            "Establish personal multi-gas detector protocols set to 5 PPM H2S alarm threshold.",
            "Maintain active eyewash safety showers and Chemical Safety Data Sheet (CSDS) protocols on site."
        ],
        action_priority="IMMEDIATE",
        immediate_control="Don positive-pressure SCBA immediately; evacuate personnel upwind to designated green muster point.",
        verification_step="Perform atmospheric H2S multi-level sampling ensuring levels are strictly < 5 PPM before re-entry.",
        responsible_safety_role="H2S Safety Specialist / Rig Medic",
        escalation_condition="Atmospheric H2S > 10 PPM or personnel displaying neurological knockdown symptoms.",
        follow_up_action="Re-certify emergency SCBA cascade systems and audit chemical safety data sheets."
    ),

    "fall_hazard": PrecursorDefinition(
        precursor_id="SIF-005",
        factor="fall_hazard",
        name="Working at Height & Fall Hazard",
        description="Personnel working at elevated structures, derrick floors, monkey boards, or scaffolding without certified fall arrest, unhooked harness lanyards, or missing guardrails.",
        primary_keywords=[
            "height", "fall", "scaffold", "scaffolding", "ladder", "derrick", "monkey board",
            "without harness", "unhooked", "grating", "open edge", "life line", "lifeline",
            "working at elevation", "fall arrest", "lanyard"
        ],
        semantic_patterns=[
            r"\b(?:working|worker|technician|personnel)\s+at\s+\d+\s*(?:m|meter|meters|ft|feet)\s+(?:height|elevation)\b",
            r"\b(?:without|missing|no|unhooked|unfastened)\s+(?:(?:full[- ]body|safety)\s+)?(?:harness|lifeline|safety\s+line|lanyard|tie[- ]off)\b",
            r"\b(?:scaffold|scaffolding)\s+(?:plank|board|structure)\s+(?:shifted|unsecured|damaged|defective|unfastened|untagged)\b",
            r"\b(?:fall|dropped)\s+from\s+(?:height|ladder|scaffold|derrick|platform|mast|monkey\s+board)\b",
            r"\b(?:open|missing)\s+(?:grating|guardrail|toe[- ]board|barrier)\s+at\s+height\b",
        ],
        related_hazards=["Gravitational Fall", "Structural Collapse", "Elevated Grating"],
        severity_contribution=20,
        possible_consequence="Fatal blunt impact trauma, spinal damage, severe multi-fracture injuries.",
        recommended_controls=[
            "Enforce 100% dual-lanyard harness anchoring to certified independent lifelines.",
            "Inspect scaffolding with OISD-compliant Green-Tag load certification prior to shift commencement.",
            "Install perimeter toe-boards, safety netting, and guardrails on all platforms exceeding 1.8 meters."
        ],
        action_priority="HIGH",
        immediate_control="Issue immediate Stop-Work order; ensure all personnel hook 100% dual lanyards to certified anchorages.",
        verification_step="Inspect scaffolding green tags, guardrail toe-boards, and static lifeline load certificates.",
        responsible_safety_role="Scaffolding Inspector / Rig Safety Officer",
        escalation_condition="Work attempted above 1.8m without scaffold tagging or certified anchorage point.",
        follow_up_action="Conduct toolbox talk on working-at-height controls and inspect fall-arrest harnesses."
    ),

    "machinery": PrecursorDefinition(
        precursor_id="SIF-006",
        factor="machinery",
        name="Machinery & Rotating Equipment",
        description="Exposed high-speed rotating equipment, bypassed safety interlocks, mud pump chain drives, rotary table, top drive, cathead entanglement, or mechanical pinch-points.",
        primary_keywords=[
            "machinery", "machine", "rotary table", "chain drive", "mud pump", "unguarded",
            "guard missing", "pinch point", "entanglement", "nip point", "cathead", "rotating",
            "top drive", "spinning chain", "winch", "conveyor"
        ],
        semantic_patterns=[
            r"\b(?:rotary\s+table|chain\s+drive|mud\s+pump|drawworks|cathead|winch|top\s+drive|spinning\s+chain)\b",
            r"\b(?:unguarded|guard\s+missing|without\s+guard|mesh\s+guard\s+removed|interlock\s+bypassed)\b",
            r"\b(?:pinch\s+point|caught\s+in|drawn\s+into|entanglement|nip\s+point|rotating\s+parts|shaft\s+exposed)\b",
            r"\b(?:belt|chain|pulley|coupling)\s+(?:snapped|slipped|loose|vibrating|unguarded)\b",
        ],
        related_hazards=["Rotary Entanglement", "Crushing Pinch-Point", "Mechanical Shear"],
        severity_contribution=20,
        possible_consequence="Traumatic limb amputation, crushing degloving trauma, projectile equipment fragments.",
        recommended_controls=[
            "Install engineered interlocked mesh machine guards preventing physical access to rotating drives.",
            "Enforce strict Stop-Work policy when machine guards or safety interlocks are removed.",
            "Maintain minimum clearance zones around active rig-floor rotary tables and drawworks."
        ],
        action_priority="HIGH",
        immediate_control="Disengage power drives immediately; install certified interlocked physical machine guards.",
        verification_step="Confirm physical barrier clearance and zero rotating equipment nip-point access.",
        responsible_safety_role="Mechanical Maintenance Supervisor",
        escalation_condition="Machine interlocks bypassed, guards missing during live equipment operations.",
        follow_up_action="Complete machine guarding non-conformance report and inspect drive couplings."
    ),

    "confined_space": PrecursorDefinition(
        precursor_id="SIF-007",
        factor="confined_space",
        name="Confined Space Exposure",
        description="Entry into tanks, separator vessels, sumps, frac tanks, mud pits, or unventilated pits with limited egress, oxygen deficiency, or toxic vapor traps.",
        primary_keywords=[
            "confined space", "tank", "vessel", "sump", "mud pit", "underground", "enclosed",
            "separator entry", "manhole", "oxygen deficient", "frac tank", "bilge"
        ],
        semantic_patterns=[
            r"\bconfined\s+space\s+(?:entry|operation|work|area)\b",
            r"\b(?:entry|entering|inside)\s+(?:into\s+)?(?:tank|vessel|sump|mud\s+pit|column|enclosed|separator|manhole|frac\s+tank)\b",
            r"\b(?:without|missing)\s+(?:gas\s+test|ventilation|standby|hole\s*watch|csep|permit)\b",
            r"\b(?:oxygen\s+deficiency|gas\s+accumulation\s+in\s+pit|toxic\s+trap|asphyxiation\s+hazard)\b",
        ],
        related_hazards=["Asphyxiation", "Atmospheric Entrapment", "Restricted Egress"],
        severity_contribution=20,
        possible_consequence="Fatal oxygen displacement asphyxiation, toxic gas trap entrapment, delayed rescue.",
        recommended_controls=[
            "Execute formal Confined Space Entry Permit (CSEP) with multi-level atmospheric testing.",
            "Deploy continuous positive mechanical ventilation throughout duration of vessel occupancy.",
            "Station dedicated trained Standby Observer / Hole Watch equipped with emergency extraction tackle."
        ],
        action_priority="IMMEDIATE",
        immediate_control="Suspend vessel/pit entry; station trained Standby Hole Watch at manway entrance.",
        verification_step="Perform 3-level atmospheric gas test (O2: 19.5-23.5%, LEL: 0%, H2S: 0 PPM) and verify forced ventilation.",
        responsible_safety_role="Confined Space Entry Supervisor",
        escalation_condition="Oxygen deficiency (<19.5%), positive toxic gas reading, or communication loss with entrant.",
        follow_up_action="Close Confined Space Entry Permit (CSEP) and log extraction harness inspection."
    ),

    "electrical": PrecursorDefinition(
        precursor_id="SIF-008",
        factor="electrical",
        name="Electrical Hazard",
        description="Live electrical conductors, frayed high-voltage cables, water/drilling fluid contact with power panels, arc flash, MCC switchgear trips, or LOTO isolation failure.",
        primary_keywords=[
            "electric", "electrical", "voltage", "shock", "power line", "spark", "frayed cable",
            "440v", "live wire", "loto", "lockout", "mcc panel", "short circuit", "arc flash",
            "switchgear", "trailing cable", "junction box"
        ],
        semantic_patterns=[
            r"\b(?:electric|electrical)\s+(?:shock|hazard|spark|fault|fire|cable|wire|panel|isolation|short\s+circuit)\b",
            r"\b(?:frayed|damaged|exposed|cut|submerged|uninsulated)\s+(?:cable|wire|power\s+line|conductor|trailing\s+cable)\b",
            r"\b\d+\s*(?:v|volt|volts|kv)\b",
            r"\b(?:lockout|tagout|loto)\s+(?:violation|bypassed|missing|not\s+applied|failed)\b",
            r"\b(?:mcc|vfd|switchgear|breaker|junction\s+box)\s+(?:panel|room|explosion|trip|spark)\b",
        ],
        related_hazards=["Arc Flash", "Electrical Shock", "Zone 1 Ignition Source"],
        severity_contribution=20,
        possible_consequence="Fatal cardiac electrocution, deep arc-flash burns, secondary ignition of flammable vapors.",
        recommended_controls=[
            "Perform positive Lockout/Tagout (LOTO) and zero-energy test at MCC breaker before touching circuits.",
            "Inspect flameproof (FLP) certified electrical enclosures in hazardous Zone 1/2 classifications.",
            "Immediately de-energize and replace frayed power cables exposed to drilling fluid puddles."
        ],
        action_priority="IMMEDIATE",
        immediate_control="De-energize electrical breaker immediately; apply physical Lockout/Tagout (LOTO) padlock.",
        verification_step="Perform positive zero-energy voltage test with calibrated multimeter before touching conductors.",
        responsible_safety_role="Chief Electrical Engineer / Certified Electrician",
        escalation_condition="Frayed cable submerged in fluid, arc-flash occurrence, or ungrounded circuit.",
        follow_up_action="Replace damaged wiring with flameproof (FLP) armored cabling and log in LOTO register."
    ),

    "ppe": PrecursorDefinition(
        precursor_id="SIF-009",
        factor="ppe",
        name="PPE Violation",
        description="Failure to wear mandatory personal protective equipment including impact helmets, eye protection, hearing protection, fall harness, or respirators.",
        primary_keywords=[
            "without ppe", "not wearing", "without wearing", "no helmet", "without helmet", "incomplete ppe",
            "no harness", "without harness", "no goggles", "missing ppe", "without hearing protection",
            "no ear plugs", "not wearing hearing protection", "without safety goggles", "without gloves",
            "ppe non-compliance", "ppe breach"
        ],
        semantic_patterns=[
            r"\b(?:without|not\s+wearing|without\s+wearing|missing|no|refusing|defying)\s+(?:(?:full[- ]body|safety|protective|proper|mandatory|hearing|ear|chemical|resistant)\s+)*(?:ppe|helmet|hard\s+hat|harness|gloves|safety\s+shoes|glasses|goggles|respirator|ear\s+protection|hearing\s+protection|ear\s*plugs|ear\s*muffs|mask)\b",
            r"\bincomplete\s+ppe\b",
            r"\bppe\s+(?:violation|non[- ]compliance|breach)\b",
        ],
        related_hazards=["Physical Exposure", "Secondary Barrier Failure", "Noise Induced Hearing Loss"],
        severity_contribution=15,
        possible_consequence="Direct physical trauma, acoustic trauma, chemical/respiratory exposure.",
        recommended_controls=[
            "Enforce immediate Stop-Work Authority (SWA) and supply mandatory personal protective gear.",
            "Conduct safety toolbox re-briefing on mandatory PPE requirements per OISD guidelines.",
            "Issue supervisor safety observation and monitor crew compliance before resuming operations."
        ],
        action_priority="MEDIUM",
        immediate_control="Stop unsafe work immediately; provide mandatory personal protective equipment before resumption.",
        verification_step="Direct supervisor physical verification of helmet, eye protection, hearing protection, or harness.",
        responsible_safety_role="Shift Safety Officer / Immediate Supervisor",
        escalation_condition="Refusal to comply with mandatory PPE or entering hazardous process zones unprotected.",
        follow_up_action="Record behavioral safety observation (BBS) and conduct corrective PPE briefing."
    ),

    "dropped_objects": PrecursorDefinition(
        precursor_id="SIF-010",
        factor="dropped_objects",
        name="Dropped Objects & Lifting Hazard",
        description="Unsecured equipment or hand tools at height falling towards personnel, crane hoisting failures, snapped lifting slings, or personnel positioned beneath suspended loads.",
        primary_keywords=[
            "dropped object", "falling tool", "suspended load", "crane", "hoisting", "rigging",
            "heavy wrench dropped", "dropped from height", "overhead hazard", "sling failure",
            "sling snapped", "under load", "un-tethered", "untethered", "falling wrench",
            "dropped wrench", "dropped pipe", "fell from derrick"
        ],
        semantic_patterns=[
            r"\b(?:dropped|falling|fell|falling\s+down)\s+(?:object|tool|wrench|equipment|pipe|bolt|grating|debris|shackle|kelly)\b",
            r"\b(?:un[- ]?tethered|unsecured|loose)\s+(?:tool|wrench|equipment|hand\s+tool|object)\b",
            r"\b(?:tool|wrench|pipe|bolt|shackle|object)\s+(?:fell|dropped|falling)\b",
            r"\b(?:under|beneath)\s+(?:suspended|overhead|crane|hoist)\s+(?:load|pipe|tubing|equipment)\b",
            r"\b(?:crane|hoisting|rigging|winch|sling|shackle)\s+(?:failure|slip|overload|damaged|snapped)\b",
        ],
        related_hazards=["Overhead Kinetic Impact", "Crush Hazard", "Rigging Failure"],
        severity_contribution=20,
        possible_consequence="Fatal head and bodily crush trauma, structural process equipment damage.",
        recommended_controls=[
            "Mandate 100% tethering and tool-lanyards for all hand tools utilized in elevated work.",
            "Establish barricaded red-zone drop exclusions beneath all active overhead and hoisting tasks.",
            "Perform pre-use non-destructive inspection of all lifting slings, shackles, and wire ropes."
        ],
        action_priority="HIGH",
        immediate_control="Halt overhead hoisting; establish barricaded drop-zone perimeter beneath elevated task.",
        verification_step="Verify 100% tool-tethering lanyards and inspect sling SWL (Safe Working Load) tags.",
        responsible_safety_role="Rigging Supervisor / Rig Floor Safety Lead",
        escalation_condition="Unsecured tools at height above active deck or overloaded lifting tackle.",
        follow_up_action="Conduct DROPS survey across derrick structures and audit rigging gear inventory."
    ),

    "maintenance": PrecursorDefinition(
        precursor_id="SIF-011",
        factor="maintenance",
        name="Maintenance Activity",
        description="Performing non-routine maintenance, line breaking, dismantling, hot bolting, or servicing on operational processing equipment.",
        primary_keywords=[
            "maintenance", "repair", "servicing", "dismantling", "line breaking", "overhaul",
            "hot bolting", "valve replacement", "equipment overhaul"
        ],
        semantic_patterns=[
            r"\b(?:during|performing|conducting)\s+(?:non[- ]routine\s+)?(?:maintenance|repair|servicing|dismantling|overhaul|line\s+break|hot\s+bolting)\b",
            r"\bmaintenance\s+(?:activity|work|crew|intervention|operation)\b",
        ],
        related_hazards=["Process Disturbance", "Human-Machine Interaction"],
        severity_contribution=10,
        possible_consequence="Unplanned release of stored energy during active equipment disassembly.",
        recommended_controls=[
            "Verify active Permit to Work (PTW) and Job Safety Analysis (JSA) prior to initiating maintenance.",
            "Conduct pre-job safety brief reviewing process isolation and emergency evacuation routes."
        ],
        action_priority="MEDIUM",
        immediate_control="Verify active Permit to Work (PTW) and Job Safety Analysis (JSA) prior to line breaking.",
        verification_step="Confirm positive mechanical and electrical isolation before equipment dismantling.",
        responsible_safety_role="Maintenance In-Charge / Shift Engineer",
        escalation_condition="Maintenance executed without signed PTW or simultaneous uncoordinated operations.",
        follow_up_action="Debrief maintenance crew and sign off completed work order."
    )
}


# ============================================================================
# 3. CONTEXTUAL QUALIFIER FILTER
# ============================================================================

class ContextualQualifierFilter:
    """Detects active negations, completed isolations, and mitigated safe states."""

    NEGATION_PREFIXES = [
        r"\b(?:no|zero|without\s+any|nil|negative\s+for|checked\s+and\s+no|eliminated|prevented|free\s+of|non[- ]hazardous)\s+(?:\w+\s+){0,3}",
        r"\b(?:was\s+not|is\s+not|not\s+found|no\s+trace\s+of|neither|unremarkable)\s+(?:\w+\s+){0,2}",
    ]

    MITIGATION_STATE_PATTERN = (
        r"\b(?:was|were|has\s+been|is|prior\s+to|properly|safely)\s+(?:isolated|de[- ]energized|depressurized|drained|vented|grounded|cleared|tested\s+negative|safely\s+anchored|tethered|certified|green[- ]tagged)\b"
        r"|\b(?:isolated|de[- ]energized|depressurized|drained)\s+(?:before|prior\s+to|via\s+loto|via\s+valve)\b"
        r"|\b(?:via|under|with)\s+loto\b"
        r"|\b0\s*%\s*lel\b"
        r"|\bwearing\s+(?:proper|full|mandatory|required|all)\s+(?:\w+\s+){0,2}(?:ppe|helmet|harness|ear\s*plugs|protection|gear)\b"
        r"|\btethered\s+to\s+(?:safety\s+)?lifeline\b"
        r"|\broutine\s+inspection\b"
    )

    ACTIVE_DAMAGE_PATTERN = (
        r"\b(?:shock|arc\s*flash|spark|sparking|frayed|exposed|submerged|cut|damaged|fault|burst|rupture|leak|leaking|violation|violated|bypassed|uninsulated|puddle|alarm)\b"
    )

    @classmethod
    def is_negated_or_mitigated(cls, sentence: str, target_match: str) -> bool:
        """Determines if a matched hazard substring in a sentence is negated or in an isolated/safe state."""
        sentence_lower = sentence.lower()
        clean_target = re.escape(target_match.lower())

        # 1. Check direct prefix negation
        for prefix in cls.NEGATION_PREFIXES:
            pattern = prefix + clean_target
            if re.search(pattern, sentence_lower):
                return True

        # 2. Check suffix negation
        suffix_pattern = clean_target + r"\s+(?:was\s+not|is\s+not|not\s+observed|not\s+detected|eliminated|cleared|prevented|zero|absent|negative)"
        if re.search(suffix_pattern, sentence_lower):
            return True

        # 3. Check safe / isolated state context
        has_mitigation = bool(re.search(cls.MITIGATION_STATE_PATTERN, sentence_lower))
        has_active_damage = bool(re.search(cls.ACTIVE_DAMAGE_PATTERN, sentence_lower))

        if has_mitigation and not has_active_damage:
            return True

        return False


# ============================================================================
# 4. SEMANTIC PROTOTYPE SIMILARITY MATCHER
# ============================================================================

class SemanticPrototypeMatcher:
    """Lightweight TF-IDF prototype matcher to score semantic alignment."""

    def __init__(self, taxonomy: Dict[str, PrecursorDefinition]):
        self.taxonomy = taxonomy
        self.precursor_keys = list(taxonomy.keys())

        self.corpus = [
            f"{p.name}. {p.description} Keywords: {', '.join(p.primary_keywords)}"
            for p in taxonomy.values()
        ]

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.prototype_matrix = self.vectorizer.fit_transform(self.corpus)

    def score(self, text: str) -> Dict[str, float]:
        """Calculates cosine similarity scores for text against each precursor prototype."""
        if not text or not text.strip():
            return {k: 0.0 for k in self.precursor_keys}

        text_vec = self.vectorizer.transform([text])
        sims = cosine_similarity(text_vec, self.prototype_matrix).flatten()

        return {
            self.precursor_keys[i]: round(float(sims[i]), 3)
            for i in range(len(self.precursor_keys))
        }


# ============================================================================
# 5. EXPLAINABLE RISK ENGINE & ACTION GENERATOR
# ============================================================================

class RiskEngine:
    """Transparent, Configurable & Explainable SIF Risk Engine with Evidence-Based Action Plans."""

    def __init__(
        self,
        custom_taxonomy: Optional[Dict[str, PrecursorDefinition]] = None,
        config: Optional[RiskScoringConfig] = None
    ):
        self.taxonomy = custom_taxonomy or SIF_TAXONOMY
        self.config = config or RiskScoringConfig()
        self.qualifier_filter = ContextualQualifierFilter()
        self.semantic_matcher = SemanticPrototypeMatcher(self.taxonomy)

    def _split_into_sentences(self, text: str) -> List[str]:
        raw_sentences = re.split(r"[.\n;!?]+", text)
        return [s.strip() for s in raw_sentences if len(s.strip()) > 3]

    def detect_precursors(self, report_text: str) -> List[Dict[str, Any]]:
        """Extracts and evaluates SIF hazard precursors from report text."""
        if not report_text or not report_text.strip():
            return []

        sentences = self._split_into_sentences(report_text)
        semantic_scores = self.semantic_matcher.score(report_text)
        detected_precursors: List[Dict[str, Any]] = []

        for key, p in self.taxonomy.items():
            matched_evidence: List[str] = []
            pattern_hits = 0

            for sent in sentences:
                sent_lower = sent.lower()

                # A. Semantic Regex Patterns
                for pattern in p.semantic_patterns:
                    matches = list(re.finditer(pattern, sent_lower))
                    for m in matches:
                        matched_str = m.group(0)
                        if not self.qualifier_filter.is_negated_or_mitigated(sent, matched_str):
                            matched_evidence.append(matched_str)
                            pattern_hits += 2

                # B. Primary Keywords
                for kw in p.primary_keywords:
                    pattern_kw = r"\b" + re.escape(kw) + r"\b"
                    if re.search(pattern_kw, sent_lower):
                        if not self.qualifier_filter.is_negated_or_mitigated(sent, kw):
                            if kw not in matched_evidence:
                                matched_evidence.append(kw)
                                pattern_hits += 1

            # Header check for maintenance to avoid false positive from sector header
            if key == "maintenance" and matched_evidence:
                header_match = re.search(r"department:\s*maintenance", report_text.lower())
                body_without_header = re.sub(r"department:\s*maintenance", "", report_text.lower())
                if header_match and not any(kw in body_without_header for kw in p.primary_keywords):
                    matched_evidence = []

            proto_sim = semantic_scores.get(key, 0.0)

            if matched_evidence:
                unique_evidence = list(dict.fromkeys(matched_evidence))

                # Hybrid Confidence Calculation
                if pattern_hits >= 4 or (pattern_hits >= 2 and proto_sim > 0.15):
                    confidence = 0.95
                elif pattern_hits >= 2 or proto_sim > 0.12:
                    confidence = 0.88
                else:
                    confidence = 0.78

                precursor_data = {
                    "precursor": p.name,
                    "evidence": unique_evidence,
                    "confidence": confidence,
                    "contribution": p.severity_contribution,
                    "factor": p.factor,
                    "label": p.name,
                    "name": p.name,
                    "precursor_id": p.precursor_id,
                    "description": p.description,
                    "confidence_type": "hybrid_contextual_semantic",
                    "semantic_alignment_score": proto_sim,
                    "related_hazards": p.related_hazards,
                    "possible_consequence": p.possible_consequence,
                    "recommended_controls": p.recommended_controls,
                }
                detected_precursors.append(precursor_data)

        return detected_precursors

    def analyze(
        self,
        report_text: str,
        predicted_severity: Optional[str] = None,
        similar_incidents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Calculates transparent, explainable SIF risk score and generates evidence-based corrective actions."""
        if not report_text or not report_text.strip():
            return {
                "score": 0,
                "level": "LOW",
                "summary": "Empty report submitted. Zero risk precursors detected.",
                "formula_explanation": "Total Score = 0/100 (No content evaluated)",
                "components": [],
                "precursors": [],
                "corrective_actions": [],
                "recommended_actions": ["Submit detailed field observation to initiate safety assessment."]
            }

        detected_precursors = self.detect_precursors(report_text)

        components: List[Dict[str, Any]] = []
        corrective_actions: List[Dict[str, Any]] = []
        base_precursor_score = 0

        # --------------------------------------------------------------------
        # 1. EVALUATE PRECURSOR COMPONENTS & CORRECTIVE ACTIONS
        # --------------------------------------------------------------------
        for p_data in detected_precursors:
            key = p_data["factor"]
            p = self.taxonomy.get(key)
            if not p:
                continue

            base_precursor_score += p_data["contribution"]

            # Add to explainable risk components
            components.append({
                "factor": p_data["factor"],
                "label": p_data["label"],
                "contribution": p_data["contribution"],
                "category": "SIF Precursor Hazard",
                "evidence": p_data["evidence"]
            })

            # Generate Evidence-Based Structured Corrective Action
            evidence_summary = ", ".join(f"'{e}'" for e in p_data["evidence"][:3])
            action_item = CorrectiveAction(
                action=f"{p.immediate_control} Then {p.verification_step}",
                priority=p.action_priority,
                reason=f"Directly mandated by detected {p.name} evidence: [{evidence_summary}].",
                related_precursor=p.name,
                precursor_id=p.precursor_id,
                immediate_control=p.immediate_control,
                verification_step=p.verification_step,
                responsible_safety_role=p.responsible_safety_role,
                escalation_condition=p.escalation_condition,
                follow_up_action=p.follow_up_action,
                requires_human_approval=True
            )
            corrective_actions.append(action_item.to_dict())

        # --------------------------------------------------------------------
        # 2. MULTI-HAZARD COMPOUND SYNERGY COMPONENT
        # --------------------------------------------------------------------
        detected_keys = {item["factor"] for item in detected_precursors}
        compound_boost = 0
        compound_reasons = []

        if "high_pressure" in detected_keys and ("leakage" in detected_keys or "fire_gas" in detected_keys):
            compound_boost += self.config.compound_hazard_boost
            compound_reasons.append("High Pressure + Flammable Gas Release (Blowout / Jet Fire Synergy)")

        if "confined_space" in detected_keys and ("toxic_chemical" in detected_keys or "leakage" in detected_keys):
            compound_boost += self.config.compound_hazard_boost
            compound_reasons.append("Confined Space Entry + Toxic/Flammable Atmosphere (Asphyxiation / Trap Synergy)")

        if "electrical" in detected_keys and ("leakage" in detected_keys or "fire_gas" in detected_keys):
            compound_boost += self.config.compound_hazard_boost
            compound_reasons.append("Electrical Hazard + Flammable Hydrocarbon (Zone 1 Ignition Synergy)")

        if "fall_hazard" in detected_keys and "dropped_objects" in detected_keys:
            compound_boost += self.config.compound_hazard_boost
            compound_reasons.append("Elevated Work + Dropped Object Threat (Overhead Drop Synergy)")

        if compound_boost > 0:
            components.append({
                "factor": "compound_hazard_synergy",
                "label": "Multi-Hazard Compounding Synergy",
                "contribution": compound_boost,
                "category": "Synergy Risk Escalation",
                "evidence": compound_reasons
            })

            # Add emergency coordination action for compounding multi-hazard
            corrective_actions.insert(0, {
                "action": "Convene immediate on-site safety emergency coordination meeting and initiate joint ESD/LOTO verification.",
                "priority": "IMMEDIATE",
                "reason": f"Compounding multi-hazard interaction active: {', '.join(compound_reasons)}.",
                "related_precursor": "Multi-Hazard Compounding Interaction",
                "precursor_id": "SIF-COMPOUND",
                "immediate_control": "Enforce strict Stop-Work across all concurrent operations in affected zone.",
                "verification_step": "Joint inspection by Process Safety Lead and Area HSE Officer prior to any operational resumption.",
                "responsible_safety_role": "Installation Manager & Lead Safety Officer",
                "escalation_condition": "Any simultaneous loss of containment with unisolated stored energy.",
                "follow_up_action": "Execute formal Process Hazard Analysis (PHA) review.",
                "requires_human_approval": True
            })

        # --------------------------------------------------------------------
        # 3. OPTIONAL AUXILIARY SEVERITY INTEGRATION
        # --------------------------------------------------------------------
        severity_factor = 0
        if predicted_severity and predicted_severity in self.config.severity_level_weights:
            if base_precursor_score > 0:
                severity_factor = self.config.severity_level_weights[predicted_severity]
                if severity_factor > 0:
                    components.append({
                        "factor": "severity_model_alignment",
                        "label": f"ML Severity Level {predicted_severity} Alignment",
                        "contribution": severity_factor,
                        "category": "Model Inference Adjustment",
                        "evidence": [f"Linear SVM classified report as Potential Level {predicted_severity}"]
                    })

        # Calculate final clamped score
        total_raw_score = base_precursor_score + compound_boost + severity_factor
        total_score = min(max(total_raw_score, self.config.min_score), self.config.max_score)

        # --------------------------------------------------------------------
        # 4. EXPLAINABLE RISK TIER ASSIGNMENT
        # --------------------------------------------------------------------
        if total_score >= self.config.tier_critical_threshold:
            risk_level = "CRITICAL"
        elif total_score >= self.config.tier_high_threshold:
            risk_level = "HIGH"
        elif total_score >= self.config.tier_medium_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # --------------------------------------------------------------------
        # 5. MATHEMATICAL FORMULA EXPLANATION
        # --------------------------------------------------------------------
        formula_parts = [f"Base Precursors ({base_precursor_score})"]
        if compound_boost > 0:
            formula_parts.append(f"Compound Synergy (+{compound_boost})")
        if severity_factor > 0:
            formula_parts.append(f"Severity Level {predicted_severity} (+{severity_factor})")

        formula_str = " + ".join(formula_parts) + f" = {total_score}/100"

        # --------------------------------------------------------------------
        # 6. CONCISE RECOMMENDED ACTIONS (Backward Compatibility)
        # --------------------------------------------------------------------
        recommended_actions = [ca["action"] for ca in corrective_actions]
        if not recommended_actions:
            recommended_actions.append("Standard operational vigilance and routine OISD field inspection protocols apply.")

        # --------------------------------------------------------------------
        # 7. NARRATIVE SUMMARY GENERATION
        # --------------------------------------------------------------------
        if compound_boost > 0:
            summary = (
                f"CRITICAL SIF ALERT: Compounding hazardous precursors detected ({', '.join(item['label'] for item in detected_precursors)}). "
                f"Multi-hazard interaction escalates overall risk to {total_score}/100 ({risk_level} Tier)."
            )
        elif len(detected_precursors) >= 2:
            summary = (
                f"Multiple industrial risk precursors detected ({', '.join(item['label'] for item in detected_precursors)}). "
                f"Evaluated risk score is {total_score}/100 ({risk_level} Tier)."
            )
        elif len(detected_precursors) == 1:
            summary = (
                f"Precursor detected: {detected_precursors[0]['label']}. "
                f"Assessed risk contribution is +{detected_precursors[0]['contribution']} points ({risk_level} Tier)."
            )
        else:
            summary = "No critical Serious Injury & Fatality (SIF) precursors were detected in the submitted observation narrative."

        return {
            "score": total_score,
            "level": risk_level,
            "summary": summary,
            "formula_explanation": formula_str,
            "base_precursor_score": base_precursor_score,
            "compound_risk_boost": compound_boost,
            "components": components,
            "precursors": detected_precursors,
            "corrective_actions": corrective_actions,
            "recommended_actions": recommended_actions
        }