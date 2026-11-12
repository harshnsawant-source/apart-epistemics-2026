# References, checked against their real records (13 Nov 2026)

Each entry was looked up on arXiv (export API) or the ACL Anthology, and the claims we rely on were checked
in the paper's own text. "Checked" means the sentence below matches what the paper says; it is still worth
reading the sections yourself before you write about them.

## Sprint 1 (announced audits)

1. **Ahmed et al. 2025.** "Do LLMs Know They Are Being Tested? Evaluation Awareness and Incentive-Sensitive
   Failures in GPT-OSS-20B." arXiv 2510.08624 (8 Oct 2025), Nisar Ahmed and 3 co-authors.
   Checked (§4.4, §7.2.2): one model (GPT-OSS-20B); citation scenario with n = 20 per cell; the "eval" framing
   demands exactly three DOIs while the "real" framing allows up to three or an uncertainty statement, so the
   framing and the permission to abstain change together; DOIs are counted with a regex ("DOI-like strings"),
   not looked up. The authors themselves say citation reliability is hard to evaluate "without external
   retrieval or bibliographic validation". **This is the gap the sprint design fills.**

2. **Agrawal, Suzgun, Mackey, Kalai 2024.** "Do Language Models Know When They're Hallucinating References?"
   Findings of EACL 2024, pp. 912-928, doi:10.18653/v1/2024.findings-eacl.62.
   Checked (abstract): asking a model consistency questions (for example about authors) can flag hallucinated
   references without external sources.

3. **Knecht, Florin, Hagendorff 2026.** "Evaluation Awareness in Language Models Has Limited Effect on
   Behaviour." arXiv 2605.05835 (7 May 2026).
   Checked: eight open-weight reasoning models including GPT-OSS-120b; evaluation-awareness sentences injected
   into or removed from the chain of thought; benchmarks on safety, alignment, moral reasoning and political
   opinion; effects near zero to small. No citation outcomes.

4. **Mehta 2025.** "Can We Trust AI Explanations? Evidence of Systematic Underreporting in Chain-of-Thought
   Reasoning." arXiv 2601.00830 (posted 25 Dec 2025), single author, Deep Pankajbhai Mehta.
   Checked (abstract): over 9,000 cases, 11 models, hints in questions; "Telling models they are being watched
   does not help" with reporting the hints. Different outcome from ours (hint reporting, not citations).

5. **Zhao et al. 2026.** "Do Deployment Constraints Make LLMs Hallucinate Citations? An Empirical Study across
   Four Models and Five Prompting Regimes." arXiv 2603.07287 (7 Mar 2026), Chen Zhao and 2 co-authors.
   Checked: Crossref + Semantic Scholar verification; Claude Sonnet, GPT-4o, Llama 3.1-8B, Qwen 2.5-14B; regimes
   Baseline, Temporal, Survey-style breadth, Non-Disclosure, Combo. **The Non-Disclosure regime forbids claims of
   training-data access; it is not an audit announcement**, so no collision. They use an Existing / Unresolved /
   Fabricated taxonomy close to ours: cite it for that.

6. **Goyal 2026.** "Towards Verifiable Answers: Reinforcement Learning with a Verifier Reduces Hallucinated
   References in Literature-Based Question Answering." Proceedings of the 4th Workshop on AI for Scientific
   Publications (WASP), pp. 199-209, published 10 Nov 2026.
   Checked: trains Llama-3.1-8B-Instruct and Llama-3.2-3B-Instruct with GRPO against a verifier using Crossref
   and OpenAlex (Semantic Scholar dropped after an ablation); §4.6 "Existence is not relevance": the trained
   model favours canonical but off-topic papers on niche questions.

Also confirmed to exist (fallback design only): SycEval, Fanous et al., arXiv 2502.08177; "Are You Sure You're
Sure? Two Confounds in a Sycophancy Benchmark", Gupta et al., arXiv 2609.32867.

## Flagship (citation probes)

7. **Obeso et al. 2025.** "Real-Time Detection of Hallucinated Entities in Long-Form Generation."
   arXiv 2509.03531 (v2), Oscar Obeso and 5 co-authors.
   Checked: token-level probes for hallucinated entities (names, dates, citations); one of four prompt
   categories is citation-focused; labels from Claude 4 Sonnet with web search; main model Llama-3.3-70B, with
   Gemma-2-9B, Qwen-2.5-7B and Mistral-24B as secondary models; includes selective answering.
   NOT checked: Astra's figure of "about 1,000 citation prompts".
   Differences for us: our labels come from bibliographic databases plus a human audit, and we use a 3B model.
8. **Chen et al. 2026.** "Where Fake Citations Are Made: Tracing Field-Level Hallucination to Specific Neurons
   in LLMs." arXiv 2604.18880 (20 Apr 2026), Yuefei Chen and 3 co-authors. Title and authors checked only.
9. **Orgad et al. 2024.** "LLMs Know More Than They Show: On the Intrinsic Representation of LLM
   Hallucinations." arXiv 2410.02707. Title and authors checked only.
10. **Ferrando et al. 2024.** "Do I Know This Entity? Knowledge Awareness and Hallucinations in Language Models."
    arXiv 2411.14257 (ICLR 2025 per Astra; venue not checked). Title and authors checked only.
