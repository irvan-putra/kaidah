# How much detail is useful before a shared log becomes noise?

Research note for pandu, November 2026. Scope: what published research suggests about how much detail to keep in a shared owner/assistant decision, permission and status log, and where the line between useful detail and noise sits. This is a limited selection of sources from several neighboring fields, not a systematic survey. None of the sources reviewed here studies owner/assistant decision logs directly, so every recommendation is a transfer from another context and is marked as such. Study findings and design recommendations are kept separate throughout. Some sources were read in full; others were read as abstract plus metadata only, which limits how deeply their methods could be checked. The sources list at the end marks the access level for each.

## Short answer

The sources reviewed here did not identify a universal optimum amount of detail, and nothing read for this note supports a fixed number, length or ratio that would separate useful detail from noise in general. What these sources do, coming from distinct contexts (team decision experiments, hospital alarms, software logging, decision records, commit messages, phone notifications, human-AI teaming, provenance systems), is point in a consistent direction:

1. More information helps up to a point, then hurts. Where the point sits varies by person, task and the cost of missing something.
2. Streams of signals that rarely require action can contribute to missed or slower responses in the settings studied (hospital alarms). Whether this transfers to routine logs is not directly studied.
3. The reason behind a decision is commonly missing and commonly needed later, in the commit-message and decision-record studies reviewed.
4. The recurring mechanism is separation between a full stored record and a filtered default view, with detail available on demand.
5. Initial choices about what to record get corrected in use, so a review loop matters.

These are converging suggestions from different settings, not an established cross-field consensus on log design.

## Findings by field

### Decision science and information systems

- Eppler and Mengis (2004) reviewed 30 years of information overload research across organization science, accounting, marketing and MIS, consolidating evidence that information load beyond a person's processing capacity degrades decision quality, and cataloging causes and countermeasures. A conceptual review, not an experiment. Read as abstract only; full text was access-limited.
- Mullins and Sabherwal (2022, MIS Quarterly) ran two experiments (118 dyads, then 60 small teams, deciding over time in a business simulation on an enterprise system) and found an inverted-U relationship between information volume and team decision performance: performance rose with information up to a point, then declined. The curve flattened for members with high computer self-efficacy, indicating the useful amount differs by person. Read as abstract plus the university's summary of the paper; full text was access-limited. Setting was a competitive business simulation, not logging.
- Assmann, Betsch, Lang and Lindow (2022, Journal of Cognitive Psychology) tested 49 high-ability, highly motivated participants (PhD students, postdocs, lecturers) on a probabilistic inference task and found participants looked up roughly twice the amount of information needed, and that using less-relevant information under conflict reduced decision accuracy. Read in full text. Small lab sample.

### Clinical alarms: measured harm from low-actionability signal streams

- The Joint Commission's Sentinel Event Alert Issue 50 (2013) estimates that 85 to 99 percent of medical device alarm signals require no clinical intervention, and describes clinicians becoming desensitized ("alarm fatigue"). Its recommendations concern defaults, per-patient tailoring of thresholds, training and periodic review of alarm policies, not asking staff to pay more attention. Read in full text.
- Paine et al. (2016, Journal of Hospital Medicine), a systematic review of 24 observational studies plus 8 intervention studies, found the proportion of actionable monitor alarms ranged from under 1 percent to 36 percent depending on setting, and that two studies linked higher alarm exposure to slower nurse response times. The authors rate the evidence as emerging, with many studies at high risk of bias. Read in full text.

Transfer caution: these are continuous monitoring environments where missed signals carry immediate clinical risk. A decision and permission log is quieter and less time-critical, so the strength of the analogy is limited. The narrower point that transfers is that a stream dominated by items nobody acts on degrades response to the items that matter, and that tuning thresholds and defaults is the fix that field reached for.

### Software logging: verbosity levels as a widely used mechanism

- Yuan, Park and Zhou (ICSE 2012) conducted what they describe as the first quantitative study of logging practice in four large open-source systems (Apache httpd, OpenSSH, PostgreSQL, Squid). Verbosity levels (fatal, error, info, debug) trade the benefit of more messages against their cost; production defaults in the studied software show errors plus a small fraction of book-keeping messages. Developers often did not get logging right initially: 33 percent of log-code modifications in the studied revision histories were afterthoughts, and 26 percent of log improvements adjusted the verbosity level, mostly reflecting changed judgment about how critical an event was. The authors caution against generalizing beyond their four C/C++ server systems. Read in full text.

Transferable suggestion: a level system with a restrictive default view is a well-worn pattern, and initial level assignments should be expected to need correction in use.

### Decision records: concise records versus rich templates

- Nogueira, Silva and Conte (2026, arXiv preprint) compared five Architecture Decision Record templates through expert feature analysis plus a controlled experiment with 33 student participants. The concise Nygard template (title, status, context, decision, consequences) scored best overall in their measures; the richer MADR template helped where structural detail mattered. The authors frame the goal as balancing documentation overhead against knowledge retention, and cite earlier conceptual work identifying common core elements (Decision, Rationale, Solution) across decision-documentation models. A preprint with student participants; transfer to other settings is suggestive. Read in full text.

### Commit messages: "what and why" in one developer community

- Tian, Zhang, Stol, Jiang and Liu (ICSE 2022) studied roughly 1,600 commit messages from five active Java open-source projects and surveyed 30 experienced developers from those projects. About 93 percent of the surveyed developers held that a good message says what changed and why; about 44 percent of the sampled real messages lacked one or both. Read in full text. One developer community and one artifact type; the agreement figure describes those 30 respondents, not developers generally.

Transferable suggestion: in this context the reason for a change was the information respondents most wanted and most often failed to record. A short entry with a reason served readers better than a longer entry without one.

### Notifications: interruption frequency is separate from stored detail

- Kushlev, Proulx and Dunn (CHI 2016), in a within-subject experiment with 221 participants, found that a week with phone notification alerts on produced higher self-reported inattention and hyperactivity symptoms than a week with alerts off, with inattention predicting lower self-reported productivity and well-being. Read in full text.

Transferable suggestion: how much a log stores and how often it interrupts its readers are independent choices. Storing more need not mean interrupting more.

### Human-AI teaming transparency: limited selection, early evidence

- Park (2023, MS thesis, University of Michigan-Dearborn) compared two AI transparency levels in one cooperative task with 20 participants and found higher transparency drew more attention to the display, reduced subjective workload and increased trust; the thesis flags individual differences. Read as abstract plus metadata.

This is one small thesis, chosen because it measures exactly the variable in question (level of transparency) in a human-AI setting. It is not a characterization of the human-AI transparency literature as a whole, and it supports at most a weak suggestion: adjustable detail may be worth offering, since the useful level appears to vary by person.

### Provenance systems: separate the base record from annotations and presentation

- MITRE's "Provenance Capture and Use: A Practical Guide" (2010) describes capturing a base provenance record that is not modified after writing, with further metadata added as annotations, treats capture granularity as an explicit per-application tradeoff, and warns that provenance gets used for questions nobody anticipated at design time. Read as extracted full text (layout-degraded in places).

## What these sources do and do not support

The sources reviewed converge on these suggestions, each arising in its own context:

- Both too little and too much information degrade decisions (decision experiments).
- Streams dominated by items requiring no action degrade response (clinical alarms; notification studies for the interruption variant).
- The reason behind a decision was commonly missing and wanted by readers in the studies reviewed (commit messages, decision records).
- Store the record and filter the view separately; offer levels and expansion on demand (logging, decision records, provenance).
- Expect to revise what gets recorded; build in periodic review (logging afterthoughts, alarm policy reviews, documentation-overhead findings).

Not supported by anything reviewed here:

- A specific number, length or ratio that separates useful detail from noise.
- Direct evidence about owner/assistant shared decision and permission logs, for human or AI assistants. No such study appeared in the sources reviewed; the recommendations below are transfers.
- Strong conclusions about optimal transparency in human-AI assistant work; the selection here is one small thesis.

## Design recommendations for pandu

Recommendations derived from the findings above, not findings themselves. They describe design direction only; the concrete storage format is the builder's evolving choice and this note does not bind it.

1. Keep two layers distinct: a stored record and a filtered status view. The stored record is written append-only by convention (corrections are new entries, old values stay readable) - that is an editing discipline, not a guarantee of immutability against anyone with file access. The status view shows current, actionable state (running, blocked, needs approval, expired-but-open attention items). Manage noise at the view layer.
2. Record the minimum sufficient evidence for each decision, grant and correction: what was decided, by whom, when, and a short reason or reference. Do not copy wholesale private messages, secrets or unrelated context into the log, and do not retain more than the record's purpose needs. Completeness of the record does not mean maximal data collection.
3. Consider asking for a short "why" on entries recording grants, decisions and corrections. In the commit-message and decision-record studies reviewed, rationale was commonly missing and wanted by readers. This is a design suggestion; nothing reviewed shows it is the highest-value field.
4. Keep kind and severity levels on entries so views can filter (the logging pattern). Expect to re-tune which kinds surface by default after real use.
5. Separate "stored" from "pushed": batch routine status into digests; reserve immediate notification for approval-needed and expiry-soon items (the notification finding).
6. The alarm and logging fields both rely on periodic review. If a review aid is wanted, keep it optional and local-only (for example, counts of entries by kind over a period, computed on demand), not an always-on tracking feature; justify any addition against the privacy constraint in point 2.
7. Offer a brief and a full status rendering; the information-volume experiments and the transparency thesis both found the useful level varies by person.
8. Do not treat "an entry nobody acts on immediately" as automatically noise. History that no one acts on today can still answer later questions (the provenance guide's point about unanticipated uses). The actionable filter belongs to the default view, not to what may be stored.

## Sources

Access level noted per source: full text, or abstract only (paywalled or metadata page).

- Eppler, M. J., and Mengis, J. (2004). "The Concept of Information Overload: A Review of Literature from Organization Science, Accounting, Marketing, MIS, and Related Disciplines." The Information Society, 20(5), 325-344. Abstract only. <https://www.tandfonline.com/doi/full/10.1080/01972240490507974>
- Mullins, J. K., and Sabherwal, R. (2022). "Just Enough Information? The Contingent Curvilinear Effect of Information Volume on Decision Performance in IS-Enabled Teams." MIS Quarterly, 46(4). Abstract plus publisher-summary only. <https://aisel.aisnet.org/misq/vol46/iss4/17/> (DOI: <https://doi.org/10.25300/misq/2022/17290>)
- Assmann, L., Betsch, T., Lang, A., and Lindow, S. (2022). "When even the smartest fail to prioritise: overuse of information can decrease decision accuracy." Journal of Cognitive Psychology, 34(6), 675-690. Full text. <https://www.tandfonline.com/doi/full/10.1080/20445911.2022.2055560>
- The Joint Commission (2013). "Medical device alarm safety in hospitals." Sentinel Event Alert, Issue 50. Full text. <https://digitalassets.jointcommission.org/api/public/content/f65e5c9df2b94000a99445e0a7877007>
- Paine, C. W., Goel, V. V., Ely, E., Stave, C. D., Stemler, S., Zander, M., and Bonafide, C. P. (2016). "Systematic review of physiologic monitor alarm characteristics and pragmatic interventions to reduce alarm frequency." Journal of Hospital Medicine, 11(2), 136-144. Full text. <https://pmc.ncbi.nlm.nih.gov/articles/PMC4778561/>
- Yuan, D., Park, S., and Zhou, Y. (2012). "Characterizing logging practices in open-source software." Proceedings of ICSE 2012. Full text. <https://cs.uwaterloo.ca/~m2nagapp/courses/CS846/1171/papers/yuan_icse12.pdf>
- Nogueira, F., Silva, N., and Conte, T. (2026). "One Size Fits All? An Empirical Comparison of ADR Templates regarding Comprehension, Usability, and Ease of Adoption." arXiv:2604.27333 (preprint). Full text. <https://arxiv.org/abs/2604.27333>
- Tian, Y., Zhang, Y., Stol, K.-J., Jiang, L., and Liu, H. (2022). "What Makes a Good Commit Message?" Proceedings of ICSE 2022. arXiv:2202.02974. Full text. <https://arxiv.org/abs/2202.02974>
- Kushlev, K., Proulx, J., and Dunn, E. W. (2016). "'Silence Your Phones': Smartphone Notifications Increase Inattention and Hyperactivity Symptoms." Proceedings of CHI 2016. Full text. <https://interruptions.net/literature/Kushlev-CHI16.pdf>
- Park, G. (2023). "The Effect of Level of AI Transparency on Human-AI Teaming Performance Including Trust in Machine Learning Interface." MS thesis, University of Michigan-Dearborn. Abstract only. <https://deepblue.lib.umich.edu/items/72f65699-26f8-4608-92a1-f58b72ac1259/full>
- MITRE (2010). "Provenance Capture and Use: A Practical Guide." Full text. <https://www.mitre.org/sites/default/files/publications/practical-provenance-guide-MP100128.pdf>
