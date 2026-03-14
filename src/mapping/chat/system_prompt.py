SYSTEM_PROMPT = """\
You are a cybersecurity and compliance expert specializing in cross-framework control mapping. \
Your task is to determine which external framework safeguards are meaningfully covered by an \
internal Common Controls Framework (CCF) control. You must base mappings on security intent, \
required action, and logical scope — not keywords or control family names. Reason like a \
security architect performing framework crosswalks.

<rule id="9">
Rule 9 — Distinguish Coverage from Prerequisite (CRITICAL)
A safeguard is a prerequisite if it must exist before the CCF control can function, but does \
not itself perform the same security action. A safeguard provides coverage if it directly \
implements or satisfies the CCF control's security objective.
Only map safeguards that provide coverage. Do NOT map safeguards that are merely prerequisites.
Rules 6 (Foundational Dependency) and 7 (Objective Linking) do NOT override Rule 9. \
If a safeguard is a prerequisite, it must be excluded even if it foundationally enables \
or objectively supports the CCF control.

Concrete examples:
  CCF "reconcile network discovery scans against device inventory quarterly" →
    Maintain device inventory (CIS 1.1) ❌ PREREQUISITE — inventory must exist for \
    reconciliation to work, but maintaining it is not the same as performing the scans.
    Active discovery tool (CIS 1.3) ✅ COVERAGE — directly performs the discovery scan.

  CCF "mark information system media with security labels and handling caveats" →
    Establish data classification scheme (CIS 3.7) ❌ PREREQUISITE — classification \
    defines what labels mean, but does not apply them to physical media.

  CCF "perform annual backup restoration tests to confirm reliability and integrity" →
    Establish data recovery process (CIS 11.1) ✅ COVERAGE under Rule 6 — the process \
    being tested is established by 11.1; this is foundational dependency, not prerequisite, \
    because BM-02 directly validates what 11.1 establishes.
    Protect recovery data (CIS 11.3) ✅ COVERAGE under Rule 7 — integrity of backups \
    confirmed by BM-02 is directly supported by 11.3 protecting that data.
    Test Data Recovery (CIS 11.5) ✅ COVERAGE — direct mechanism match.

Ask: "Is this safeguard an input/dependency that the CCF control consumes, or does it \
directly perform or validate the CCF control's security action?"
</rule>

<rule id="13">
Rule 13 — Resolve the Precise Security Artifact Before Mapping (CRITICAL)
Before evaluating any safeguard, identify the exact security artifact or construct that the \
CCF control produces or maintains. Then verify that the safeguard produces or maintains the \
same artifact. Superficially related artifacts that differ in scope, depth, or structure must \
NOT be treated as equivalent.

Artifact distinctions to strictly enforce:

- Software Bill of Materials (SBOM): component-level decomposition of software capturing \
  internal modules, open-source libraries, transitive dependencies, versions, licenses, \
  and supply chain provenance. Defined by SPDX and CycloneDX standards. \
  → SBOM ≠ Software Inventory ≠ Application Asset Inventory.

- Software Inventory: list of licensed software titles installed on enterprise assets, \
  capturing product name, publisher, version, install date, and license count. \
  Device-centric, installed-software record. \
  → Software Inventory ≠ SBOM ≠ Application Asset Inventory.

- Application Asset Inventory: enterprise-level registry of application assets \
  (systems, platforms, services) capturing ownership, business purpose, classification, \
  and lifecycle status. Scoped to applications as portfolio assets, not endpoint installs. \
  → Application Asset Inventory ≠ Software Inventory. Do not map these to each other \
  even though both involve "software" or "applications."

- Asset Inventory: list of hardware and network-connected devices. \
  → Asset Inventory ≠ Software Inventory ≠ Application Asset Inventory ≠ SBOM. \
  Exception: a broad enterprise asset inventory explicitly including assets that store \
  or process data qualifies as a superset of Application Asset Inventory — map under \
  Rule 3 (subset reasoning) when it covers the application asset scope.

- Business Continuity Plan (BCP): an organizational document addressing how the enterprise \
  continues operations during emergencies, covering facility access, personnel roles, \
  communication procedures, data access, and recovery priorities across all functions. \
  → BCP ≠ Data Recovery Process. A data recovery process (e.g., CIS 11.1) is a technical \
  backup procedure. It may be a component a BCP references, but it does not constitute or \
  satisfy a BCP requirement. Do not map data recovery safeguards to BCP CCF controls.

- Business Continuity / Contingency Test: a cross-functional organizational exercise \
  testing the full BCP with relevant contingency teams, documented results, corrective \
  actions, and plan updates. Covers people, processes, communications, and systems. \
  → BCP Test ≠ Backup Recovery Test. CIS 11.5 (test backup recovery) covers only the \
  technical data restoration subset. It does NOT satisfy a CCF control requiring full \
  business contingency testing with teams, documentation, corrective actions, and plan \
  updates. Excluded under Rule 16 — partial subset below coverage threshold.

- Telecom Continuity Agreement: a service agreement with alternate telecommunication \
  providers establishing priority of service, failover provisions, and service resumption \
  guarantees for business continuity purposes. \
  → Telecom Continuity Agreement ≠ Security Requirements Contract. CIS 15.4 requires \
  contracts to include security requirements (encryption, incident notification, data \
  disposal). Priority of service and failover provisions are continuity clauses, not \
  security requirement clauses. Do not map 15.4 to telecom continuity CCF controls — \
  they address different contract content for entirely different purposes.

- Backup Failure Review: a periodic operational process of reviewing and resolving failed \
  backup jobs to maintain backup reliability and continuity. \
  → Safeguards that establish the backup process (CIS 11.1) or test backup recovery \
  (CIS 11.5) share the same backup maintenance lifecycle stage and directly support \
  backup failure review — map under Rules 6, 7, and 8.

- Pre-Installation Inspection: a security gate applied to hardware components before \
  installation in a production environment, verifying absence of unauthorized modifications. \
  → Pre-Installation Inspection is a pre-deployment lifecycle gate on network hardware. \
  A secure configuration process for network infrastructure (CIS 4.2) encompasses \
  pre-installation verification — map under Rule 8 (shared lifecycle stage: pre-deployment, \
  same asset type: network hardware/devices).

- Media Marking: the physical or logical act of applying security labels, handling \
  caveats, and distribution limitation markings directly onto information system media \
  (tapes, drives, USB devices, printouts, removable storage). \
  → Media Marking ≠ Data Classification Scheme. A classification scheme (e.g., CIS 3.7) \
  defines what labels mean — it does NOT apply them to physical media. CIS 3.7 is a \
  PREREQUISITE to media marking, not a coverage match. If no safeguard performs the \
  actual media marking action, the correct result is [].

- Data Classification Scheme: a taxonomy defining sensitivity label categories and their \
  meaning applied enterprise-wide to data categories. \
  → Classification Scheme ≠ Media Marking ≠ Data Inventory.

- Enforcement control: technical control that blocks, allows, or restricts execution \
  (allowlisting, firewalls, access control lists). \
  → Enforcement control ≠ inventory or documentation control, even on the same asset type.

- Configuration baseline: documented secure state for a system or software. \
  → Configuration baseline ≠ inventory ≠ SBOM.

Ask: "Does this safeguard produce or maintain the exact same type of security artifact \
as the CCF control requires — or a valid superset that explicitly includes that scope?"
</rule>

<rule id="15">
Rule 15 — Resolve Mechanism at the Correct Abstraction Level (CRITICAL)
When the CCF control names a specific technology or protocol as its mechanism \
(e.g., ARP scan, DHCP log, SNMP poll), identify the broader mechanism class that \
technology belongs to before evaluating safeguards. Match safeguards that implement \
the same mechanism class — not only those naming the exact technology.

Mechanism class hierarchy:
  ARP scan, network probe, nmap scan → active network discovery class
  Passive traffic capture, passive listener → passive network discovery class
  DHCP log, syslog, event log, audit log → log-based discovery class
  Vulnerability scanner → vulnerability assessment class
  Configuration check → configuration assessment class

Matching rule:
  Same mechanism class ✅ | Different mechanism class ❌

Example — CCF specifies "ARP scan" or "ARP table reconciliation":
  Resolve: ARP scan → active network discovery class
  Active discovery tool (CIS 1.3) ✅ same class
  Passive discovery tool (CIS 1.5) ✅ equivalent class (network discovery, passive variant)
  DHCP logging (CIS 1.4) ❌ different class (log-based, not scan-based)

Do NOT reject a safeguard solely because it does not name the exact protocol used. \
Do NOT over-specify mechanism matching to the point where no safeguard can match — \
this signals the abstraction level was set too narrowly.
</rule>

<rule id="16">
Rule 16 — Partial Subset Must Meet Minimum Coverage Threshold (CRITICAL)
When applying subset reasoning (Rule 3), a safeguard that covers only a minor or \
peripheral subset of the CCF control's required scope must be excluded under Rule 11 \
if the uncovered majority of the CCF control's requirements are left unaddressed.

Threshold test: "Does this safeguard satisfy the PRIMARY and DOMINANT requirement \
of the CCF control, or only a peripheral subset?"

Examples:
  CCF BC-04: full business contingency testing WITH cross-functional teams + \
  documentation + corrective actions + plan updates.
  CIS 11.5: technical backup recovery testing only.
  → 11.5 covers one narrow technical subset; the dominant requirements \
  (teams, documentation, corrective actions, plan updates) are entirely unaddressed. \
  FAILS threshold → exclude under Rules 11 and 16.

  CCF BM-02: annual backup restoration tests to confirm reliability and integrity.
  CIS 11.5: quarterly backup recovery testing.
  → 11.5 directly addresses the dominant and primary requirement. \
  PASSES threshold → include.

  CCF BM-05: alternate telecom agreements with priority of service provisions.
  CIS 15.4: service provider contracts with security requirements.
  → 15.4 addresses different contract content (security clauses vs continuity clauses). \
  Not a subset relationship at all — different artifact type entirely → exclude under \
  Rules 11 and 13.

Do NOT use PARTIAL mapping to include safeguards that address only a minor peripheral \
subset while leaving the primary requirement of the CCF control unmet.
</rule>

MAPPING RULES

<rule id="1">
Rule 1 — Identify the Core Security Action AND Mechanism
Before evaluating any safeguard, extract BOTH:
(a) the core required action(s) of the CCF control, AND
(b) the specific mechanism or data source the CCF control uses to perform that action,
    resolved to its mechanism class (see Rule 15).

Action examples:
  maintain inventory → asset inventory
  reconcile periodically → periodic review
  enforce access → access control
  monitor logs → logging/monitoring
  classify data → data classification
  scan network → network discovery
  address unmanaged assets → asset remediation
  test/validate/confirm → validation and testing
  protect integrity → integrity assurance
  mark media → media marking (physical/logical label application)
  inspect hardware before installation → pre-deployment security gate
  review and resolve failures → operational failure management
  test business continuity → organizational resilience exercise
  establish alternate service agreements → continuity contract management

Mechanism class examples:
  "reconcile log repository against inventory" → log-based discovery class
  "ARP scan / ARP table / network discovery scan" → active network discovery class
  "DHCP logging" → log-based discovery class
  "passive discovery tool" → passive network discovery class
  "automated backups" → backup tooling class
  "mark physical media" → physical handling procedure
  "inspect hardware prior to installation" → pre-deployment inspection gate
  "test backup restoration" → backup recovery testing class
  "test business continuity with teams" → organizational continuity exercise class

Always extract both action and mechanism class before comparing any safeguard.
</rule>

<rule id="2">
Rule 2 — Evaluate Each Safeguard Independently
Read only the safeguard's own description and action. Completely ignore its parent control \
family or domain. Never let the domain label override what the safeguard actually requires.
</rule>

<rule id="3">
Rule 3 — Apply Subset Reasoning (CRITICAL)
If the internal control references a broad category, any safeguard addressing a specific \
sub-type of that category is a valid mapping candidate.
Example hierarchy: information systems → servers, applications, network devices, \
authentication systems, authorization systems, software assets.
Never exclude a safeguard solely because it applies to a specialized subset of scope.
NOTE: Subset reasoning is subject to Rule 16 — the subset must meet the minimum \
coverage threshold. A minor peripheral subset that leaves the primary requirement \
unmet is excluded under Rules 11 and 16.
</rule>

<rule id="4">
Rule 4 — Match on Mechanism Class, Not Exact Technology (CRITICAL)
Only map safeguards that use the same or equivalent mechanism CLASS as the CCF control. \
Do not require exact technology or protocol name match.

Mechanism class examples:
  ARP scan, active discovery tool, network probe → active network discovery class
  Passive traffic capture, passive discovery tool → passive network discovery class
  DHCP log, syslog, event log → log-based discovery class
  These classes are distinct — do not cross-map between classes.

Example — CCF specifies "ARP scan" or "network discovery scan":
  Active discovery tool ✅ same class | Passive discovery tool ✅ equivalent class
  DHCP logging ❌ different class (log-based, not scan-based)

Do NOT map safeguards achieving similar outcomes through fundamentally different mechanism classes.
</rule>

<rule id="5">
Rule 5 — Evaluate Safeguard Intent, Not Just Its Examples (CRITICAL)
Evaluate the safeguard's broader security intent, not just its listed example actions.
Example: "address unauthorized assets — remove, quarantine, or deny access" →
  Broader intent: ensure unmanaged assets do not go unaddressed.
  CCF "assign owner to non-inventoried device" → ownership assignment satisfies this intent ✅

CAUTION — Rule 5 is bidirectional:
  Do not over-restrict to listed examples only. \
  Do not over-extend to force matches between genuinely different actions. \
  Do not match on shared surface keywords (e.g., "both involve service provider contracts", \
  "both involve backups") — the security action and artifact content must align.
</rule>

<rule id="6">
Rule 6 — Apply Foundational Dependency Reasoning (CRITICAL)
If the CCF control tests, validates, or confirms a capability, safeguards that establish \
or maintain that underlying capability are valid mapping candidates.
Example: CCF "perform backup restoration tests" →
  Test data recovery ✅ | Establish data recovery process ✅ | Perform automated backups ❌

IMPORTANT: Rule 6 does NOT override Rule 9. However, when the CCF control directly \
tests or validates what a safeguard establishes, that safeguard provides COVERAGE \
(not merely a prerequisite) because the test confirms the established capability. \
Example: BM-02 tests backup restoration → 11.1 establishes the data recovery process \
being tested → 11.1 provides COVERAGE under Rule 6, not merely a prerequisite.

Ask: "Is this safeguard establishing the specific capability the CCF control tests or confirms?"
</rule>

<rule id="7">
Rule 7 — Apply Objective Linking (CRITICAL)
If a safeguard's outcome directly enables, supports, or is confirmed by the CCF control's \
objective, they are meaningfully linked.
Example: CCF "confirm integrity of backups" →
  Protect recovery data ✅ | Encrypt data at rest ❌

IMPORTANT: Rule 7 does NOT override Rule 9. But when a safeguard's outcome is \
directly validated by the CCF control's test or confirmation, it provides COVERAGE. \
Example: BM-02 confirms integrity of backups → 11.3 protects recovery data integrity \
→ 11.3 provides COVERAGE under Rule 7 because BM-02 validates what 11.3 ensures.

Ask: "Does this safeguard's outcome get directly confirmed or validated by the CCF control?"
</rule>

<rule id="8">
Rule 8 — Apply Shared Lifecycle Stage Reasoning (CRITICAL)
If both the CCF control and the safeguard apply a security check at the same lifecycle \
stage on the same asset type, they share the same security gate objective.
Lifecycle stages: Pre-installation/Pre-deployment, During operation, Maintenance, Decommission.

Examples:
  CCF "inspect hardware prior to installation in production network" →
    Secure configuration process for network devices (CIS 4.2) ✅ — same lifecycle \
    stage (pre-installation), same asset type (network hardware/devices), same gate \
    objective (ensure only secure, verified components enter the production network).

Ask: "Does this safeguard apply a security check at the same lifecycle stage and asset type?"
</rule>

<rule id="10">
Rule 10 — Focus on Primary Required Action
For each safeguard ask:
1. What is the safeguard's broader security intent beyond its listed examples?
2. Does the internal control implement or satisfy that intent?
3. Is the safeguard scoped to a subset of what the internal control covers?
4. Does the mechanism class match what the internal control specifies?
5. Is this safeguard foundational to what the CCF control tests or confirms?
6. Does this safeguard's outcome get directly validated by the CCF control?
7. Do both apply a security check at the same lifecycle stage on the same asset type?
8. Does this safeguard provide coverage or is it merely a prerequisite?
9. Does this safeguard meet the minimum coverage threshold (Rule 16)?

If (2) or (3) is yes AND (4) is satisfied AND (9) passes → include it.
If (5) or (6) is yes AND (8) confirms coverage AND (9) passes → include it.
If (7) is yes AND (9) passes → include it.
Only include if (8) confirms coverage and (9) confirms threshold met.
</rule>

<rule id="11">
Rule 11 — Exclude Weak or Tangential Mappings
Do NOT map a safeguard when:
- It addresses a fundamentally different security function
- It only partially overlaps with the internal control's objective
- It requires additional controls not implied by the internal control
- It uses a different mechanism class than what the internal control specifies
- It is a prerequisite rather than a coverage match
- The relationship is coincidental rather than purposeful
- It matches only on shared surface keywords (e.g., "both involve contracts", \
  "both involve backups") without matching on action, artifact, or mechanism
- It covers only a minor peripheral subset below the coverage threshold (Rule 16)
</rule>

<rule id="12">
Rule 12 — Prefer High-Confidence Mappings
Only include safeguards where the internal control directly and meaningfully satisfies \
the safeguard's main requirement. Fewer strong mappings are better than many weak ones. \
Zero mappings is acceptable only after all rules and the empty-result gate have been applied.
</rule>

<rule id="14">
Rule 14 — Exhaustively Apply Subset Reasoning Across All Safeguards Before Concluding (CRITICAL)
Step 1 — Derive the full asset/artifact subset hierarchy from the CCF control.
Step 2 — For every safeguard, ask independently: \
  "Does this safeguard's required action apply to any member of this subset hierarchy?"
  If yes → evaluate for mapping. If no → exclude.
Step 3 — Do NOT stop scanning after finding one strong match. Continue evaluating ALL safeguards.
Step 4 — Pay special attention to safeguards in non-obvious parent domains \
  (Access Control, Secure Configuration, etc.) acting on asset types within the hierarchy.

Failure mode to avoid: terminating the scan early after finding the first match.
For backup-related CCF controls specifically: always evaluate ALL of 11.1, 11.2, 11.3, \
11.4, and 11.5 independently before concluding.
</rule>

REASONING REQUIREMENT
Before producing the final JSON array, internally reason through each safeguard using \
the mandatory evaluation checklist. Apply every checklist item explicitly. Do not skip \
safeguards. Do not produce the JSON array until all safeguards have been evaluated.

MANDATORY EVALUATION CHECKLIST
Apply this checklist to every candidate safeguard before finalizing:
 1. What is the safeguard's primary required action and broader intent?
 2. Does the internal control directly perform that action or satisfy that intent?
 3. Is the safeguard addressing a subset or specialization of the internal control's scope?
 4. Am I being influenced by the safeguard's parent domain rather than its own content?
 5. Am I evaluating the safeguard's intent or just its listed examples?
 6. Does the mechanism CLASS match? Have I resolved the CCF control's named technology \
    to its broader mechanism class first (Rule 15)?
 7. Is this safeguard foundational to the capability the CCF control tests or confirms? \
    If yes — does the CCF control directly validate what this safeguard establishes? \
    (If yes → COVERAGE under Rule 6, not prerequisite.)
 8. Does this safeguard's outcome get directly confirmed or validated by the CCF control? \
    (If yes → COVERAGE under Rule 7.)
 9. Do both apply a security check at the same lifecycle stage on the same asset type?
10. Is this safeguard providing coverage or merely a prerequisite? \
    Rules 6 and 7 do NOT override Rule 9 EXCEPT when the CCF control directly tests \
    or validates what the safeguard establishes or protects.
11. Would excluding this safeguard leave a meaningful coverage gap?
12. Do both the CCF control and the safeguard produce or maintain the same precise \
    security artifact type? If not, do not map (Rule 13). \
    Watch for: BCP ≠ Data Recovery Process, Telecom Agreement ≠ Security Contract, \
    BCP Test ≠ Backup Recovery Test.
13. Have I evaluated ALL safeguards across ALL control families? Have I derived the \
    full subset hierarchy and checked every safeguard against every member of it? \
    For backup CCF controls: have I evaluated 11.1, 11.2, 11.3, 11.4, and 11.5 individually?
14. Does this safeguard meet the minimum coverage threshold (Rule 16)? \
    Does it address the PRIMARY and DOMINANT requirement, or only a minor peripheral subset?

SCAN COMPLETION GATE
Before returning your answer, confirm ALL of the following:
- Total safeguards evaluated equals total safeguards in the input — none skipped.
- Scanning did not stop after finding the first match.
- Safeguards from every control family were checked.
- Both the action AND mechanism class were extracted and resolved before evaluating.
- Rule 5 was applied bidirectionally — no surface keyword matching.
- Rules 6 and 7 were NOT used to override Rule 9, EXCEPT where the CCF control \
  directly tests or validates what the safeguard establishes or protects.
- Rule 16 threshold was applied — no peripheral subsets included.
- Artifact types were verified under Rule 13 — BCP ≠ Data Recovery, \
  Telecom Agreement ≠ Security Contract, BCP Test ≠ Backup Recovery Test.
- Output contains ONLY safeguards that passed all 16 rules and all 14 checklist items.

EMPTY RESULT GATE (CRITICAL)
If your result is [], perform these checks before returning:
1. Were mechanism classes (Rules 4 and 15) applied at the correct abstraction level?
2. Was Rule 5 applied too narrowly?
3. Were safeguards incorrectly classified as prerequisites under Rule 9 when they \
   provide direct coverage — especially for CCF controls that test or validate a capability?
4. Were Rule 8 shared lifecycle stage matches checked — especially for pre-deployment \
   or maintenance stage CCF controls?
5. Was Rule 9 correctly applied — were prerequisites incorrectly promoted via Rules 6 or 7?

An empty result is valid ONLY after all five checks pass.

OUTPUT FORMAT (STRICT)
Return ONLY a raw JSON array — no markdown fences, no explanation, no extra text.
For each safeguard with a meaningful mapping, include an entry with exactly these fields:
  "safeguard_id": string,
  "mapping": "FULL" or "PARTIAL",
  "reason": string (one concise sentence explaining the compliance relationship)

Use FULL when the safeguard completely satisfies the internal control's security objective.
Use PARTIAL when the safeguard meaningfully addresses it but does not fully cover it.
Omit safeguards with no meaningful relationship — do NOT include NO entries.
An empty array [] is valid only after the EMPTY RESULT GATE has been passed.

POSITIVE EXAMPLES:
[{"safeguard_id": "11.5", "mapping": "FULL", "reason": "Test Data Recovery directly performs backup restoration testing, satisfying BM-02's objective to confirm backup reliability and integrity."},
 {"safeguard_id": "11.1", "mapping": "PARTIAL", "reason": "Establishing the data recovery process is the foundational capability that BM-02's restoration test directly validates — coverage under Rule 6."},
 {"safeguard_id": "11.3", "mapping": "PARTIAL", "reason": "Protecting recovery data ensures the integrity that BM-02 confirms — coverage under Rule 7 as BM-02 directly validates what 11.3 protects."},
 {"safeguard_id": "4.2", "mapping": "PARTIAL", "reason": "A secure configuration process for network devices encompasses pre-installation inspection gates, sharing the same pre-deployment lifecycle stage and asset type as AM-12."}]

NEGATIVE EXAMPLES (do NOT produce entries like these):

[{"safeguard_id": "11.1", "mapping": "PARTIAL", "reason": "11.1 establishes data recovery which supports the BCP data access objective."}]
← WRONG: BCP ≠ Data Recovery Process (Rule 13). 11.1 is a technical backup procedure; \
BC-02 requires an organizational Business Continuity Plan covering facility access, \
personnel, communications, and data. Different artifact types — do not map.

[{"safeguard_id": "11.5", "mapping": "PARTIAL", "reason": "11.5 covers the disaster recovery subset of BC-04's contingency testing requirement."}]
← WRONG: BC-04 requires full business contingency testing with cross-functional teams, \
documentation, corrective actions, and plan updates. 11.5 covers only technical backup \
recovery testing — a minor subset leaving the dominant requirements entirely unmet. \
Excluded under Rule 16 (below coverage threshold) and Rule 11.

[{"safeguard_id": "15.4", "mapping": "PARTIAL", "reason": "15.4 covers service provider contracts which supports telecom continuity agreements."}]
← WRONG: Telecom Continuity Agreement ≠ Security Requirements Contract (Rule 13). \
15.4 addresses security clauses (encryption, breach notification, disposal). BM-05 \
requires continuity clauses (priority of service, failover provisions). Different \
contract content and purpose — Rule 11 exclusion. Do not match on "both involve \
service provider contracts."

[{"safeguard_id": "3.7", "mapping": "PARTIAL", "reason": "CIS 3.7 classifies data using labels which supports media marking."}]
← WRONG: Classification scheme ≠ Media Marking (Rule 13). 3.7 is a PREREQUISITE \
to marking, not a coverage match. Rule 9 excludes prerequisites.

[empty array for a backup-related CCF control without evaluating 11.1, 11.3, 11.5]
← WRONG: For any backup-related CCF control, always individually evaluate 11.1, 11.2, \
11.3, 11.4, and 11.5 under Rules 6, 7, and 8 before concluding.\
"""


USER_PROMPT = """
USER PROMPT:
 INTERNAL CONTROL (CCF):
  CCF ID: 
  Control Domain: 
  Control Name: 
  Control Description: 

EXTERNAL FRAMEWORK SAFEGUARDS:
[
  {
    "safeguard_id": "1.1",
    "safeguard_title": "Establish and Maintain Detailed Enterprise Asset Inventory",
    "safeguard_description": "Establish and maintain an accurate, detailed, and up-to-date inventory of all enterprise assets with the potential to store or process data, to include: end-user devices (including portable and mobile), network devices, non-computing/IoT devices, and servers. Ensure the inventory records the network address (if static), hardware address, machine name, enterprise asset owner, department for each asset, and whether the asset has been approved to connect to the network. For mobile end-user devices, MDM type tools can support this process, where appropriate. This inventory includes assets connected to the infrastructure physically, virtually, remotely, and those within cloud environments. Additionally, it includes assets that are regularly connected to the enterprise's network infrastructure, even if they are not under control of the enterprise. Review and update the inventory of all enterprise assets bi-annually, or more frequently."
  },
  {
    "safeguard_id": "1.2",
    "safeguard_title": "Address Unauthorized Assets",
    "safeguard_description": "Ensure that a process exists to address unauthorized assets on a weekly basis. The enterprise may choose to remove the asset from the network, deny the asset from connecting remotely to the network, or quarantine the asset."
  },
  {
    "safeguard_id": "1.3",
    "safeguard_title": "Utilize an Active Discovery Tool",
    "safeguard_description": "Utilize an active discovery tool to identify assets connected to the enterprise's network. Configure the active discovery tool to execute daily, or more frequently."
  },
  {
    "safeguard_id": "1.4",
    "safeguard_title": "Use Dynamic Host Configuration Protocol (DHCP) Logging to Update Enterprise Asset Inventory",
    "safeguard_description": "Use DHCP logging on all DHCP servers or Internet Protocol (IP) address management tools to update the enterprise's asset inventory. Review and use logs to update the enterprise's asset inventory weekly, or more frequently."
  },
  {
    "safeguard_id": "1.5",
    "safeguard_title": "Use a Passive Asset Discovery Tool",
    "safeguard_description": "Use a passive discovery tool to identify assets connected to the enterprise's network. Review and use scans to update the enterprise's asset inventory at least weekly, or more frequently."
  },
  {
    "safeguard_id": "2.1",
    "safeguard_title": "Establish and Maintain a Software Inventory",
    "safeguard_description": "Establish and maintain a detailed inventory of all licensed software installed on enterprise assets. The software inventory must document the title, publisher, initial install/use date, and business purpose for each entry; where appropriate, include the Uniform Resource Locator (URL), app store(s), version(s), deployment mechanism, decommission date, and number of licenses. Review and update the software inventory bi-annually, or more frequently."
  },
  {
    "safeguard_id": "2.2",
    "safeguard_title": "Ensure Authorized Software is Currently Supported",
    "safeguard_description": "Ensure that only currently supported software is designated as authorized in the software inventory for enterprise assets. If software is unsupported, yet necessary for the fulfillment of the enterprise's mission, document an exception detailing mitigating controls and residual risk acceptance. For any unsupported software without an exception documentation, designate as unauthorized. Review the software list to verify software support at least monthly, or more frequently."
  },
  {
    "safeguard_id": "2.3",
    "safeguard_title": "Address Unauthorized Software",
    "safeguard_description": "Ensure that unauthorized software is either removed from use on enterprise assets or receives a documented exception. Review monthly, or more frequently."
  },
  {
    "safeguard_id": "2.4",
    "safeguard_title": "Utilize Automated Software Inventory Tools",
    "safeguard_description": "Utilize software inventory tools, when possible, throughout the enterprise to automate the discovery and documentation of installed software."
  },
  {
    "safeguard_id": "2.5",
    "safeguard_title": "Allowlist Authorized Software",
    "safeguard_description": "Use technical controls, such as application allowlisting, to ensure that only authorized software can execute or be accessed. Reassess bi-annually, or more frequently."
  },
  {
    "safeguard_id": "2.6",
    "safeguard_title": "Allowlist Authorized Libraries",
    "safeguard_description": "Use technical controls to ensure that only authorized software libraries, such as specific .dll, .ocx, and .so files, are allowed to load into a system process. Block unauthorized libraries from loading into a system process. Reassess bi-annually, or more frequently."
  },
  {
    "safeguard_id": "2.7",
    "safeguard_title": "Allowlist Authorized Scripts",
    "safeguard_description": "Use technical controls, such as digital signatures and version control, to ensure that only authorized scripts, such as specific .ps1, and .py files are allowed to execute. Block unauthorized scripts from executing. Reassess bi-annually, or more frequently."
  },
  {
    "safeguard_id": "3.1",
    "safeguard_title": "Establish and Maintain a Data Management Process",
    "safeguard_description": "Establish and maintain a documented data management process. In the process, address data sensitivity, data owner, handling of data, data retention limits, and disposal requirements, based on sensitivity and retention standards for the enterprise. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "3.2",
    "safeguard_title": "Establish and Maintain a Data Inventory",
    "safeguard_description": "Establish and maintain a data inventory based on the enterprise's data management process. Inventory sensitive data, at a minimum. Review and update inventory annually, at a minimum, with a priority on sensitive data."
  },
  {
    "safeguard_id": "3.3",
    "safeguard_title": "Configure Data Access Control Lists",
    "safeguard_description": "Configure data access control lists based on a user's need to know. Apply data access control lists, also known as access permissions, to local and remote file systems, databases, and applications."
  },
  {
    "safeguard_id": "3.4",
    "safeguard_title": "Enforce Data Retention",
    "safeguard_description": "Retain data according to the enterprise's documented data management process. Data retention must include both minimum and maximum timelines."
  },
  {
    "safeguard_id": "3.5",
    "safeguard_title": "Securely Dispose of Data",
    "safeguard_description": "Securely dispose of data as outlined in the enterprise's documented data management process. Ensure the disposal process and method are commensurate with the data sensitivity."
  },
  {
    "safeguard_id": "3.6",
    "safeguard_title": "Encrypt Data on End-User Devices",
    "safeguard_description": "Encrypt data on end-user devices containing sensitive data. Example implementations can include: Windows BitLocker\u00ae, Apple FileVault\u00ae, Linux\u00ae dm-crypt."
  },
  {
    "safeguard_id": "3.7",
    "safeguard_title": "Establish and Maintain a Data Classification Scheme",
    "safeguard_description": "Establish and maintain an overall data classification scheme for the enterprise. Enterprises may use labels, such as \"Sensitive,\" \"Confidential,\" and \"Public,\" and classify their data according to those labels. Review and update the classification scheme annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "3.8",
    "safeguard_title": "Document Data Flows",
    "safeguard_description": "Document data flows. Data flow documentation includes service provider data flows and should be based on the enterprise's data management process. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "3.9",
    "safeguard_title": "Encrypt Data on Removable Media",
    "safeguard_description": "Encrypt data on removable media."
  },
  {
    "safeguard_id": "3.10",
    "safeguard_title": "Encrypt Sensitive Data in Transit",
    "safeguard_description": "Encrypt sensitive data in transit. Example implementations can include: Transport Layer Security (TLS) and Open Secure Shell (OpenSSH)."
  },
  {
    "safeguard_id": "3.11",
    "safeguard_title": "Encrypt Sensitive Data at Rest",
    "safeguard_description": "Encrypt sensitive data at rest on servers, applications, and databases. Storage-layer encryption, also known as server-side encryption, meets the minimum requirement of this Safeguard. Additional encryption methods may include application-layer encryption, also known as client-side encryption, where access to the data storage device(s) does not permit access to the plain-text data."
  },
  {
    "safeguard_id": "3.12",
    "safeguard_title": "Segment Data Processing and Storage Based on Sensitivity",
    "safeguard_description": "Segment data processing and storage based on the sensitivity of the data. Do not process sensitive data on enterprise assets intended for lower sensitivity data."
  },
  {
    "safeguard_id": "3.13",
    "safeguard_title": "Deploy a Data Loss Prevention Solution",
    "safeguard_description": "Implement an automated tool, such as a host-based Data Loss Prevention (DLP) tool to identify all sensitive data stored, processed, or transmitted through enterprise assets, including those located onsite or at a remote service provider, and update the enterprise's data inventory."
  },
  {
    "safeguard_id": "3.14",
    "safeguard_title": "Log Sensitive Data Access",
    "safeguard_description": "Log sensitive data access, including modification and disposal."
  },
  {
    "safeguard_id": "4.1",
    "safeguard_title": "Establish and Maintain a Secure Configuration Process",
    "safeguard_description": "Establish and maintain a documented secure configuration process for enterprise assets (end-user devices, including portable and mobile, non-computing/IoT devices, and servers) and software (operating systems and applications). Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "4.2",
    "safeguard_title": "Establish and Maintain a Secure Configuration Process for Network Infrastructure",
    "safeguard_description": "Establish and maintain a documented secure configuration process for network devices. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "4.3",
    "safeguard_title": "Configure Automatic Session Locking on Enterprise Assets",
    "safeguard_description": "Configure automatic session locking on enterprise assets after a defined period of inactivity. For general purpose operating systems, the period must not exceed 15 minutes. For mobile end-user devices, the period must not exceed 2 minutes."
  },
  {
    "safeguard_id": "4.4",
    "safeguard_title": "Implement and Manage a Firewall on Servers",
    "safeguard_description": "Implement and manage a firewall on servers, where supported. Example implementations include a virtual firewall, operating system firewall, or a third-party firewall agent."
  },
  {
    "safeguard_id": "4.5",
    "safeguard_title": "Implement and Manage a Firewall on End-User Devices",
    "safeguard_description": "Implement and manage a host-based firewall or port-filtering tool on end-user devices, with a default-deny rule that drops all traffic except those services and ports that are explicitly allowed."
  },
  {
    "safeguard_id": "4.6",
    "safeguard_title": "Securely Manage Enterprise Assets and Software",
    "safeguard_description": "Securely manage enterprise assets and software. Example implementations include managing configuration through version-controlled Infrastructure-as-Code (IaC) and accessing administrative interfaces over secure network protocols, such as Secure Shell (SSH) and Hypertext Transfer Protocol Secure (HTTPS). Do not use insecure management protocols, such as Telnet (Teletype Network) and HTTP, unless operationally essential."
  },
  {
    "safeguard_id": "4.7",
    "safeguard_title": "Manage Default Accounts on Enterprise Assets and Software",
    "safeguard_description": "Manage default accounts on enterprise assets and software, such as root, administrator, and other pre-configured vendor accounts. Example implementations can include: disabling default accounts or making them unusable."
  },
  {
    "safeguard_id": "4.8",
    "safeguard_title": "Uninstall or Disable Unnecessary Services on Enterprise Assets and Software",
    "safeguard_description": "Uninstall or disable unnecessary services on enterprise assets and software, such as an unused file sharing service, web application module, or service function."
  },
  {
    "safeguard_id": "4.9",
    "safeguard_title": "Configure Trusted DNS Servers on Enterprise Assets",
    "safeguard_description": "Configure trusted DNS servers on network infrastructure. Example implementations include configuring network devices to use enterprise-controlled DNS servers and/or reputable externally accessible DNS servers."
  },
  {
    "safeguard_id": "4.10",
    "safeguard_title": "Enforce Automatic Device Lockout on Portable End-User Devices",
    "safeguard_description": "Enforce automatic device lockout following a predetermined threshold of local failed authentication attempts on portable end-user devices, where supported. For laptops, do not allow more than 20 failed authentication attempts; for tablets and smartphones, no more than 10 failed authentication attempts. Example implementations include Microsoft\u00ae InTune Device Lock and Apple\u00ae Configuration Profile maxFailedAttempts."
  },
  {
    "safeguard_id": "4.11",
    "safeguard_title": "Enforce Remote Wipe Capability on Portable End-User Devices",
    "safeguard_description": "Remotely wipe enterprise data from enterprise-owned portable end-user devices when deemed appropriate such as lost or stolen devices, or when an individual no longer supports the enterprise."
  },
  {
    "safeguard_id": "4.12",
    "safeguard_title": "Separate Enterprise Workspaces on Mobile End-User Devices",
    "safeguard_description": "Ensure separate enterprise workspaces are used on mobile end-user devices, where supported. Example implementations include using an Apple\u00ae Configuration Profile or Android\u2122 Work Profile to separate enterprise applications and data from personal applications and data."
  },
  {
    "safeguard_id": "5.1",
    "safeguard_title": "Establish and Maintain an Inventory of Accounts",
    "safeguard_description": "Establish and maintain an inventory of all accounts managed in the enterprise. The inventory must at a minimum include user, administrator, and service accounts. The inventory, at a minimum, should contain the person's name, username, start/stop dates, and department. Validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently."
  },
  {
    "safeguard_id": "5.2",
    "safeguard_title": "Use Unique Passwords",
    "safeguard_description": "Use unique passwords for all enterprise assets. Best practice implementation includes, at a minimum, an 8-character password for accounts using Multi-Factor Authentication (MFA) and a 14-character password for accounts not using MFA."
  },
  {
    "safeguard_id": "5.3",
    "safeguard_title": "Disable Dormant Accounts",
    "safeguard_description": "Delete or disable any dormant accounts after a period of 45 days of inactivity, where supported."
  },
  {
    "safeguard_id": "5.4",
    "safeguard_title": "Restrict Administrator Privileges to Dedicated Administrator Accounts",
    "safeguard_description": "Restrict administrator privileges to dedicated administrator accounts on enterprise assets. Conduct general computing activities, such as internet browsing, email, and productivity suite use, from the user's primary, non-privileged account."
  },
  {
    "safeguard_id": "5.5",
    "safeguard_title": "Establish and Maintain an Inventory of Service Accounts",
    "safeguard_description": "Establish and maintain an inventory of service accounts. The inventory, at a minimum, must contain department owner, review date, and purpose. Perform service account reviews to validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently."
  },
  {
    "safeguard_id": "5.6",
    "safeguard_title": "Centralize Account Management",
    "safeguard_description": "Centralize account management through a directory or identity service."
  },
  {
    "safeguard_id": "6.1",
    "safeguard_title": "Establish an Access Granting Process",
    "safeguard_description": "Establish and follow a documented process, preferably automated, for granting access to enterprise assets upon new hire or role change of a user."
  },
  {
    "safeguard_id": "6.2",
    "safeguard_title": "Establish an Access Revoking Process",
    "safeguard_description": "Establish and follow a process, preferably automated, for revoking access to enterprise assets, through disabling accounts immediately upon termination, rights revocation, or role change of a user. Disabling accounts, instead of deleting accounts, may be necessary to preserve audit trails."
  },
  {
    "safeguard_id": "6.3",
    "safeguard_title": "Require MFA for Externally-Exposed Applications",
    "safeguard_description": "Require all externally-exposed enterprise or third-party applications to enforce MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard."
  },
  {
    "safeguard_id": "6.4",
    "safeguard_title": "Require MFA for Remote Network Access",
    "safeguard_description": "Require MFA for remote network access."
  },
  {
    "safeguard_id": "6.5",
    "safeguard_title": "Require MFA for Administrative Access",
    "safeguard_description": "Require MFA for all administrative access accounts, where supported, on all enterprise assets, whether managed on-site or through a service provider."
  },
  {
    "safeguard_id": "6.6",
    "safeguard_title": "Establish and Maintain an Inventory of Authentication and Authorization Systems",
    "safeguard_description": "Establish and maintain an inventory of the enterprise's authentication and authorization systems, including those hosted on-site or at a remote service provider. Review and update the inventory, at a minimum, annually, or more frequently."
  },
  {
    "safeguard_id": "6.7",
    "safeguard_title": "Centralize Access Control",
    "safeguard_description": "Centralize access control for all enterprise assets through a directory service or SSO provider, where supported."
  },
  {
    "safeguard_id": "6.8",
    "safeguard_title": "Define and Maintain Role-Based Access Control",
    "safeguard_description": "Define and maintain role-based access control, through determining and documenting the access rights necessary for each role within the enterprise to successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently."
  },
  {
    "safeguard_id": "7.1",
    "safeguard_title": "Establish and Maintain a Vulnerability Management Process",
    "safeguard_description": "Establish and maintain a documented vulnerability management process for enterprise assets. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "7.2",
    "safeguard_title": "Establish and Maintain a Remediation Process",
    "safeguard_description": "Establish and maintain a risk-based remediation strategy documented in a remediation process, with monthly, or more frequent, reviews."
  },
  {
    "safeguard_id": "7.3",
    "safeguard_title": "Perform Automated Operating System Patch Management",
    "safeguard_description": "Perform operating system updates on enterprise assets through automated patch management on a monthly, or more frequent, basis."
  },
  {
    "safeguard_id": "7.4",
    "safeguard_title": "Perform Automated Application Patch Management",
    "safeguard_description": "Perform application updates on enterprise assets through automated patch management on a monthly, or more frequent, basis."
  },
  {
    "safeguard_id": "7.5",
    "safeguard_title": "Perform Automated Vulnerability Scans of Internal Enterprise Assets",
    "safeguard_description": "Perform automated vulnerability scans of internal enterprise assets on a quarterly, or more frequent, basis. Conduct both authenticated and unauthenticated scans."
  },
  {
    "safeguard_id": "7.6",
    "safeguard_title": "Perform Automated Vulnerability Scans of Externally-Exposed Enterprise Assets",
    "safeguard_description": "Perform automated vulnerability scans of externally-exposed enterprise assets. Perform scans on a monthly, or more frequent, basis."
  },
  {
    "safeguard_id": "7.7",
    "safeguard_title": "Remediate Detected Vulnerabilities",
    "safeguard_description": "Remediate detected vulnerabilities in software through processes and tooling on a monthly, or more frequent, basis, based on the remediation process."
  },
  {
    "safeguard_id": "8.1",
    "safeguard_title": "Establish and Maintain an Audit Log Management Process",
    "safeguard_description": "Establish and maintain a documented audit log management process that defines the enterprise's logging requirements. At a minimum, address the collection, review, and retention of audit logs for enterprise assets. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "8.2",
    "safeguard_title": "Collect Audit Logs",
    "safeguard_description": "Collect audit logs. Ensure that logging, per the enterprise's audit log management process, has been enabled across enterprise assets."
  },
  {
    "safeguard_id": "8.3",
    "safeguard_title": "Ensure Adequate Audit Log Storage",
    "safeguard_description": "Ensure that logging destinations maintain adequate storage to comply with the enterprise's audit log management process."
  },
  {
    "safeguard_id": "8.4",
    "safeguard_title": "Standardize Time Synchronization",
    "safeguard_description": "Standardize time synchronization. Configure at least two synchronized time sources across enterprise assets, where supported."
  },
  {
    "safeguard_id": "8.5",
    "safeguard_title": "Collect Detailed Audit Logs",
    "safeguard_description": "Configure detailed audit logging for enterprise assets containing sensitive data. Include event source, date, username, timestamp, source addresses, destination addresses, and other useful elements that could assist in a forensic investigation."
  },
  {
    "safeguard_id": "8.6",
    "safeguard_title": "Collect DNS Query Audit Logs",
    "safeguard_description": "Collect DNS query audit logs on enterprise assets, where appropriate and supported."
  },
  {
    "safeguard_id": "8.7",
    "safeguard_title": "Collect URL Request Audit Logs",
    "safeguard_description": "Collect URL request audit logs on enterprise assets, where appropriate and supported."
  },
  {
    "safeguard_id": "8.8",
    "safeguard_title": "Collect Command-Line Audit Logs",
    "safeguard_description": "Collect command-line audit logs. Example implementations include collecting audit logs from PowerShell\u00ae, BASH\u2122, and remote administrative terminals."
  },
  {
    "safeguard_id": "8.9",
    "safeguard_title": "Centralize Audit Logs",
    "safeguard_description": "Centralize, to the extent possible, audit log collection and retention across enterprise assets in accordance with the documented audit log management process. Example implementations primarily include leveraging a SIEM tool to centralize multiple log sources."
  },
  {
    "safeguard_id": "8.10",
    "safeguard_title": "Retain Audit Logs",
    "safeguard_description": "Retain audit logs across enterprise assets for a minimum of 90 days."
  },
  {
    "safeguard_id": "8.11",
    "safeguard_title": "Conduct Audit Log Reviews",
    "safeguard_description": "Conduct reviews of audit logs to detect anomalies or abnormal events that could indicate a potential threat. Conduct reviews on a weekly, or more frequent, basis."
  },
  {
    "safeguard_id": "8.12",
    "safeguard_title": "Collect Service Provider Logs",
    "safeguard_description": "Collect service provider logs, where supported. Example implementations include collecting authentication and authorization events, data creation and disposal events, and user management events."
  },
  {
    "safeguard_id": "9.1",
    "safeguard_title": "Ensure Use of Only Fully Supported Browsers and Email Clients",
    "safeguard_description": "Ensure only fully supported browsers and email clients are allowed to execute in the enterprise, only using the latest version of browsers and email clients provided through the vendor."
  },
  {
    "safeguard_id": "9.2",
    "safeguard_title": "Use DNS Filtering Services",
    "safeguard_description": "Use DNS filtering services on all end-user devices, including remote and on-premises assets, to block access to known malicious domains."
  },
  {
    "safeguard_id": "9.3",
    "safeguard_title": "Maintain and Enforce Network-Based URL Filters",
    "safeguard_description": "Enforce and update network-based URL filters to limit an enterprise asset from connecting to potentially malicious or unapproved websites. Example implementations include category-based filtering, reputation-based filtering, or through the use of block lists. Enforce filters for all enterprise assets."
  },
  {
    "safeguard_id": "9.4",
    "safeguard_title": "Restrict Unnecessary or Unauthorized Browser and Email Client Extensions",
    "safeguard_description": "Restrict, either through uninstalling or disabling, any unauthorized or unnecessary browser or email client plugins, extensions, and add-on applications."
  },
  {
    "safeguard_id": "9.5",
    "safeguard_title": "Implement DMARC",
    "safeguard_description": "To lower the chance of spoofed or modified emails from valid domains, implement DMARC policy and verification, starting with implementing the Sender Policy Framework (SPF) and the DomainKeys Identified Mail (DKIM) standards."
  },
  {
    "safeguard_id": "9.6",
    "safeguard_title": "Block Unnecessary File Types",
    "safeguard_description": "Block unnecessary file types attempting to enter the enterprise's email gateway."
  },
  {
    "safeguard_id": "9.7",
    "safeguard_title": "Deploy and Maintain Email Server Anti-Malware Protections",
    "safeguard_description": "Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing."
  },
  {
    "safeguard_id": "10.1",
    "safeguard_title": "Deploy and Maintain Anti-Malware Software",
    "safeguard_description": "Deploy and maintain anti-malware software on all enterprise assets."
  },
  {
    "safeguard_id": "10.2",
    "safeguard_title": "Configure Automatic Anti-Malware Signature Updates",
    "safeguard_description": "Configure automatic updates for anti-malware signature files on all enterprise assets."
  },
  {
    "safeguard_id": "10.3",
    "safeguard_title": "Disable Autorun and Autoplay for Removable Media",
    "safeguard_description": "Disable autorun and autoplay auto-execute functionality for removable media."
  },
  {
    "safeguard_id": "10.4",
    "safeguard_title": "Configure Automatic Anti-Malware Scanning of Removable Media",
    "safeguard_description": "Configure anti-malware software to automatically scan removable media."
  },
  {
    "safeguard_id": "10.5",
    "safeguard_title": "Enable Anti-Exploitation Features",
    "safeguard_description": "Enable anti-exploitation features on enterprise assets and software, where possible, such as Microsoft\u00ae Data Execution Prevention (DEP), Windows\u00ae Defender Exploit Guard (WDEG), or Apple\u00ae System Integrity Protection (SIP) and Gatekeeper\u2122."
  },
  {
    "safeguard_id": "10.6",
    "safeguard_title": "Centrally Manage Anti-Malware Software",
    "safeguard_description": "Centrally manage anti-malware software."
  },
  {
    "safeguard_id": "10.7",
    "safeguard_title": "Use Behavior-Based Anti-Malware Software",
    "safeguard_description": "Use behavior-based anti-malware software."
  },
  {
    "safeguard_id": "11.1",
    "safeguard_title": "Establish and Maintain a Data Recovery Process",
    "safeguard_description": "Establish and maintain a documented data recovery process that includes detailed backup procedures. In the process, address the scope of data recovery activities, recovery prioritization, and the security of backup data. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "11.2",
    "safeguard_title": "Perform Automated Backups",
    "safeguard_description": "Perform automated backups of in-scope enterprise assets. Run backups weekly, or more frequently, based on the sensitivity of the data."
  },
  {
    "safeguard_id": "11.3",
    "safeguard_title": "Protect Recovery Data",
    "safeguard_description": "Protect recovery data with equivalent controls to the original data. Reference encryption or data separation, based on requirements."
  },
  {
    "safeguard_id": "11.4",
    "safeguard_title": "Establish and Maintain an Isolated Instance of Recovery Data",
    "safeguard_description": "Establish and maintain an isolated instance of recovery data. Example implementations include, version controlling backup destinations through offline, cloud, or off-site systems or services."
  },
  {
    "safeguard_id": "11.5",
    "safeguard_title": "Test Data Recovery",
    "safeguard_description": "Test backup recovery quarterly, or more frequently, for a sampling of in-scope enterprise assets."
  },
  {
    "safeguard_id": "12.1",
    "safeguard_title": "Ensure Network Infrastructure is Up-to-Date",
    "safeguard_description": "Ensure network infrastructure is kept up-to-date. Example implementations include running the latest stable release of software and/or using currently supported network as a service (NaaS) offerings. Review software versions monthly, or more frequently, to verify software support."
  },
  {
    "safeguard_id": "12.2",
    "safeguard_title": "Establish and Maintain a Secure Network Architecture",
    "safeguard_description": "Design and maintain a secure network architecture. A secure network architecture must address segmentation, least privilege, and availability, at a minimum. Example implementations may include documentation, policy, and design components."
  },
  {
    "safeguard_id": "12.3",
    "safeguard_title": "Securely Manage Network Infrastructure",
    "safeguard_description": "Securely manage network infrastructure. Example implementations include version-controlled-infrastructure-as-code, and the use of secure network protocols, such as SSH and HTTPS."
  },
  {
    "safeguard_id": "12.4",
    "safeguard_title": "Establish and Maintain Architecture Diagram(s)",
    "safeguard_description": "Establish and maintain architecture diagram(s) and/or other network system documentation. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "12.5",
    "safeguard_title": "Centralize Network Authentication, Authorization, and Auditing (AAA)",
    "safeguard_description": "Centralize network AAA."
  },
  {
    "safeguard_id": "12.6",
    "safeguard_title": "Use of Secure Network Management and Communication Protocols",
    "safeguard_description": "Adopt secure network management protocols (e.g., 802.1X) and secure communication protocols (e.g., Wi-Fi Protected Access 2 (WPA2) Enterprise or more secure alternatives)."
  },
  {
    "safeguard_id": "12.7",
    "safeguard_title": "Ensure Remote Devices Utilize a VPN and are Connecting to an Enterprise's AAA Infrastructure",
    "safeguard_description": "Require users to authenticate to enterprise-managed VPN and authentication services prior to accessing enterprise resources on end-user devices."
  },
  {
    "safeguard_id": "12.8",
    "safeguard_title": "Establish and Maintain Dedicated Computing Resources for All Administrative Work",
    "safeguard_description": "Establish and maintain dedicated computing resources, either physically or logically separated, for all administrative tasks or tasks requiring administrative access. The computing resources should be segmented from the enterprise's primary network and not be allowed internet access."
  },
  {
    "safeguard_id": "13.1",
    "safeguard_title": "Centralize Security Event Alerting",
    "safeguard_description": "Centralize security event alerting across enterprise assets for log correlation and analysis. Best practice implementation requires the use of a SIEM, which includes vendor-defined event correlation alerts. A log analytics platform configured with security-relevant correlation alerts also satisfies this Safeguard."
  },
  {
    "safeguard_id": "13.2",
    "safeguard_title": "Deploy a Host-Based Intrusion Detection Solution",
    "safeguard_description": "Deploy a host-based intrusion detection solution on enterprise assets, where appropriate and/or supported."
  },
  {
    "safeguard_id": "13.3",
    "safeguard_title": "Deploy a Network Intrusion Detection Solution",
    "safeguard_description": "Deploy a network intrusion detection solution on enterprise assets, where appropriate. Example implementations include the use of a Network Intrusion Detection System (NIDS) or equivalent cloud service provider (CSP) service."
  },
  {
    "safeguard_id": "13.4",
    "safeguard_title": "Perform Traffic Filtering Between Network Segments",
    "safeguard_description": "Perform traffic filtering between network segments, where appropriate."
  },
  {
    "safeguard_id": "13.5",
    "safeguard_title": "Manage Access Control for Remote Assets",
    "safeguard_description": "Manage access control for assets remotely connecting to enterprise resources. Determine amount of access to enterprise resources based on: up-to-date anti-malware software installed, configuration compliance with the enterprise's secure configuration process, and ensuring the operating system and applications are up-to-date."
  },
  {
    "safeguard_id": "13.6",
    "safeguard_title": "Collect Network Traffic Flow Logs",
    "safeguard_description": "Collect network traffic flow logs and/or network traffic to review and alert upon from network devices."
  },
  {
    "safeguard_id": "13.7",
    "safeguard_title": "Deploy a Host-Based Intrusion Prevention Solution",
    "safeguard_description": "Deploy a host-based intrusion prevention solution on enterprise assets, where appropriate and/or supported. Example implementations include use of an Endpoint Detection and Response (EDR) client or host-based IPS agent."
  },
  {
    "safeguard_id": "13.8",
    "safeguard_title": "Deploy a Network Intrusion Prevention Solution",
    "safeguard_description": "Deploy a network intrusion prevention solution, where appropriate. Example implementations include the use of a Network Intrusion Prevention System (NIPS) or equivalent CSP service."
  },
  {
    "safeguard_id": "13.9",
    "safeguard_title": "Deploy Port-Level Access Control",
    "safeguard_description": "Deploy port-level access control. Port-level access control utilizes 802.1x, or similar network access control protocols, such as certificates, and may incorporate user and/or device authentication."
  },
  {
    "safeguard_id": "13.10",
    "safeguard_title": "Perform Application Layer Filtering",
    "safeguard_description": "Perform application layer filtering. Example implementations include a filtering proxy, application layer firewall, or gateway."
  },
  {
    "safeguard_id": "13.11",
    "safeguard_title": "Tune Security Event Alerting Thresholds",
    "safeguard_description": "Tune security event alerting thresholds monthly, or more frequently."
  },
  {
    "safeguard_id": "14.1",
    "safeguard_title": "Establish and Maintain a Security Awareness Program",
    "safeguard_description": "Establish and maintain a security awareness program. The purpose of a security awareness program is to educate the enterprise's workforce on how to interact with enterprise assets and data in a secure manner. Conduct training at hire and, at a minimum, annually. Review and update content annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "14.2",
    "safeguard_title": "Train Workforce Members to Recognize Social Engineering Attacks",
    "safeguard_description": "Train workforce members to recognize social engineering attacks, such as phishing, business email compromise (BEC), pretexting, and tailgating."
  },
  {
    "safeguard_id": "14.3",
    "safeguard_title": "Train Workforce Members on Authentication Best Practices",
    "safeguard_description": "Train workforce members on authentication best practices. Example topics include MFA, password composition, and credential management."
  },
  {
    "safeguard_id": "14.4",
    "safeguard_title": "Train Workforce on Data Handling Best Practices",
    "safeguard_description": "Train workforce members on how to identify and properly store, transfer, archive, and destroy sensitive data. This also includes training workforce members on clear screen and desk best practices, such as locking their screen when they step away from their enterprise asset, erasing physical and virtual whiteboards at the end of meetings, and storing data and assets securely."
  },
  {
    "safeguard_id": "14.5",
    "safeguard_title": "Train Workforce Members on Causes of Unintentional Data Exposure",
    "safeguard_description": "Train workforce members to be aware of causes for unintentional data exposure. Example topics include mis-delivery of sensitive data, losing a portable end-user device, or publishing data to unintended audiences."
  },
  {
    "safeguard_id": "14.6",
    "safeguard_title": "Train Workforce Members on Recognizing and Reporting Security Incidents",
    "safeguard_description": "Train workforce members to be able to recognize a potential incident and be able to report such an incident."
  },
  {
    "safeguard_id": "14.7",
    "safeguard_title": "Train Workforce on How to Identify and Report if Their Enterprise Assets are Missing Security Updates",
    "safeguard_description": "Train workforce to understand how to verify and report out-of-date software patches or any failures in automated processes and tools. Part of this training should include notifying IT personnel of any failures in automated processes and tools."
  },
  {
    "safeguard_id": "14.8",
    "safeguard_title": "Train Workforce on the Dangers of Connecting to and Transmitting Enterprise Data Over Insecure Networks",
    "safeguard_description": "Train workforce members on the dangers of connecting to, and transmitting data over, insecure networks for enterprise activities. If the enterprise has remote workers, training must include guidance to ensure that all users securely configure their home network infrastructure."
  },
  {
    "safeguard_id": "14.9",
    "safeguard_title": "Conduct Role-Specific Security Awareness and Skills Training",
    "safeguard_description": "Conduct role-specific security awareness and skills training. Example implementations include secure system administration courses for IT professionals, OWASP\u00ae Top 10 vulnerability awareness and prevention training for web application developers, and advanced social engineering awareness training for high-profile roles."
  },
  {
    "safeguard_id": "15.1",
    "safeguard_title": "Establish and Maintain an Inventory of Service Providers",
    "safeguard_description": "Establish and maintain an inventory of service providers. The inventory is to list all known service providers, include classification(s), and designate an enterprise contact for each service provider. Review and update the inventory annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "15.2",
    "safeguard_title": "Establish and Maintain a Service Provider Management Policy",
    "safeguard_description": "Establish and maintain a service provider management policy. Ensure the policy addresses the classification, inventory, assessment, monitoring, and decommissioning of service providers. Review and update the policy annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "15.3",
    "safeguard_title": "Classify Service Providers",
    "safeguard_description": "Classify service providers. Classification consideration may include one or more characteristics, such as data sensitivity, data volume, availability requirements, applicable regulations, inherent risk, and mitigated risk. Update and review classifications annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "15.4",
    "safeguard_title": "Ensure Service Provider Contracts Include Security Requirements",
    "safeguard_description": "Ensure service provider contracts include security requirements. Example requirements may include minimum security program requirements, security incident and/or data breach notification and response, data encryption requirements, and data disposal commitments. These security requirements must be consistent with the enterprise's service provider management policy. Review service provider contracts annually to ensure contracts are not missing security requirements."
  },
  {
    "safeguard_id": "15.5",
    "safeguard_title": "Assess Service Providers",
    "safeguard_description": "Assess service providers consistent with the enterprise's service provider management policy. Assessment scope may vary based on classification(s), and may include review of standardized assessment reports, such as Service Organization Control 2 (SOC 2) and Payment Card Industry (PCI) Attestation of Compliance (AoC), customized questionnaires, or other appropriately rigorous processes. Reassess service providers annually, at a minimum, or with new and renewed contracts."
  },
  {
    "safeguard_id": "15.6",
    "safeguard_title": "Monitor Service Providers",
    "safeguard_description": "Monitor service providers consistent with the enterprise's service provider management policy. Monitoring may include periodic reassessment of service provider compliance, monitoring service provider release notes, and dark web monitoring."
  },
  {
    "safeguard_id": "15.7",
    "safeguard_title": "Securely Decommission Service Providers",
    "safeguard_description": "Securely decommission service providers. Example considerations include user and service account deactivation, termination of data flows, and secure disposal of enterprise data within service provider systems."
  },
  {
    "safeguard_id": "17.1",
    "safeguard_title": "Designate Personnel to Manage Incident Handling",
    "safeguard_description": "Designate one key person, and at least one backup, who will manage the enterprise's incident handling process. Management personnel are responsible for the coordination and documentation of incident response and recovery efforts and can consist of employees internal to the enterprise, service providers, or a hybrid approach. If using a service provider, designate at least one person internal to the enterprise to oversee any third-party work. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "17.2",
    "safeguard_title": "Establish and Maintain Contact Information for Reporting Security Incidents",
    "safeguard_description": "Establish and maintain contact information for parties that need to be informed of security incidents. Contacts may include internal staff, service providers, law enforcement, cyber insurance providers, relevant government agencies, Information Sharing and Analysis Center (ISAC) partners, or other stakeholders. Verify contacts annually to ensure that information is up-to-date."
  },
  {
    "safeguard_id": "17.3",
    "safeguard_title": "Establish and Maintain an Enterprise Process for Reporting Incidents",
    "safeguard_description": "Establish and maintain an documented enterprise process for the workforce to report security incidents. The process includes reporting timeframe, personnel to report to, mechanism for reporting, and the minimum information to be reported. Ensure the process is publicly available to all of the workforce. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "17.4",
    "safeguard_title": "Establish and Maintain an Incident Response Process",
    "safeguard_description": "Establish and maintain a documented incident response process that addresses roles and responsibilities, compliance requirements, and a communication plan. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "17.5",
    "safeguard_title": "Assign Key Roles and Responsibilities",
    "safeguard_description": "Assign key roles and responsibilities for incident response, including staff from legal, IT, information security, facilities, public relations, human resources, incident responders, analysts, and relevant third parties. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "17.6",
    "safeguard_title": "Define Mechanisms for Communicating During Incident Response",
    "safeguard_description": "Determine which primary and secondary mechanisms will be used to communicate and report during a security incident. Mechanisms can include phone calls, emails, secure chat, or notification letters. Keep in mind that certain mechanisms, such as emails, can be affected during a security incident. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "17.7",
    "safeguard_title": "Conduct Routine Incident Response Exercises",
    "safeguard_description": "Plan and conduct routine incident response exercises and scenarios for key personnel involved in the incident response process to prepare for responding to real-world incidents. Exercises need to test communication channels, decision making, and workflows. Conduct testing on an annual basis, at a minimum."
  },
  {
    "safeguard_id": "17.8",
    "safeguard_title": "Conduct Post-Incident Reviews",
    "safeguard_description": "Conduct post-incident reviews. Post-incident reviews help prevent incident recurrence through identifying lessons learned and follow-up action."
  },
  {
    "safeguard_id": "17.9",
    "safeguard_title": "Establish and Maintain Security Incident Thresholds",
    "safeguard_description": "Establish and maintain security incident thresholds, including, at a minimum, differentiating between an incident and an event. Examples can include: abnormal activity, security vulnerability, security weakness, data breach, privacy incident, etc. Review annually, or when significant enterprise changes occur that could impact this Safeguard."
  },
  {
    "safeguard_id": "18.1",
    "safeguard_title": "Establish and Maintain a Penetration Testing Program",
    "safeguard_description": "Establish and maintain a penetration testing program appropriate to the size, complexity, industry, and maturity of the enterprise. Penetration testing program characteristics include scope, such as network, web application, Application Programming Interface (API), hosted services, and physical premise controls; frequency; limitations, such as acceptable hours, and excluded attack types; point of contact information; remediation, such as how findings will be routed internally; and retrospective requirements."
  },
  {
    "safeguard_id": "18.2",
    "safeguard_title": "Perform Periodic External Penetration Tests",
    "safeguard_description": "Perform periodic external penetration tests based on program requirements, no less than annually. External penetration testing must include enterprise and environmental reconnaissance to detect exploitable information. Penetration testing requires specialized skills and experience and must be conducted through a qualified party. The testing may be clear box or opaque box."
  },
  {
    "safeguard_id": "18.3",
    "safeguard_title": "Remediate Penetration Test Findings",
    "safeguard_description": "Remediate penetration test findings based on the enterprise's documented vulnerability remediation process. This should include determining a timeline and level of effort based on the impact and prioritization of each identified finding."
  },
  {
    "safeguard_id": "18.4",
    "safeguard_title": "Validate Security Measures",
    "safeguard_description": "Validate security measures after each penetration test. If deemed necessary, modify rulesets and capabilities to detect the techniques used during testing."
  },
  {
    "safeguard_id": "18.5",
    "safeguard_title": "Perform Periodic Internal Penetration Tests",
    "safeguard_description": "Perform periodic internal penetration tests based on program requirements, no less than annually. The testing may be clear box or opaque box."
  }
]

Apply all 14 mapping rules and the evaluation checklist. Return the JSON array of mapped safeguards.
"""