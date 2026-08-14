/** The reference library: browsable provisions with retrieval coverage.
 *
 * Counts, identifiers and the hierarchy convention all come from the pack.
 * The policy gap list here contains ONLY no_governing_rule claims, labelled
 * as candidates for a rulebook gap: a judge rejecting its shortlist is a
 * retrieval failure and never appears in this list.
 */

import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { RevealLines } from "../components/Reveal";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../lib/useFetch";
import type { PolicySection } from "../types";
import "./corpus.css";

function rootOf(sectionId: string, separators: string[]): string {
  let cut = sectionId.length;
  for (const separator of separators) {
    const at = sectionId.indexOf(separator);
    if (at >= 0 && at < cut) cut = at;
  }
  return sectionId.slice(0, cut);
}

export function Corpus() {
  const { packId } = useParams();
  const [params, setParams] = useSearchParams();
  const coverageRun = params.get("run") ?? undefined;
  const navigate = useNavigate();

  const packs = useFetch(() => api.corpusList(), []);
  const activePack = packId ?? packs.data?.packs[0]?.pack_id ?? null;
  const corpus = useFetch(
    () => (activePack ? api.corpus(activePack, coverageRun) : Promise.reject(new Error("no pack"))),
    [activePack, coverageRun],
  );
  const runs = useFetch(() => api.runs(), []);
  const gapSource = useFetch(
    () =>
      coverageRun
        ? api.run(coverageRun).catch(() => null)
        : Promise.resolve(null),
    [coverageRun],
  );

  const [filter, setFilter] = useState("");
  const [obligation, setObligation] = useState<string>("all");

  const grouped = useMemo(() => {
    if (!corpus.data) return [];
    const query = filter.trim().toLowerCase();
    const sections = corpus.data.sections.filter((section) => {
      if (obligation !== "all" && section.obligation_type !== obligation) return false;
      if (!query) return true;
      return (
        section.section_id.toLowerCase().includes(query) ||
        section.verbatim_text.toLowerCase().includes(query) ||
        section.heading.toLowerCase().includes(query)
      );
    });
    const map = new Map<string, PolicySection[]>();
    for (const section of sections) {
      const root = rootOf(section.section_id, corpus.data.hierarchy_separators);
      if (!map.has(root)) map.set(root, []);
      map.get(root)!.push(section);
    }
    return [...map.entries()];
  }, [corpus.data, filter, obligation]);

  if (packs.loading) return <div className="page"><Loading what="policy packs" /></div>;
  if (packs.error) return <div className="page"><ErrorState error={packs.error} retry={packs.retry} /></div>;
  if (!packs.data || packs.data.packs.length === 0) {
    return (
      <div className="page">
        <RevealLines as="h1" className="corpus-display" lines={["GOVERNING", "CORPUS"]} />
        <Empty
          label="no policy pack built"
          detail="Build one from the live eCFR API with: python scripts/build_policy_pack_ecfr.py"
        />
      </div>
    );
  }

  return (
    <div className="page corpus">
      <header className="corpus-head">
        <RevealLines as="h1" className="corpus-display" lines={["GOVERNING", "CORPUS"]} />
        {corpus.data && (
          <p className="corpus-lede">
            <span className="mono">{corpus.data.manifest.citation ?? activePack}</span>
            {" · "}
            {corpus.data.sections.length} provisions, verbatim, content-addressed
            at version{" "}
            <span className="mono faint">
              {String(corpus.data.manifest.policy_pack_version ?? "").slice(0, 12)}
            </span>
          </p>
        )}
      </header>

      <div className="corpus-controls">
        {packs.data.packs.length > 1 && (
          <label className="corpus-control">
            <span className="syslabel">pack</span>
            <select
              value={activePack ?? ""}
              onChange={(event) => navigate(`/corpus/${event.target.value}`)}
            >
              {packs.data.packs.map((pack) => (
                <option key={pack.pack_id} value={pack.pack_id}>
                  {pack.pack_id} ({pack.record_count})
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="corpus-control">
          <span className="syslabel">retrieval coverage from run</span>
          <select
            value={coverageRun ?? ""}
            onChange={(event) => {
              const value = event.target.value;
              if (value) setParams({ run: value });
              else setParams({});
            }}
          >
            <option value="">none</option>
            {(runs.data?.runs ?? [])
              .filter((run) => run.chain_ok)
              .map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id}
                </option>
              ))}
          </select>
        </label>
        <label className="corpus-control">
          <span className="syslabel">obligation</span>
          <select value={obligation} onChange={(event) => setObligation(event.target.value)}>
            <option value="all">all</option>
            <option value="prohibition">prohibition</option>
            <option value="requirement">requirement</option>
            <option value="permission">permission</option>
            <option value="definition">definition</option>
          </select>
        </label>
        <label className="corpus-control corpus-search">
          <span className="syslabel">filter</span>
          <input
            className="mono"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="section id or text"
          />
        </label>
      </div>

      {coverageRun && gapSource.data && (
        <section className="corpus-gaps">
          <h2 className="syslabel">
            policy gap list: run {coverageRun}
          </h2>
          {gapSource.data.policy_gap_claims.length === 0 ? (
            <p className="muted">
              Empty for this run. Only a claim where nothing in the corpus
              cleared the retrieval floor may appear here; an empty list means
              retrieval always found something plausible, not that the
              rulebook is complete.
            </p>
          ) : (
            <>
              <p className="muted">
                Claims where nothing in this corpus cleared the retrieval
                floor. Candidates for a rulebook gap, not violations, and not
                judge disagreements.
              </p>
              <ul className="corpus-gaplist">
                {gapSource.data.policy_gap_claims.map((finding) => (
                  <li key={finding.claim_id}>
                    <Link
                      to={`/runs/${coverageRun}/claims/${finding.claim_id}`}
                      className="mono"
                    >
                      {finding.claim_id}
                    </Link>{" "}
                    <span className="muted">{finding.claim_text.slice(0, 140)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {corpus.loading && <Loading what={`packs/policy/${activePack}`} />}
      {corpus.error && <ErrorState error={corpus.error} retry={corpus.retry} />}

      {corpus.data && (
        <div className="corpus-body">
          {grouped.length === 0 ? (
            <Empty label="no provisions match the filter" />
          ) : (
            grouped.map(([root, sections]) => (
              <section key={root} className="corpus-root">
                <h2 className="corpus-root-id mono">{root}</h2>
                <p className="corpus-root-heading muted">
                  {sections[0]?.heading.split(".")[0] ?? ""}
                </p>
                <ol className="corpus-sections">
                  {sections.map((section) => {
                    const coverage = corpus.data!.coverage[section.section_id];
                    return (
                      <li key={section.section_id} className="corpus-section" tabIndex={0}>
                        <div className="corpus-section-head">
                          <span className="mono corpus-section-id">
                            {section.section_id}
                          </span>
                          <span
                            className="syslabel"
                            data-obligation={section.obligation_type}
                          >
                            {section.obligation_type}
                          </span>
                          {coverage && (
                            <span className="mono faint corpus-coverage">
                              retrieved {coverage.retrieved}x
                              {coverage.cited > 0 && ` · cited ${coverage.cited}x`}
                            </span>
                          )}
                        </div>
                        <p className="law corpus-text">{section.verbatim_text}</p>
                        {section.cross_references.length > 0 && (
                          <p className="mono faint corpus-refs">
                            refs {section.cross_references.join("  ")}
                          </p>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </section>
            ))
          )}
        </div>
      )}
    </div>
  );
}
