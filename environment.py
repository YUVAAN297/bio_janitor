import json
import random
import os
from typing import List, Dict, Any
from openenv.core.env_server import Environment, State
from models import ComplianceAction, ComplianceObservation, ComplianceState

STRICT_SCORE_MIN = 0.01
STRICT_SCORE_MAX = 0.99
DEFAULT_TASK_SEEDS = {
    "easy_gdpr_obvious": "easy-fixed-seed-2026",
    "medium_gdpr_subtle": "medium-fixed-seed-2026",
    "hard_gdpr_ccpa_multi": "hard-fixed-seed-2026",
}


def strict_open_interval_score(value: float) -> float:
    return max(STRICT_SCORE_MIN, min(STRICT_SCORE_MAX, float(value)))


def resolve_episode_seed(task_name: str, provided_seed: Any = None) -> str:
    base_seed = str(
        provided_seed
        or os.getenv("OPENENV_SEED")
        or DEFAULT_TASK_SEEDS.get(task_name, f"default-{task_name}")
    )
    return f"{task_name}:{base_seed}"

class ClauseGenerator:
    """The Procedural Engine armed with distinct legal scenarios."""
    
    TEMPLATES = {
        # EASY
        "retention_period": {
            "compliant": "Data Retention: We strictly retain user data for exactly {days} days before permanent deletion.",
            "violating": "Data Retention: We retain your personal data indefinitely to support our {system}.",
            "violation_msg": "GDPR Article 13(2)(a) - No data retention period specified."
        },
        "right_to_erasure": {
            "compliant": "User Rights: You have the right to request the erasure of your personal data at any time.",
            "violating": "Records: Due to technical constraints of our {system}, user profiles are immutable once created.",
            "violation_msg": "GDPR Article 17 - Total denial of the right to erasure."
        },
        "controller_contact": {
            "compliant": "Data Controller: {company} Inc, reachable at privacy@{domain}.com.",
            "violating": "Contact: Please reach out to our general support line for any questions.",
            "violation_msg": "GDPR Article 13(1)(a) - No controller or DPO contact info provided."
        },
        "lawful_basis": {
            "compliant": "Lawful Basis: We process your data strictly based on your explicit consent.",
            "violating": "Processing: We process your data automatically as soon as you access the {system}.",
            "violation_msg": "GDPR Article 6 - No lawful basis for processing stated."
        },
        "unencrypted_http_transmission": {
            "compliant": "Security: All data is transmitted via secure {protocol} encryption.",
            "violating": "Security: User data is transmitted via standard HTTP protocols to our legacy servers.",
            "violation_msg": "GDPR Article 32 - Security of processing. Data is transmitted over unencrypted HTTP."
        },
        "data_minimization": {
            "compliant": "Data Minimization: We only collect information strictly necessary for service delivery.",
            "violating": "Collection Scope: We collect all available data including {invasive_data}.",
            "violation_msg": "GDPR Article 5(1)(c) - Failure to observe data minimization principle."
        },
        "purpose_limitation": {
            "compliant": "Purpose: Data is used solely for account management and core service improvement.",
            "violating": "Usage: We may use your accumulated profile data for any internal or external business purpose.",
            "violation_msg": "GDPR Article 5(1)(b) - No purpose limitation specified."
        },
        "right_to_rectification": {
            "compliant": "Rectification: You may correct inaccurate personal data via your account dashboard.",
            "violating": "Records: User records cannot be altered; we cannot change profile information once submitted.",
            "violation_msg": "GDPR Article 16 - No right to rectification mentioned."
        },
        "right_to_withdraw_consent": {
            "compliant": "Withdrawal: You have the right to withdraw your consent at any time without affecting prior processing.",
            "violating": "Commitment: Once consent is granted during signup, it remains binding for the lifetime of the account.",
            "violation_msg": "GDPR Article 7(3) - Right to withdraw consent missing."
        },
        "lodge_complaint_authority": {
            "compliant": "Complaints: You have the right to lodge a complaint with a relevant data protection supervisory authority.",
            "violating": "Disputes: All disputes must be settled through binding arbitration; you waive the right to lodge formal regulatory complaints.",
            "violation_msg": "GDPR Article 13(2)(d) - Right to lodge a complaint with a supervisory authority missing."
        },

        # MEDIUM
        "invalid_consent": {
            "compliant": "Consent: Users must actively check the box during {action} to opt-in.",
            "violating": "Consent: We collect personal data based on your consent, assumed by pre-ticked boxes during {action}.",
            "violation_msg": "GDPR Article 4(11) - Pre-ticked boxes do not constitute valid consent."
        },
        "vague_retention": {
            "compliant": "Retention: We keep logs for exactly {months} months for security auditing.",
            "violating": "Retention: We keep your personal data for as long as necessary to provide our services.",
            "violation_msg": "GDPR Article 13(2)(a) - 'As long as necessary' is too vague."
        },
        "restricted_erasure": {
            "compliant": "Erasure: You can erase your data via your account settings at any point.",
            "violating": "Erasure: You have the right to erase your data, except for our internal analytics needs.",
            "violation_msg": "GDPR Article 17 - Excessive exceptions to the right of erasure."
        },
        "data_portability": {
            "compliant": "Portability: You can download your data in a machine-readable {format} format.",
            "violating": "Portability: We do not allow data exports or downloads to protect proprietary {format} schemas.",
            "violation_msg": "GDPR Article 20 - Refusal to provide data portability."
        },
        "breach_notification_delay": {
            "compliant": "Data Breach: We will notify the supervisory authority within 72 hours of discovering a breach.",
            "violating": "Data Breach: We will notify the supervisory authority within {breach_days} days of discovering a breach.",
            "violation_msg": "GDPR Article 33 - Breach notification timeframe exceeds 72 hours."
        },
        "automated_decision_making": {
            "compliant": "Automation: Significant account decisions are always reviewed by a human moderator.",
            "violating": "Automation: Account terminations are processed entirely by automated algorithms with no manual review.",
            "violation_msg": "GDPR Article 22 - Unlawful automated decision-making without human intervention."
        },
        "processor_contracts": {
            "compliant": "Sub-processors: We ensure all third-party vendors sign strict data processing agreements.",
            "violating": "Vendors: We use third-party tools to process data; we are not responsible for their internal compliance standards.",
            "violation_msg": "GDPR Article 28 - Missing guarantees regarding sub-processor compliance."
        },
        "cookie_wall": {
            "compliant": "Cookies: You may reject non-essential cookies and still access our content.",
            "violating": "Access: You must accept all tracking cookies to view any content on this website.",
            "violation_msg": "GDPR Article 7(4) - Forced consent via cookie wall."
        },
        "legitimate_interest_vague": {
            "compliant": "Legitimate Interests: We process telemetry data to prevent fraud and DDOS attacks.",
            "violating": "Legitimate Interests: We process your data for our company's legitimate interests as we see fit.",
            "violation_msg": "GDPR Article 13(1)(d) - Legitimate interests are not specified."
        },
        "cross_border_transfers": {
            "compliant": "International Data: Data transferred outside the EEA is protected using Standard Contractual Clauses.",
            "violating": "International Data: We routinely transfer EU data to unprotected servers globally without specific legal safeguards.",
            "violation_msg": "GDPR Article 46 - International transfers lack proper safeguards (e.g., SCCs)."
        },

        # HARD
        "gdpr_opt_out": {
            "compliant": "Data Collection: We collect data only after you actively click 'I Agree'.",
            "violating": "Data Collection: By using the site, you opt-out if you email us within {opt_out_days} days.",
            "violation_msg": "GDPR Article 6 - Opt-out consent is invalid; requires active opt-in."
        },
        "ccpa_sale_disclosure": {
            "compliant": "Data Sharing: We do not sell your personal information.",
            "violating": "Data Sharing: We share profiles for ads. We do not officially 'sell' data, so no 'Do Not Sell' link is provided.",
            "violation_msg": "CCPA 1798.120 - 'Sharing' for ads constitutes a 'sale', requiring Do Not Sell disclosure."
        },
        "ccpa_non_discrimination": {
            "compliant": "Non-Discrimination: We will not deny goods to you for exercising privacy rights.",
            "violating": "Service Restriction: Exercising your deletion rights will result in immediate termination of your basic tier service.",
            "violation_msg": "CCPA 1798.125 - Discriminatory practices against consumers exercising privacy rights."
        },
        "gdpr_ccpa_conflict": {
            "compliant": "Jurisdiction: European users must explicitly opt-in; Californian users may opt-out.",
            "violating": "Jurisdiction: We apply standard opt-out consent to all global users, including EU residents.",
            "violation_msg": "GDPR Art 6 & CCPA 1798.120 Conflict - Improper consent mechanisms across borders."
        },
        "ccpa_financial_incentive": {
            "compliant": "Incentives: We do not offer financial incentives in exchange for the retention of personal data.",
            "violating": "Incentives: Users receive a {discount}% discount on subscriptions if they waive their CCPA deletion rights.",
            "violation_msg": "CCPA 1798.125 - Financial incentive offered without proper notice/consent."
        },
        "ccpa_authorized_agent": {
            "compliant": "Agents: You may designate an authorized agent to make privacy requests on your behalf.",
            "violating": "Agents: We only process privacy requests submitted directly by the account owner; proxy requests are ignored.",
            "violation_msg": "CCPA 1798.130 - Failure to allow requests via authorized agents."
        },
        "cpra_sharing_opt_out": {
            "compliant": "Targeted Ads: You may opt-out of having your data shared for cross-context behavioral advertising.",
            "violating": "Targeted Ads: We share your usage data with ad networks. You cannot opt-out of this sharing.",
            "violation_msg": "CPRA - Failure to provide opt-out for cross-context behavioral advertising."
        },
        "ccpa_lookback_period": {
            "compliant": "Data Access: You may request access to all personal information we hold about you.",
            "violating": "Data Access: You may only request access to data collected within the preceding 12 months.",
            "violation_msg": "CCPA 1798.130 - Restricting access requests to a 12-month lookback period."
        },
        "coppa_gdpr_age_mismatch": {
            "compliant": "Children: We do not process data of users under 16 without explicit parental consent.",
            "violating": "Children: We freely process data for users aged 13 and above globally without requiring parental authorization.",
            "violation_msg": "GDPR Article 8 / COPPA Conflict - Processing children's data without parental consent."
        },
        "gdpr_article_27_rep": {
            "compliant": "EU Representative: Our designated EU representative can be contacted at eurep@{domain}.eu.",
            "violating": "EU Representative: As a US-based company, we do not maintain any representatives in the European Union.",
            "violation_msg": "GDPR Article 27 - Failure to designate a representative in the EU for non-EU entities."
        },
        
        # EXTREME / MODERN (AI, Biometrics, Dark Patterns)
        "ai_training_consent": {
            "compliant": "AI Training: We do not use your personal data to train our {ai_model} without your explicit, separate opt-in consent.",
            "violating": "AI Training: By using this service, you grant us an irrevocable right to use all your inputted data to train and fine-tune our {ai_model}.",
            "violation_msg": "GDPR Article 5(1)(b) - Unlawful repurposing of user data for AI training without explicit consent."
        },
        "biometric_retention": {
            "compliant": "Biometrics: {biometric_type} data is stored locally on your device and is never transmitted to our servers.",
            "violating": "Biometrics: We collect {biometric_type} for authentication and store it indefinitely on our {system}.",
            "violation_msg": "GDPR Article 9 - Processing of special categories of personal data (biometrics) without strict safeguards/limits."
        },
        "dark_pattern_deletion": {
            "compliant": "Account Deletion: You can permanently delete your account with a single click in your account settings.",
            "violating": "Account Deletion: To delete your account, you must print, notarize, and mail a physical letter to our headquarters.",
            "violation_msg": "CCPA 1798.130 / GDPR Art 12 - Placing undue burden/dark patterns on the exercise of data subject rights."
        },
        "hidden_data_brokers": {
            "compliant": "Third Parties: We maintain a public, up-to-date registry of all {third_party} we share data with.",
            "violating": "Third Parties: We routinely share your profile with {third_party}, but we reserve the right to keep their identities confidential.",
            "violation_msg": "GDPR Article 13(1)(e) - Failure to disclose the specific recipients or categories of recipients of personal data."
        },
        "automated_profiling_bias": {
            "compliant": "Profiling: Users may opt-out of our {ai_model} evaluating their personal preferences.",
            "violating": "Profiling: Our {ai_model} continuously monitors your behavior to determine your socioeconomic status. You cannot opt out of this core feature.",
            "violation_msg": "GDPR Article 22 - Subjecting users to automated profiling with legal/significant effects without opt-out."
        },
        "employee_monitoring": {
            "compliant": "Workplace Privacy: Employee monitoring is strictly limited to security logs and requires HR authorization.",
            "violating": "Workplace Privacy: We record {invasive_data} of all employees globally, including personal devices connected to our network, without notification.",
            "violation_msg": "GDPR Article 88 - Unlawful monitoring of employees without necessity or transparency."
        },
        "dsar_charging_fees": {
            "compliant": "Data Requests: Processing your Data Subject Access Request (DSAR) is completely free of charge.",
            "violating": "Data Requests: A non-refundable processing fee of $50 is required before we will action your data deletion request.",
            "violation_msg": "GDPR Article 12(5) - Unlawfully charging fees for standard data subject requests."
        },
        "sale_of_childrens_data": {
            "compliant": "Minors: We absolutely never sell the personal information of consumers we know are under 16 years of age.",
            "violating": "Minors: Data collected from our youth platform (ages 13-16) is aggregated and sold to {third_party} for targeted advertising.",
            "violation_msg": "CCPA 1798.120(c) - Selling personal information of minors without affirmative authorization."
        },
        "inferred_data_classification": {
            "compliant": "Inferred Data: Any assumptions we generate about your health or political views are treated as highly sensitive data requiring explicit consent.",
            "violating": "Inferred Data: Since we merely 'guess' your health status using our {ai_model}, we treat it as non-sensitive standard data.",
            "violation_msg": "CJEU Jurisprudence / GDPR Art 9 - Inferred sensitive data must be protected as special category data."
        },
        "unilateral_policy_changes": {
            "compliant": "Policy Updates: If we materially change this policy, we will request your renewed consent before applying it to your existing data.",
            "violating": "Policy Updates: We may fundamentally alter how we use your existing data at any time. Continued use of our {system} constitutes absolute consent.",
            "violation_msg": "GDPR Article 7 - Consent is not valid if the controller can unilaterally change the terms of processing."
        }
    }

    @staticmethod
    def generate(seed: str, difficulty: str, enabled_types: List[str], target_violations: int):
        rng = random.Random(seed)
        generated_clauses = {}
        
        # Procedural Modifiers (Massively Expanded)
        dynamic_vars = {
            "days": rng.randint(30, 365),
            "months": rng.randint(6, 24),
            "breach_days": rng.randint(10, 45),
            "opt_out_days": rng.randint(14, 60),
            "discount": rng.randint(5, 25),
            "system": rng.choice(["legacy mainframe", "cloud infrastructure", "analytics engine", "edge nodes"]),
            "domain": rng.choice(["globaltech", "analytics-hub", "data-stream", "techcorp", "aivision"]),
            "company": rng.choice(["TechCorp", "GlobalData", "Synapse", "OmniCorp", "NeuralNet"]),
            "protocol": rng.choice(["TLS 1.3", "HTTPS", "SSL", "unencrypted UDP"]),
            "format": rng.choice(["JSON", "XML", "CSV", "proprietary binary"]),
            "action": rng.choice(["registration", "signup", "checkout", "app installation"]),
            "invasive_data": rng.choice(["background processes", "real-time location", "local network contacts", "keystroke logs"]),
            "ai_model": rng.choice(["Large Language Model", "predictive neural network", "generative AI", "automated profiling engine"]),
            "biometric_type": rng.choice(["retinal scans", "facial recognition geometry", "voiceprint analysis", "gait tracking"]),
            "third_party": rng.choice(["marketing affiliates", "data brokers", "unnamed subsidiaries", "ad-tech partners"])
        }
        
        actual_violating_keys = set(rng.sample(enabled_types, min(target_violations, len(enabled_types))))
        
        for c_type in enabled_types:
            template = ClauseGenerator.TEMPLATES.get(c_type)
            if not template: continue
            
            if c_type in actual_violating_keys:
                text = template["violating"].format(**dynamic_vars)
                violation = template["violation_msg"]
            else:
                text = template["compliant"].format(**dynamic_vars)
                violation = None
            
            generated_clauses[c_type] = {"text": text, "violation": violation}
            
        return generated_clauses

class ComplianceAuditorEnv(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self):
        super().__init__()
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self._state = ComplianceState(
            episode_id="audit-init", step_count=0, task_id="easy_gdpr_obvious",
            precision=0.0, recall=0.0, ground_truth_keys=[]
        )
        self.policy_text = ""
        self.ground_truth = {}
        self.flagged_issues = []
        self.suggested_fixes = set()
        self.available_tools = [
            "read_document",
            "check_regulation",
            "search_web",
            "ask_expert",
            "compare_clauses",
            "flag_violation",
            "suggest_fix",
            "submit_report",
        ]
        
        self.regulations = {}
        self.neutral_boilerplate = []
        base_path = os.path.join(self.root_dir, "tasks", "base_knowledge.json")
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.regulations = data.get("regulations", {})
                self.neutral_boilerplate = data.get("neutral_boilerplate", [])

    def _generate_dynamic_document(self, task_name: str, seed: str):
        rng = random.Random(f"{seed}:document")
        task_file = os.path.join(self.root_dir, "tasks", f"{task_name}.json")
        if not os.path.exists(task_file):
            task_file = os.path.join(self.root_dir, "tasks", "easy_gdpr_obvious.json")
            
        with open(task_file, "r", encoding="utf-8") as f:
            task_config = json.load(f)
            
        enabled_templates = task_config.get("enabled_templates", ["retention_period"])
        
        default_violating = task_config.get("default_violations", 3)
        num_violating = int(os.getenv("NUM_VIOLATIONS", str(default_violating)))
        num_violating = min(num_violating, len(enabled_templates))
        
        procedural_data = ClauseGenerator.generate(
            seed=seed, 
            difficulty=task_config.get("difficulty", "easy"), 
            enabled_types=enabled_templates,
            target_violations=num_violating
        )

        paragraphs = []
        self.ground_truth = {}

        for key, val in procedural_data.items():
            paragraphs.append(val["text"])
            if val["violation"]:
                self.ground_truth[key] = val["violation"]

        if self.neutral_boilerplate:
            paragraphs.extend(
                rng.sample(self.neutral_boilerplate, min(3, len(self.neutral_boilerplate)))
            )
        
        rng.shuffle(paragraphs)
        self.policy_text = "\n\n".join([f"PRIVACY POLICY — UID: {seed[:8]}", "Last Updated: October 2023", ""] + paragraphs)

        self.policy_text = "\n\n".join(
            [f"PRIVACY POLICY - UID: {seed[:8]}", "Last Updated: October 2023", ""]
            + paragraphs
        )

    def _update_live_metrics(self):
        true_positives = sum(1 for f in self.flagged_issues if not f.get("invalid"))
        false_positives = sum(1 for f in self.flagged_issues if f.get("invalid"))
        total_actual = len(self.ground_truth)
        
        self._state.precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        self._state.recall = true_positives / total_actual if total_actual > 0 else 0.0

    def reset(self, **kwargs) -> ComplianceObservation:
        task_name = kwargs.get("task_name", "easy_gdpr_obvious")
        episode_seed = resolve_episode_seed(task_name, kwargs.get("seed"))
        
        self._state.episode_id = f"audit-{episode_seed[:8]}"
        self._state.step_count = 0
        self._state.task_id = task_name
        self._state.precision = 0.0
        self._state.recall = 0.0
        
        self._generate_dynamic_document(task_name, episode_seed)
        self._state.ground_truth_keys = list(self.ground_truth.keys())
        
        self.flagged_issues = []
        self.suggested_fixes = set()
        
        task_file = os.path.join(self.root_dir, "tasks", f"{task_name}.json")
        default_max_steps = 15
        if os.path.exists(task_file):
            with open(task_file, "r", encoding="utf-8") as f:
                default_max_steps = json.load(f).get("default_max_steps", 15)
                
        max_steps = int(os.getenv("MAX_STEPS", str(default_max_steps)))
        
        return ComplianceObservation(
            done=False, reward=0.0, 
            message=f"Initialized audit for {task_name}. Max steps: {max_steps}.",
            flagged_issues=self.flagged_issues,
            available_tools=self.available_tools,
            max_steps=max_steps,
            error=None
        )

    def step(self, action: ComplianceAction) -> ComplianceObservation:
        self._state.step_count += 1
        reward, message, error, done = 0.0, "", None, False
        
        task_file = os.path.join(self.root_dir, "tasks", f"{self._state.task_id}.json")
        default_max_steps = 15
        if os.path.exists(task_file):
            with open(task_file, "r", encoding="utf-8") as f:
                default_max_steps = json.load(f).get("default_max_steps", 15)
        max_steps = int(os.getenv("MAX_STEPS", str(default_max_steps)))
        
        if action.tool == "read_document":
            message = f"DOCUMENT TEXT:\n{self.policy_text}"
            if self._state.step_count <= 2: reward += 0.05 
                
        elif action.tool == "check_regulation":
            reg_query = action.parameters.get("query", "")
            matches = [v for k, v in self.regulations.items() if k.lower() in reg_query.lower()]
            message = f"REGULATION TEXT:\n" + "\n".join(matches) if matches else "Regulation not found."
            reward += 0.02 
            
        elif action.tool == "search_web":
            query = action.parameters.get("query", "")
            message = f"Simulated Web Search for '{query}': Regulatory guidance implies explicit consent is mandatory."
            reward += 0.01 
            
        elif action.tool == "ask_expert":
            issue_id = action.parameters.get("issue_id", "")
            message = f"Expert Hint: Double check the opt-in/opt-out mechanisms related to {issue_id}."
            reward += 0.01 
            
        elif action.tool == "compare_clauses":
            message = "Similarity Score: 0.88. Clauses are highly similar but jurisdictionally different."
            reward += 0.01 

        elif action.tool == "flag_violation":
            issue_id = action.parameters.get("issue_id", "").strip().lower()
            if any(f["issue_id"] == issue_id for f in self.flagged_issues):
                error, reward = "Issue already flagged.", -0.05
            elif issue_id in self.ground_truth:
                self.flagged_issues.append({"issue_id": issue_id, "explanation": "Valid"})
                base_reward = 0.15
                early_bonus = 0.10 if self._state.step_count <= 5 else 0.0
                message, reward = f"Correctly flagged: {issue_id}", base_reward + early_bonus
            else:
                self.flagged_issues.append({"issue_id": issue_id, "explanation": "Invalid", "invalid": True})
                error, reward = "False positive.", -0.10
                
        elif action.tool == "suggest_fix":
            issue_id = action.parameters.get("issue_id", "").strip().lower()
            if any(f["issue_id"] == issue_id for f in self.flagged_issues) and issue_id in self.ground_truth:
                if issue_id not in self.suggested_fixes:
                    self.suggested_fixes.add(issue_id)
                    message, reward = f"Fix proposed for {issue_id}.", 0.05
                else:
                    error, reward = "Fix already suggested.", 0.0
            else:
                error, reward = "Cannot suggest fix for unflagged issue.", -0.05
                
        elif action.tool == "submit_report":
            self._update_live_metrics()
            f1_score = 2 * (self._state.precision * self._state.recall) / (self._state.precision + self._state.recall) if (self._state.precision + self._state.recall) > 0 else 0.0
            reward, done = strict_open_interval_score(f1_score), True
            message = f"Audit submitted. F1: {reward:.2f}."
            
        else:
            error, reward = f"Unknown tool.", -0.1

        self._update_live_metrics()

        timed_out = self._state.step_count >= max_steps
        if timed_out and not done:
            message = (message or "") + " WARNING: Step limit reached."

        reward = round(max(-1.0, min(1.0, reward)), 2)

        return ComplianceObservation(
            done=done or timed_out,
            reward=reward, message=message or error,
            flagged_issues=self.flagged_issues,
            available_tools=self.available_tools,
            max_steps=max_steps,
            error=error
        )

    @property
    def state(self) -> State:
        return self._state

def _calculate_trajectory_f1(task_name: str, trajectory: List[Dict[str, Any]]) -> float:
    if not trajectory:
        return STRICT_SCORE_MIN
    
    last_step = trajectory[-1]
    info = last_step.get("info", {})
    state_dict = info.get("state", {}) if "state" in info else last_step.get("state", {})
    actual_violations = state_dict.get("ground_truth_keys", [])
    
    flagged = {step.get("action", {}).get("parameters", {}).get("issue_id", "").strip().lower() 
                for step in trajectory if step.get("action", {}).get("tool") == "flag_violation"}
    flagged.discard("")
                
    true_positives = sum(1 for i in flagged if i in actual_violations)
    false_positives = len(flagged) - true_positives
    total_actual = len(actual_violations)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / total_actual if total_actual > 0 else 0.0
    
    if precision + recall > 0:
        return strict_open_interval_score(
            2 * (precision * recall) / (precision + recall)
        )
    return STRICT_SCORE_MIN

def grade_easy_gdpr_obvious(trajectory: List[Dict[str, Any]]) -> float:
    return _calculate_trajectory_f1("easy_gdpr_obvious", trajectory)

def grade_medium_gdpr_subtle(trajectory: List[Dict[str, Any]]) -> float:
    return _calculate_trajectory_f1("medium_gdpr_subtle", trajectory)

def grade_hard_gdpr_ccpa_multi(trajectory: List[Dict[str, Any]]) -> float:
    return _calculate_trajectory_f1("hard_gdpr_ccpa_multi", trajectory)
