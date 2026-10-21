# Demo script: legacy risk models to Python with Devin

> **All fictional.** Exemplar Bank, Quill, RiskDB, every person and number here are invented.
> Audience: Head of Risk Engineering, first meeting (M1). 15 minutes, about 5 minutes of demo.

**The line to land:** "Your engineers stop spending a quarter on translation and spend it on judgment calls like #10."

Plain-English glossary for the room: **Quill** = the bank's old in-house risk language;
**parity** = the new Python gives the same numbers as the old system, case by case;
**PR** (pull request) = a proposed code change waiting for a human to approve it;
**playbook** = a written procedure Devin follows every time.

---

## Before the meeting (day before)

1. **Connect the repo** in Devin (`club-cog/sap-migration-demo`) and check out the demo branch
   (no suffix). Make sure the repo is **indexed for Ask Devin** (open Ask Devin, ask a test question, check it cites files).
2. **Register the playbook**: create a Devin playbook from `docs/playbook-quill-to-python.md`.
   Note its id: `playbook-<id>`.
3. **Pre-run Scene 1** in Ask Devin and keep the answer tab open.
4. **Pre-run the fan-out session (Scene 3)** with the exact prompt below. It takes a while: 10
   child sessions, 10 PRs. Keep that session tab open. Check: 9 PRs show 100% parity, the
   `collateral_margin_call` PR starts with "Human decision needed".
5. **Backup branch**: the same branch name with the `-complete` suffix has the finished result
   (`docs/migration-report.md`, `docs/findings/collateral_margin_call.md`). Have it open in a tab.
6. Tabs open, left to right:
   1. Ask Devin answer (Scene 1)
   2. `legacy/models/lcr_outflows.quill` in the repo (to show what legacy looks like)
   3. New Devin session, empty, ready for the Scene 3 prompt
   4. The pre-run fan-out session (Scene 3 result)
   5. The flagged `collateral_margin_call` PR in Devin Review (Scene 4)
   6. Backup: `docs/migration-report.md` on the `-complete` branch

---

## Opening (30 s, before any screen)

**Say:** "This is a made-up bank, Exemplar Bank. Ten risk models in a language only a few people
there ever knew. Most of the authors are gone. Sound familiar?"
**Ask:** "How many models like this do you have, and who still understands them?"
**Bridge:** "Let me show you three things: understand, migrate, review."

---

## Scene 1: Ask Devin, understand (~1 min, pre-run)

**Prompt (paste into Ask Devin):**

> Where does the LCR model apply the stress haircut, and what breaks if we change it?

**What to show** (from the pre-run answer tab):
- It finds the haircut in `legacy/models/lcr_outflows.quill`: the `STRESS_HC` cell (L20) and
  where it is passed in when the stress flag is on (L61-65).
- It follows the call into `hqla_haircut.quill`: `hqla_stock` adds the extra haircut by level and
  caps at 100% (L60), then the Level 2 caps (L66-68).
- It names the shared dependency: `lib/rounding.quill` (money / rate rounding).
- It gives a diagram: `lcr_outflows -> hqla_haircut -> rounding`, and says what breaks:
  LCR ratio, RED/AMBER/GREEN status, and anything else calling `hqla_stock`.
- Every claim has a file + line citation. Click one to prove it.

**Say:** "Nobody here wrote Quill. Devin read the code and the dependencies and answered with line numbers."
**Ask:** "How long does it take your team today to answer a question like that on an old model?"
**Bridge:** "Understanding is step one. Now let's move the whole thing."

---

## Scene 2 (optional): Ask Devin, plan and risks (~30 s)

**Prompt:**

> In what order should we migrate these 10 models, based on dependencies and risk?

**What a good answer shows:** shared libs first (`rounding`, `daycount`, `stats`), then
`hqla_haircut` before `lcr_outflows`, `hist_var` before `expected_shortfall`; flags higher-risk
models (date logic and rounding in `collateral_margin_call`, stress branches in `lcr_outflows`).

**Say:** "Same index, now as a planning tool: order and risk, before anyone writes code."
**Ask:** "Do you have an inventory like this today, or is it in people's heads?"
**Bridge:** "Now the part that usually takes a quarter."

---

## Scene 3: the wow, one prompt, 10 models in parallel (~3 min)

**Live:** in the empty Devin session tab, paste this prompt (replace `<id>`), hit enter:

```
Migrate all 10 Quill models in legacy/models to Python using playbook-<id>.
Start one managed Devin session per model, each opening its own PR.
Port hqla_haircut before lcr_outflows and hist_var before expected_shortfall.
When done, give me one table: model, PR link, parity (cases matched / total), and any "Human decision needed".
```

Let it start the first child sessions (10-20 s), then **switch to the pre-run tab**.

**What to show** (pre-run session):
- 10 child sessions, 10 PRs.
- 9 PRs: 100% parity, unit tests green, a docstring table mapping each rule to the Quill line.
- **#10 `collateral_margin_call`**: top of the PR says **Human decision needed**. On weekend
  as-of dates the legacy code takes a different branch, rolls back to the Friday fixing and
  **truncates** the call instead of rounding half-up. 3 cases out of 28. Devin did not copy the
  bug and did not touch the reference outputs: it marked those 3 cases, wrote a finding with the
  exact Quill lines, and laid out Option A (keep legacy) vs Option B (fix and restate).

**Say:** "One prompt. Ten parallel engineers. Each proved its numbers match the old system, case by case."
**Say:** "And #10 is the important one. Devin found a weekend rounding bug nobody knew about, and stopped to ask."
**Ask:** "Who on your side would make that call today, and how would they even find it?"
**Bridge:** "Which brings us to the human in the loop."

---

## Scene 4: Devin Review (~1 min)

**What to show:** open the `collateral_margin_call` PR in Devin Review.
- The diff is grouped and explained; the finding doc and the 3 `xfail` cases are right there.
- The parity table in the description: 25 match, 3 flagged, 0 silent failures.
- A human picks Option A or B and approves. **Nothing merges without sign-off.**

**Say:** "Devin does the translation and the proof. Your engineer makes the judgment call, with all the evidence on one page."
**Ask:** "What would your model risk team need to see in a PR like this to sign it off?"
**Bridge:** "Your engineers stop spending a quarter on translation and spend it on judgment calls like #10."

---

## Discovery questions

1. **How many models are still on in-house or legacy languages, and how many people can maintain them?**
   Follow-up: what happens when one of those people leaves? Has it already happened?
2. **How do you prove a migrated model gives the same numbers today?**
   Follow-up: who signs off on parity, and how long does validation take per model?
3. **What is on the migration roadmap for the next 12-18 months?**
   Follow-up: what is the current estimate per model, and what is blocking it, people or process?
4. **When you change a shared library (rounding, day count, curves), how do you find what it breaks?**
   Follow-up: has a "small" change ever caused a break in a regulatory number?
5. **How does model risk / validation get involved in a code change?**
   Follow-up: what evidence do they require: parity reports, line-level traceability, test cases?
6. **Where does your team spend most of its time: new models, regulatory change, or keeping old ones alive?**
   Follow-up: what would you do with a quarter of that time back?
7. **Which AI coding tools are approved today, and under what controls?**
   Follow-up: who owns that approval, tech risk, CISO, or the architecture board?

---

## Objections

**"We already have Claude Code / Codex."**
Great for one engineer in one file. This is different: Devin runs 10 sessions in parallel, follows
your playbook every time, proves parity, and opens reviewable PRs. It is the team, not the autocomplete.

**"Our tech risk team won't allow it."**
Understood, and they should have a say. Devin can run in your environment, with your access
controls and audit trail, and it never merges: every change is a PR a human approves. Happy to start
with their checklist.

**"How do we trust AI output in a regulated model?"**
You don't have to trust it, you check it. Every rule is traced to the legacy line, every case is
compared to the legacy output, and when they differ Devin stops and asks, like on #10.

---

## If something goes wrong

- **Ask Devin is slow or the index is stale:** use the pre-run answer tab.
- **The live fan-out is slow or fails to start:** don't wait. Say "I started this yesterday, here is
  the result" and switch to the pre-run session tab.
- **The pre-run session is missing or broken:** switch to the backup branch (same name with
  `-complete`). Show `docs/migration-report.md` (the 10-model table), then
  `docs/findings/collateral_margin_call.md` (the #10 finding), then `pytest -v` output:
  all green with exactly 3 xfails.
- **Anything else:** go back to the line: "Your engineers stop spending a quarter on translation and spend it on judgment calls like #10."
