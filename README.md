# zero-to-hero-AI

This is where I build things with AI — real projects, end to end, each one a
step past the last. Some are small experiments, some turn into full systems
with actual hardware behind them. All of it lives here, organized by project,
as a running record of what I've built and how I got there.

Each project gets its own folder with its own README — go in for the details,
the architecture, the numbers. This top-level page is just the front door.


.                               .:;:;;i1i,,:;;ii;.
                            .1C880GGGCCCGGG088CfC0f...
                      .:i1tLG088808880GCG0008880GGG00GCG00CLf1:                        karam@hammouda ──────────────────────────
                   :ifC0GG0888GCG8@@@@@80G0@@@@@88880008@@80088L;                      School ...... UBC · CompE '27
                1G8880GGG00CC08888@@@@@@@8@@@@@@@@@8880000G0880088t.                   Intern ...... Hexaware · AI Engineer
              i08888088880008@@@@@@@@@@@880008@@@@@@@@80G08@@800GC08Cf;                Thesis ...... quantized physical AI
            ,fGG088@@888@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@8GG08GLL;              Measure ..... accuracy · latency · energy
          iG880888@@@@8088@@@@@@@@@@@@@8@@@@@@@@@@@@@@@8@@@@88888880G80t.
         ;8@G088888@@@@8@@@@@@@@@@@@@@@@@@@@88@@@@@@@@@@@@@@@8888@@@880f:.             ─ Shipped ────────────────────────────────
        .;C008@@8888@@@@@@@@@@@@@@8@@@@@@@@@@@@@@@@88@@@@@@@@@8888@@88880Li,.          Edge RL ..... distilled + INT8/INT4 on a Pi
        C@8808@@@@@@@@8800008@@8GG088@@@88@@@@@@@8@@80GG0@@@@@@@@@@@88800GLi           Vision ...... YOLO teacher → tiny student
       iG@@888@@@@@@8GLfffLLLfLCCG0880GG8@0008@8GLCG000GGGCLC08@@@@@@@@@800f.          Quantum ..... hybrid quantum head, FordA
       :tG@@@@@@@@@@0ft1111111tfLCCLffffCG8800Cfttt111111111fL0@@@@@@@@8@@f,           Robotics .... RoboStrike CV < 50 ms
         .L8@@@@@@@CtfCGGGGGGCCCLLLfftttttttttttttttfttttttt11L8@@@@@@@@8C:            Photonics ... hBN coupler surrogate
           L@@@@@8f1fCCCGG00088888@8GLftttfffC0@@@@@@@@@@8888f1C@@@@@@8L;.             Security .... Dirty Pipe CVE-2022-0847
            ,1C8@G:,iii1tfCGGG00GGCCCft1111tfCCGGGGCLft111iii;;t0@@@@@8t.              Hardware .... thermal marker, mining tires
             :1fCt::itC08008@@@08800Gtii1ii1LCG8888@@@8CCCLti;;iL0Cff,                 Agents ...... self-improving loop + RAG
             ift1;:;iii1tfLCCCCCCCCf1ii11i;;1tfLCGG000GCLLff1i;:1C1.
              ,LC1::iiii11tttftt11iiiii11i;;iii1tttttttt1iii;;;;t1                     ─ Stack ──────────────────────────────────
               ;1i:;iii11ttt11111iii;iiiiii;;;iii11111111iiii:;t;                      Languages ... Python · TypeScript · C++
                ;11i;iii111111tt1;;;;i1tt1i;:;;;1t11iiiiiiiii;i1:                      ML .......... PyTorch · SB3 · LangGraph
                   :ii;iiii11tttttLCCf1tt1ifGCf1111111iiiiii;;,                        Edge ........ Jetson · Pi · ROS2 · ONNX
                   ;f1;;;ii11111tfCGG0GGG0GCCft1ii11111iii;i1:                         Web ......... FastAPI · React · AWS
                   ,11ii1iitCGGCLffffffffffffffLCCGL1iiiiiitt.
                    .tf11ttfC88GCGGG0000GGGGGGCLLLCCfttt1it1,                          ─ Find me ────────────────────────────────
                     :1ftttfLfttttttfffffffftttfffLLftttttt:                           GitHub ...... karamh5
                      .tLLLLCCLfffLCCGGGGCCLffttfffLLtttfi
                      :i1fCCLLLffffLCG000GCLLffLLLLCCCf1ii.


## Projects

- **[WildSense/](WildSense/)** — edge-AI wildfire risk detection on a
  Raspberry Pi. A sensor node that learns its own baseline instead of relying
  on a hardcoded threshold, with a simulated fleet showing how it'd federate
  across many nodes.

- **[EchoProof/](EchoProof/)** — a compliance assurance layer for voice AI
  agents. It takes a transcript of a conversation an agent had,
  pulls the governing rule out of a real policy corpus (Regulation F, 303
  sections, straight from the eCFR API), and issues a verdict with the exact
  section cited, the rule text quoted, and an audio clip of the sentence, all
  in a hash-chained evidence log that renders to a single self-contained HTML
  report. Citation precision runs 0.75 to 0.83, and it produced zero false
  positives on the compliant control across three runs. It is a triage layer
  that routes to human review rather than an unattended release gate, and the
  report says so on its front page. Built as the foundational project of the
  Hexaware AI Launchpad, summer 2026. See `EchoProof/POC-BRIEF.md`.

More projects will land here over time!
