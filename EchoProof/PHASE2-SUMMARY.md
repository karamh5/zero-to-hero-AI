# EchoProof - Phase 2 Summary

Automatic proxy capture and the audio path. SPEC sections 2 and 8.
Completion condition from PHASES.md: a live exchange flows proxy to claim to
verdict with a playable clip and zero manual feed. Met.

## 1. Proxy overhead, measured

| Measure | Value |
|---|---|
| Median overhead added by EchoProof | **0.129 ms** client side, 0.036 ms server side |
| p95 | 0.189 ms |
| Worst case observed | 0.250 ms |
| Budget | 50 ms |
| Upstream model latency, for comparison | 1198 ms median |

Roughly 200 times under budget. Overhead is measured as the time EchoProof adds,
excluding the upstream model call, which is the honest reading: the client pays
for that call whether or not EchoProof is in front of it. Both figures are
returned on every response as `x-echoproof-overhead-ms` and
`x-echoproof-upstream-ms`, so a client sees the cost in their own traces rather
than taking this document's word for it.

Closes brief audit gap 3, which the brief listed as a diagnostic metric with no
phase measuring it.

## 2. Capture with zero manual feed

| Measure | Value |
|---|---|
| Turns captured | 13 |
| Processed | 13 |
| Dropped | 0 |
| Failed | 0 |

Twelve came from real proxied calls driven by the stock OpenAI SDK pointed at
the proxy, which is exactly what a client's agent does. One came through the
transcript ingest path.

## 3. Transcript ingest path

`POST /v1/transcripts` accepts a turn that never passed through an LLM proxy,
which is what makes a speech to speech stack adjudicable at all. Verified
accepting a valid turn and rejecting an empty one with HTTP 400. Closes brief
audit gap 4, which the brief called necessary rather than optional.

## 4. Audio citation, end to end

Synthesized turn of 11.32 seconds, transcribed to 35 word tokens, adjudicated on
text alone, then clipped per claim.

| Claim | Characters | Word tokens | Audio | Clip |
|---|---|---|---|---|
| "I can have this removed from your credit report entirely." | [156:213] | 10 | 8.33s to 11.27s | 2.94s of 11.32s |
| "four thousand five hundred dollars" | [110:144] | 5 | 5.69s to 7.51s | 1.82s |
| "today" | [145:150] | 1 | 7.21s to 8.23s | 1.02s |

The clip is the sentence, not the recording. That is the whole point of SPEC
section 8, and the durations above are the evidence for it.

Every clip is content addressed, so the evidence log references it by digest and
a report can claim the clip has not been altered since the finding was written.

## 5. Design decisions worth recording

**The proxy is transparent and stays out of the decision path.** Responses are
returned unmodified, adjudication happens on a worker thread after the response
is sent, and a capture failure never becomes a request failure. Upstream rate
limited during testing and the proxy passed the 429 through untouched, which is
correct: swallowing upstream state would hide a real condition from the client's
own retry logic. Retry belongs in the client, so pacing and backoff live in the
driver script.

**The capture queue is bounded at 256 and drops rather than blocks.** Losing an
adjudication is a gap in a pre-deployment report. Blocking a live call is an
outage, and the brief is explicit that the first dropped call attributable to
the tool loses the account.

**The transcript is assembled from word tokens rather than parsed after the
fact.** Deepgram returns a joined transcript string as well, but locating words
inside a string somebody else assembled means re-deriving positions that were
already known. Building the string here records every token's character span at
the moment it is formed, so claim offsets resolve to word tokens by interval
overlap with no fuzzy matching anywhere. Fuzzy matching fails hardest on hedged,
disfluent speech, which is exactly where the liability sits.

**Model identifiers were read from the live API, not from the brief.** The brief
says Aura-2. There is no bare `aura-2` model: TTS requires a named voice, and
this build uses `aura-2-asteria-en`. STT reports canonically as
`nova-3-general`, accepting `nova-3` as an alias. Verifying rather than
hardcoding caught a wrong identifier before it reached a demo.

## 6. Limitations

**Synthesized speech is cleaner than a real call.** The offset to timestamp
machinery is exercised correctly, but disfluency, interruption and overlap are
not. This is the ASR degradation delta the brief defers, and this phase does not
close it.

**The numeric confidence rule has reduced coverage.** SPEC section 8 routes a
numeric token below the confidence floor to abstention. The rule is implemented
and unit tested, but on this run it reported no numeric tokens at all, because
`smart_format` is deliberately off so the transcript quotes the call verbatim,
and with it off Nova-3 renders "four thousand five hundred dollars" as words
rather than digits. Verbatim quoting and digit-level confidence gating pull in
opposite directions. The rule fires only when the speaker's numbers are
transcribed as digits, and that is narrower than section 8 implies.

**The demo turn produced four abstentions and no findings.** Consistent with
Phase 1: this is the credit report deletion claim, the same case that abstains
as fixture fx-027, where the governing rule is a general prohibition rather than
a provision naming the conduct. The audio path is not the cause and the
adjudication behaviour is unchanged from Phase 1, which is correct, because
CLAUDE.md decision 9 fixes the backend for a scored run.

## 7. Artifacts

| Path | Contents |
|---|---|
| `adapter/proxy.py` | OpenAI-compatible capture proxy, transcript ingest, metrics |
| `adapter/capture.py` | Bounded out of band capture queue, `agent.turn` span |
| `engine/audio.py` | Synthesis, transcription, offset mapping, clip extraction |
| `scripts/run_proxy.py` | Start the proxy, with or without adjudication |
| `scripts/drive_proxy.py` | Scripted client and overhead measurement |
| `scripts/audio_demo.py` | The end to end audio run reported above |
| `runs/audio-demo/` | Source wav, four clips, evidence chain |

Test suite: 66 passing, including 11 new offset mapping tests. Evidence chain
verifies on write and on reload, carrying seven span types including
`agent.turn` and `finding.emit`, both declared in Phase 1 and first emitted here.
