# ContentMatePro Agentic Roadmap

This document captures the planned "agentic" phase for ContentMatePro so we can
pause it, ship other work such as SEO, and return without losing the design.

## Goal

Upgrade the current single-pass analysis flow into a specialist, multi-step AI
pipeline that feels meaningfully smarter and more transparent to the user.

Today the backend does this:

1. Sync channel and candidate videos.
2. Fetch transcripts or fall back to metadata-only analysis.
3. Run one analysis pass.
4. Run one ideas generation pass.
5. Return a combined result.

Target direction:

1. Build a channel evidence package once.
2. Run specialist agents on that shared evidence.
3. Pass structured outputs from one stage to the next.
4. Merge those outputs into a richer final report and strategy plan.

## Proposed Agent Lineup

### 1. Channel Strategy Agent

Purpose:

- Identify niche, audience, content pillars, strengths, weaknesses, and content
  opportunities.

Inputs:

- Channel metadata
- Selected video metadata
- Transcript evidence when available
- Transcript coverage stats
- Selected content types (videos, streams, shorts)

Outputs:

- Channel niche summary
- Audience profile
- Strongest recurring themes
- Key strengths
- Key gaps
- Strategic opportunities
- Confidence notes tied to transcript coverage

Why first:

- Every other specialist should build on the same diagnosis instead of
  re-deriving it from scratch.

### 2. Long-Form Ideas Agent

Purpose:

- Turn the strategy diagnosis into strong long-form content ideas.

Inputs:

- Strategy agent output
- Channel/video evidence package

Outputs:

- Long-form video ideas
- Title hooks
- Thumbnail angles
- Why each idea fits the channel

Notes:

- This should stay grounded in the strategy output so ideas are channel-specific
  rather than generic.

### 3. Shorts Agent

Purpose:

- Generate short-form content opportunities, especially from clips, hooks, or
  repeatable short concepts.

Inputs:

- Strategy agent output
- Channel/video evidence package
- Transcript snippets when available

Outputs:

- Shorts concepts
- Hook ideas
- Clip angles
- Repackaging suggestions from long-form content

Notes:

- If the user analyzed only streams, this agent should still work by extracting
  short-form moments from streams.

### 4. Planner Agent

Purpose:

- Turn diagnosis plus ideas into a usable publishing plan.

Inputs:

- Strategy agent output
- Long-form ideas output
- Shorts output

Outputs:

- 4-week content calendar
- Sequencing rationale
- Recommended publishing mix
- Priority order
- Suggested testing plan

Notes:

- This is the "synthesis" step that should make the overall experience feel like
  a coherent strategist rather than several disconnected generators.

## Recommended Orchestration

Planned backend order:

1. Channel sync
2. Transcript fetch or metadata fallback
3. Evidence packaging
4. Strategy agent
5. Long-form ideas agent
6. Shorts agent
7. Planner agent
8. Final response assembly

Important rule:

- All downstream agents should consume a shared normalized evidence package
  rather than each building its own prompt input independently.

## Proposed Backend Shape

Current relevant files:

- `apps/api/app/services/pipeline_service.py`
- `apps/api/app/services/analysis_service.py`
- `apps/api/app/services/ideas_service.py`
- `apps/api/app/integrations/openai/analysis_client.py`
- `apps/api/app/integrations/openai/ideas_client.py`

Likely additions:

- `apps/api/app/services/agent_orchestrator_service.py`
- `apps/api/app/services/agent_strategy_service.py`
- `apps/api/app/services/agent_longform_service.py`
- `apps/api/app/services/agent_shorts_service.py`
- `apps/api/app/services/agent_planner_service.py`
- `apps/api/app/integrations/openai/strategy_client.py`
- `apps/api/app/integrations/openai/longform_client.py`
- `apps/api/app/integrations/openai/shorts_client.py`
- `apps/api/app/integrations/openai/planner_client.py`
- `apps/api/app/schemas/agent_strategy.py`
- `apps/api/app/schemas/agent_longform.py`
- `apps/api/app/schemas/agent_shorts.py`
- `apps/api/app/schemas/agent_planner.py`
- `apps/api/app/schemas/agent_workflow.py`

## Shared Evidence Package

Before running agents, build a shared package with:

- Channel title and description
- Selected content types
- Analyzed videos list
- Video titles, descriptions, durations, publish dates, views
- Transcript text or transcript snippets
- Transcript success/failure counts
- Transcript coverage ratio
- Analysis mode:
  - `transcript-backed`
  - `metadata-only`

This package should be reusable across all agent prompts and saved as a
first-class internal object so the workflow stays stable as agents evolve.

## Output Contract Direction

The final workflow response should eventually contain:

- `strategy`
- `long_form_ideas`
- `shorts_ideas`
- `planner`
- `workflow_meta`

`workflow_meta` should include:

- models used
- transcript coverage ratio
- number of videos analyzed
- number of transcripts analyzed
- whether metadata fallback was used
- per-agent success or failure state

## UX Direction

The UI should eventually show the workflow as stages, for example:

1. Collecting channel evidence
2. Diagnosing channel strategy
3. Generating long-form ideas
4. Generating shorts concepts
5. Building 4-week plan

Optional later improvement:

- Let users expand each stage to view the specialist output separately.

## Guardrails

When implementing the agentic phase:

- Keep all claims grounded in provided metadata and transcripts.
- Preserve metadata-only fallback when transcripts fail.
- Do not invent evidence from outside the fetched channel context.
- Keep outputs structured and schema-validated.
- Keep prompts role-specific instead of one giant universal prompt.
- Maintain current auth, rate limit, and daily usage protections.

## Delivery Plan

Recommended implementation sequence:

### Phase A: Internal refactor

- Extract shared evidence package builder.
- Introduce an orchestrator service.
- Keep existing API response shape stable where possible.

### Phase B: Strategy agent

- Ship strategy specialist first.
- Verify output quality against current single-pass analysis.

### Phase C: Ideas split

- Separate long-form ideas and shorts ideas into different specialists.

### Phase D: Planner

- Add planner synthesis and 4-week sequencing output.

### Phase E: UI visibility

- Show workflow stages in the frontend.
- Optionally expose per-agent outputs.

## Success Criteria

We should consider the agentic phase successful when:

- Outputs feel more specialized than the current single-pass flow.
- Strategy, ideas, shorts, and planning each have clear ownership.
- Metadata-only fallback still produces useful structured output.
- The final result is more actionable without becoming harder to read.
- The implementation remains maintainable and testable.

## Where To Resume Later

When we come back to agentic work, start here:

1. Review this file.
2. Inspect:
   - `apps/api/app/services/pipeline_service.py`
   - `apps/api/app/services/analysis_service.py`
   - `apps/api/app/services/ideas_service.py`
   - `apps/api/app/integrations/openai/analysis_client.py`
   - `apps/api/app/integrations/openai/ideas_client.py`
3. Build the shared evidence package.
4. Add the orchestrator service.
5. Implement the strategy agent first.
