================ ECHOPROOF ================
================ FINAL DEMO SCRIPT ================

Target: 10 minutes. Slides about 6, walkthrough about 3, close about 1.
Every click marker below is verified against a real build step in deck.html.
Grouped reveals fire on ONE press and settle in sequence, so there is no
drumming on the space bar.

---------------- BEFORE YOU START ----------------

[RUN .VENV/SCRIPTS/PYTHON SCRIPTS/RUN_UI.PY]

[OPEN HTTP://127.0.0.1:8077/RIG IN TAB ONE]

[UNDER 02 / SELECT CONVERSATION, GROUP SUPPORTED, CLICK 04 VALIDATION NOTICE CONTENTS DESCRIBED]

[TYPE WARM UP IN THE ASSESSMENT TITLE BOX, CLICK RUN ADJUDICATION, LET IT FINISH]

[OPEN PRESENTATION/DEMO-DAY/DECK.HTML IN TAB TWO, PRESS F FOR FULLSCREEN]

[OPEN HTTP://127.0.0.1:8077/BENCH IN TAB THREE, CHECK THE TOP CARD READS THIRD PARTY DISCLOSURE - DEMO BASELINE]

---------------- OPENING (0:00) ----------------

[SLIDE 1: CLICK 1X]

Thanks Erik.

Like Erik said, this is EchoProof. It has been my foundational project this
summer at Hexaware and I am excited to get right into it.

So here is something true about every voice AI agent, no matter who built it.
You can swap the speech vendor. You can swap the voice. But somewhere in the
middle there is a language model deciding what to actually say to the customer.
That model is the part that can break a rule. And it is the one piece every
stack has in common.

In regulated AI, being right is not enough. You have to be able to prove you
were right.

I learned that interning in compliance at TELUS.

And today THAT proof is produced by people, manually, across hundreds of
conversations.

That is the bottleneck. [CLICK 1X]

---------------- THE BOTTLENECK (1:15) ----------------

[CLICK 1X]

The proof is the part that is missing.

[CLICK 1X]

Deployment stalls right here, because Quality Assurance has to sign their name
to a document saying this agent is safe, and there is no consistent framework
sitting behind that signature.

The constraint is not capability. It is proof.

EchoProof came out of multiple rounds of iteration with stakeholders, including
validation from an applied engineer at Deepgram and several working sessions
with Roger in customer experience.

Two common problems stood out.

First being coverage, because nobody can listen to every conversation on file.
And the second is evidence, because a score in a spreadsheet is not something
you hand a regulator.

Each of those adds weeks to agent rollout, and here is how things are typically
done today. [CLICK 1X]

---------------- WHAT THEY DO TODAY (2:00) ----------------

[CLICK 1X]

Industry benchmarks put quality review somewhere between one and five percent
of calls.

[CLICK 1X]

One analyst gets through a handful of conversations a day. So most of what your
agent says is never fully examined by anyone.

[CLICK 1X]

That is a manual process, and something EchoProof can automate. [CLICK 1X]

---------------- WHAT IT IS (2:30) ----------------

[SLIDE 4: CLICK 1X]

What goes in is a transcript of a test conversation the agent already had. What
comes out is a verdict on every line the agent said, with the exact rule quoted
next to it. It is a pre-deployment check. It runs before anything goes live.

In just four steps. It reads what the agent said. It pulls out each claim. It
finds the one rule in the client's own policy documents that governs that claim.
Then it rules, and seals the record.

Now, the next few slides are the reasons you can trust that output. [CLICK 1X]

---------------- THE ISOLATION BOUNDARY (3:30) ----------------

[CLICK 1X]

Retrieval searches the client's rulebook by evaluating keywords and meaning of
the claims.

[CLICK 1X]

It pulls out exactly one policy and pairs it with one claim.

[CLICK 1X]

Then you have the fence. That pair is everything the judge ever sees. Not the
full corpus, and not even the model's own training knowledge.

This brings us to. [CLICK 1X]

---------------- THE FIVE STATES (4:00) ----------------

[CLICK 1X]

The verdicts. Supported and contradicted, are the two that decide the outcome.

[CLICK 1X]

And these three verdicts are scenarios where the model itself refuses to judge
them, this can be due to no policies governing a certain claim, or the judge
unwilling to give a false positive.

Those three route to a human reviewer, and they are separate from findings in
the system. [CLICK 1X]

---------------- EVIDENCE AND TRACEABILITY (4:30) ----------------

[CLICK 1X]

Traceability. So every search and every finding writes a record into a linked
log.

[CLICK 1X]

This is what happens when somebody edits an entry in the middle. Every link
after it breaks. You cannot discretely change this record, only visibly destroy
it.

That gives you traceability of the decision itself, not only of the model.
[CLICK 1X]

---------------- AUDIO AS EVIDENCE (5:00) ----------------

[CLICK 1X]

The audio component of EchoProof is the speech to text running through
Deepgram, which returns timestamps.

[CLICK 1X]

And that slices the source audio, so the reviewer hears the eight seconds that
matter instead of scrubbing a twelve minute recording. This is done because if
the transcription ever gets it wrong, the QA can simply listen to the raw audio
to verify it themselves.

Now with regards to the stack. [CLICK 1X]

---------------- THE STACK (5:30) ----------------

[CLICK 1X]

The top layer is the customer's voice agent. Deepgram, or any other vendor,
handles speech to text.

[CLICK 1X]

In the middle layer is EchoProof. It is a standardized endpoint, which just
means it plugs into whatever stack a customer already runs.

[CLICK 1X]

And the bottom layer is the engine. Where the judge monitors off to the side.

And every vendor in that top layer is swappable. The attachment point does not
move, so nothing gets rebuilt to accommodate it.

That is the theory. Now this is all easier to show than to describe so let us
head to the user interface.

---------------- THE WALKTHROUGH (6:00) ----------------

[ALT TAB TO THE BROWSER]

[YOUR UI WALKTHROUGH GOES HERE. HOME PAGE, THEN RIG, THEN BENCH, THEN CORPUS.]

[WHEN YOU ARE DONE, ALT TAB BACK TO THE DECK]

That is the product. Here is where it goes. [CLICK 1X]

---------------- ROADMAP (8:45) ----------------

[CLICK 1X]

Today, it diagnoses. It finds the violation, it cites the rule that governs it,
and it seals the evidence. That is what you just saw, and it is deliberately
narrow, because compliance against a client's own rulebook is the part nobody
filled.

[CLICK 1X]

Next, it repairs. Instead of testing a scripted handful of conversations, it
searches thousands of paths looking for the ones that break. Then it does not
just flag the bad line, it rewrites the agent's instructions to kill that whole
class of problem, and re runs everything to prove the fix held and nothing else
broke.

[CLICK 1X]

Then it compounds. Every violation ever found becomes a permanent test case, so
every client makes the next client's launch safer. And eventually the rulebook
itself generates the guardrails, which means agents start compliant instead of
being tested into compliance.

[CLICK 1X]

Which is the interesting part long term. It stops being a report you read, and
becomes a loop that keeps making the next agent better than the last one.
[CLICK 1X]

---------------- MARKET AND COST (9:15) ----------------

[CLICK 1X]

The voice AI market is around 3.5 billion this year, and forecasts near 35
billion by 2033. And with more agents comes more compliance pressure.

[CLICK 1X]

Here is what it actually costs to run. The measured campaign was eighteen calls
for eighty two cents in model spend, projecting to roughly twenty three dollars
per hundred calls.

So model spend is not the constraint here. Access is, because we need the
client's authorization to test against their policies.

This also raises the question of who else is doing this. [CLICK 1X]

---------------- COMPETITIVE (9:30) ----------------

[CLICK 1X]

The closest product is OpenAI Presence. It is a strong product, but it is end to
end, which means the vendor supplying the agent also supplies the grade. That is
a self assessment.

EchoProof works across mixed stacks where the speech layer and the model come
from different vendors, which is what most real enterprise deployments look
like, especially when factoring in economics, budget and existing partnerships.
[CLICK 1X]

---------------- CLOSE (9:45) ----------------

[CLICK 1X]

So, as a result. A review that took two weeks takes minutes. It covers every
turn instead of only a handful. And at the end you are holding an evidence file
with a citation on every line.

I think governance is the thing standing between these deployments and revenue.

I know you will each have your own read on it. So I would like to end here and I
would love to hear any of your thoughts and questions.

[STOP TALKING]

---------------- IF SOMETHING GOES WRONG ----------------

---- THE BENCH WILL NOT LOAD ----

[CHECK THE TERMINAL IS STILL RUNNING RUN_UI.PY]

[RELOAD THE PAGE]

If it does not come back, go back to the deck and close from the last slide.
Say this.

That runs live on this laptop and I am not going to debug it in front of you.
Everything I described is on disk and I will walk anyone through it afterwards.

---- A SCREEN RENDERS HALF WAY ----

[HARD RELOAD WITH CONTROL SHIFT R]

Keep talking through the reload. Do not narrate it.

---- A LIVE RUN IS STILL GOING WHEN YOU COME BACK ----

Do not wait for it. Switch to the bench and open the stored baseline. Say that
it is a live model call on a laptop CPU, that about two minutes a conversation
is expected, and that it is the first thing production fixes.
