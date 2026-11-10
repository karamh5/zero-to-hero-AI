# zero-to-hero-AI

This is where I build things with AI — real projects, end to end, each one a
step past the last. Some are small experiments, some turn into full systems
with actual hardware behind them. All of it lives here, organized by project,
as a running record of what I've built and how I got there.

Each project gets its own folder with its own README — go in for the details,
the architecture, the numbers. This top-level page is just the front door.


                      ,i1i1t1;i1t1i.                        karam@hammouda ────────────────────────
                .,,;f8@80GCC00080LG0t11i;:.                 School .... UBC · CompE '27
             ,;LGC080CG8@@@0G0@@@880008@808C,               Intern .... Hexaware · AI Engineer
          .L8880G0GC0@@@@@@@@@8@@@@@880GG8800G;             Thesis .... quantized physical AI
         ;088888@88@@@@@@@@@800@@@@@@888@@@88088C;          Measure ... accuracy·latency·energy
       i0@00@@@808@@@@@@@@@8@@@@@@@@@@8@@88800000t          ─ Shipped ──────────────────────────────
      :808808@@@@@@@@@@@@@@@@@@@@@@@@@@@@@808@@88f,         Edge RL ... distilled INT8/INT4 on Pi
     ,C808@@8@@@@@88@@008@@@@@@@@@@@888@@@@@@@@8888L,       Vision .... YOLO teacher → student
     t@@88@@@@8LfLCCCCGG88G08008@GC000G0CC0@@@@@@@80:       Quantum ... hybrid quantum head
     :L@@@@@@@Li11ii11fLftffCGGCf111i;;ii1L8@@@@@8@t        Robotics .. RoboStrike CV <50 ms
       t@@@@8tL088@@88800LtttttfCCGG00GG0C1L@@@@@0f.        Photonics . hBN coupler surrogate
        iL8@1,;iifLCGGGGGCt111fCGGGGCftt1tii0@@@@i          Security .. Dirty Pipe CVE-2022-0847
         ;LL;:1LG00@@8880fii1;tC088@@@CGC1;:fGfi            Hardware .. thermal tire marker
         :Lf::i;1tffffff1;i1i;;itfLLLLf1ii;:tf              Agents .... self-improving loop + RAG
          :f;:ii1tttt11ii;iii;;;ii11111iii:1i               ─ Stack ────────────────────────────────
           :ii;ii1i1tf1i111t1;ii;1t1iiiiii;i,               Languages . Python · TS · C++
             ;t;;;i1111tCCLLffCL1i1111ii;i:                 ML ........ PyTorch · SB3 · LangGraph
             :fiiiiLCCLLLLLLCLLLLLLfiiiiif,                 Edge ...... Jetson · Pi · ROS2 · ONNX
              ;L1tfC0GCCCGGGGGGCLLGCft11f:                  Web ....... FastAPI · React · AWS
               :LtfLftttfffffft1ttfLf1tf,                   ─ Find me ──────────────────────────────
               ,1LCCCLffLG080CLffLLCGL1i                    GitHub .... karamh5
               

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
