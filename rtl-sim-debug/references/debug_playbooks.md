# Debug Playbooks — per-scenario drill-downs

Reach for a playbook once the Failure Digest and classification are in hand. Each playbook assumes Phases 1-5 are complete and provides the Phase 6 waveform steps plus Phase 7 next-actions.

## Playbook: Testbench hang (no fatal/error, sim stuck)

1. Confirm it's a hang, not a slow run — check last sim-time progression over the tail 2000 lines.
2. Find the last `phase_started`. That's the stuck phase.
3. Extract the objection trace (`phase_dump_state` or rerun with `+UVM_OBJECTION_TRACE`). Identify components still objecting.
4. For each objecting component, ask: what transaction is it waiting on?
   - Sequencer waiting for driver response → driver deadlock.
   - Monitor waiting on interface event → RTL never produced the event.
5. Pull that interface's signals from `.rc`; extract waveform from `last_activity_time - 1us` to `last_activity_time`.
6. Classify: if DUT port never asserted the expected event → **RTL**. If DUT fired event but TB missed it (monitor bug, sampling edge) → **TB**.

## Playbook: X-propagation into control signal

1. From the digest, the failing signal name and time are known.
2. Waveform window: `[fail_time - 100ns, fail_time + 10ns]`.
3. Trace the `X` backward one hop at a time (Phase 6e). Every hop, identify whether the `X` source is:
   - Uninitialized register (no reset, no first write) → RTL.
   - Select of an uninitialized register through a mux with an `X` select → trace the select.
   - Port driven by TB with `X` → TB stimulus bug.
4. Clock gating with wrong enable before reset deassertion is a classic cause — check clock/reset timing at the suspect module.

## Playbook: Protocol assertion (AXI SLVERR / DECERR)

1. Digest provides assertion name + time + hierarchy (the port instance).
2. Pull AXI5-channel signals from `.rc` for that port: `AR*`, `R*`, `AW*`, `W*`, `B*`.
3. Waveform window `[fail_time - 2us, fail_time + 100ns]`.
4. Apply §6d checklist (Error-to-signal mapping) on each channel.
5. Key decision:
   - If DUT returned SLVERR/DECERR on a **legal** address → RTL decoder bug or attribute mismatch.
   - If DUT returned SLVERR on a **TB-driven illegal** address → TB or test.
   - If IDs mismatch between request and response → RTL ordering/ID reuse bug.
6. If RTL, trace the response-generator path back from `BRESP`/`RRESP` to the address-decoder output.

## Playbook: Reset/CDC glitch

1. Reset-release timing: compare each reset's deassertion edge to the clock it's synchronized to. Async deassert without sync release → metastability.
2. For each flagged CDC: confirm the hand-off uses a proper synchronizer (2+ flops on destination clock, no combinational path between source and sync-flop-input).
3. Waveform check: look for pulses narrower than the destination clock period on non-synchronized CDC lines.
4. Classification: almost always **RTL**; file JIRA.

## Playbook: Scoreboard mismatch

1. Are both the expected and actual transactions produced correctly? Check:
   - Monitor on DUT input side captured the input correctly? (compare vs sequence item on driver side).
   - Monitor on DUT output side captured the output correctly? (compare vs waveform at the port).
   - Predictor transformed input correctly?
2. If input monitor is correct but predictor output != DUT output → **RTL**.
3. If input monitor disagrees with driver stimulus → **TB** (monitor bug).
4. If predictor is wrong → **TB** (predictor bug).

## Playbook: Phase race / `config_db` miss

1. Log shows `CFGNTS` or NULL handle.
2. Find the `set` call (grep for the exact field name under DV root).
3. Find the `get` call site.
4. Confirm `set` executes before `get`'s phase. Common race: `set` in `build_phase` of a component that is itself created in `build_phase` of its parent, and a sibling reads before it's set.
5. Fix: promote the `set` to an earlier phase/scope, or change instantiation order.

## Playbook: Seed-sensitive flake

1. Check regression index for the fail rate across seeds.
2. Low rate + same signature → likely a race (RTL CDC, arbitration, TB race).
3. High rate + same signature → real bug just seed-revealed.
4. Rerun the same seed with richer verbosity to capture a reproducible trace.

## Playbook: Env wave (many tests failing today)

1. Regression index shows a spike in `daily_totals.fails` today across unrelated testcases.
2. Check build: was `simv` rebuilt today? Any tool/version change in the env?
3. Compare any single known-good testcase against yesterday's build; if it passes on yesterday's simv → Env.
4. Classification: **Env**. Do not waste cycles on RTL/TB unless infra is cleared first.
