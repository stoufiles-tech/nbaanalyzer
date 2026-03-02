import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api";
import type { Player, SimPlayer, ProjectionResult, ProjectionYear } from "../api";
import { fmtSalary } from "../utils";

interface Props {
  teamId: string;
  players: Player[];
}

const SEASONS = ["2025-26", "2026-27", "2027-28"];

const capStatusStyle = (yr: ProjectionYear): React.CSSProperties => {
  if (yr.over_second_apron) return { color: "#7c3aed", fontWeight: 700 };
  if (yr.over_first_apron)  return { color: "#ef4444", fontWeight: 700 };
  if (yr.over_luxury_tax)   return { color: "#f97316", fontWeight: 700 };
  if (yr.over_cap)          return { color: "#eab308", fontWeight: 700 };
  return { color: "#22c55e", fontWeight: 700 };
};

const capLabel = (yr: ProjectionYear) => {
  if (yr.over_second_apron) return "Over 2nd Apron";
  if (yr.over_first_apron)  return "Over 1st Apron";
  if (yr.over_luxury_tax)   return "Luxury Tax";
  if (yr.over_cap)          return "Over Cap";
  return `${fmtSalary(yr.cap_space)} space`;
};

const emptySign = (): SimPlayer => ({
  full_name: "", salary_year1: 0, salary_year2: 0, salary_year3: 0,
});

export default function CapProjection({ teamId, players }: Props) {
  const [released, setReleased] = useState<Set<string>>(new Set());
  const [signedPlayers, setSignedPlayers] = useState<SimPlayer[]>([]);
  const [form, setForm] = useState<SimPlayer>(emptySign());
  const [showForm, setShowForm] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.projectTeam(teamId, { sign: signedPlayers, release: Array.from(released) }),
  });

  // Run projection automatically when params change
  const result: ProjectionResult | undefined = mutation.data;

  const runProjection = () => mutation.mutate();

  const toggleRelease = (name: string) => {
    setReleased((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const addSigning = () => {
    if (!form.full_name.trim() || form.salary_year1 <= 0) return;
    setSignedPlayers((p) => [...p, { ...form }]);
    setForm(emptySign());
    setShowForm(false);
  };

  const removeSigning = (idx: number) =>
    setSignedPlayers((p) => p.filter((_, i) => i !== idx));

  const fmtInput = (val: number) =>
    val > 0 ? String(Math.round(val / 1_000_000)) : "";

  const parseSalary = (s: string) => {
    const n = parseFloat(s.replace(/[^0-9.]/g, ""));
    return isNaN(n) ? 0 : n * 1_000_000;
  };

  return (
    <div className="cap-projection">
      <div className="proj-header">
        <h3>Cap Projections</h3>
        <span className="proj-note">3-year outlook · future cap thresholds held constant</span>
      </div>

      {/* ── Simulation Controls ──────────────────────────────────────── */}
      <div className="proj-controls">
        <div className="proj-controls-left">
          <div className="proj-section-label">Release Players</div>
          <div className="release-chips">
            {players
              .filter((p) => p.salary > 0)
              .sort((a, b) => b.salary - a.salary)
              .map((p) => (
                <button
                  key={p.full_name}
                  className={`release-chip ${released.has(p.full_name) ? "released" : ""}`}
                  onClick={() => toggleRelease(p.full_name)}
                  title={fmtSalary(p.salary)}
                >
                  {p.full_name.split(" ").slice(-1)[0]}
                  {released.has(p.full_name) ? " ✕" : ""}
                </button>
              ))}
          </div>
        </div>

        <div className="proj-controls-right">
          <div className="proj-section-label">Signings</div>
          {signedPlayers.map((sp, i) => (
            <div key={i} className="signed-chip">
              <span>{sp.full_name}</span>
              <span className="signed-chip-sal">
                {fmtSalary(sp.salary_year1)}
                {sp.salary_year2 > 0 && ` / ${fmtSalary(sp.salary_year2)}`}
                {sp.salary_year3 > 0 && ` / ${fmtSalary(sp.salary_year3)}`}
              </span>
              <button className="signed-chip-remove" onClick={() => removeSigning(i)}>✕</button>
            </div>
          ))}

          {showForm ? (
            <div className="sign-form">
              <input
                className="sign-input sign-name"
                placeholder="Player name"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
              <div className="sign-salaries">
                {(["salary_year1", "salary_year2", "salary_year3"] as const).map((key, yi) => (
                  <input
                    key={key}
                    className="sign-input sign-sal"
                    placeholder={`Yr ${yi + 1} ($M)`}
                    value={fmtInput(form[key])}
                    onChange={(e) => setForm({ ...form, [key]: parseSalary(e.target.value) })}
                  />
                ))}
              </div>
              <div className="sign-form-btns">
                <button className="btn-primary" onClick={addSigning}>Add</button>
                <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <button className="btn-add-signing" onClick={() => setShowForm(true)}>
              + Sign a Player
            </button>
          )}
        </div>
      </div>

      <button
        className="btn-run-projection"
        onClick={runProjection}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Calculating…" : "Run Projection"}
      </button>

      {/* ── Results ──────────────────────────────────────────────────── */}
      {result && (
        <>
          {result.is_repeater && (
            <div className="repeater-banner">
              ⚠ Repeater taxpayer — enhanced luxury tax rates apply
            </div>
          )}

          <div className="proj-years">
            {SEASONS.map((season) => {
              const yr = result.years[season];
              if (!yr) return null;
              return (
                <div key={season} className="proj-year-col">
                  <div className="proj-year-header">
                    <div className="proj-year-label">{season}</div>
                    <div className="proj-year-total">{fmtSalary(yr.total_salary)}</div>
                    <div className="proj-year-status" style={capStatusStyle(yr)}>
                      {capLabel(yr)}
                    </div>
                  </div>

                  {/* Tax bill */}
                  {yr.is_taxpayer && (
                    <div className="proj-tax-row">
                      <div className="proj-tax-label">
                        Luxury Tax Bill
                        <button
                          className="btn-breakdown"
                          onClick={() =>
                            setShowBreakdown(showBreakdown === season ? null : season)
                          }
                        >
                          {showBreakdown === season ? "▲" : "▼"}
                        </button>
                      </div>
                      <div className="proj-tax-amount">{fmtSalary(yr.tax_bill)}</div>
                      <div className="proj-tax-sub">
                        {fmtSalary(yr.tax_amount_over)} over threshold ·{" "}
                        {(yr.tax_effective_rate * 100).toFixed(1)}¢ per $1
                      </div>

                      {showBreakdown === season && (
                        <table className="bracket-table">
                          <thead>
                            <tr>
                              <th>Bracket ($)</th>
                              <th>Rate</th>
                              <th>Tax</th>
                            </tr>
                          </thead>
                          <tbody>
                            {yr.bracket_breakdown.map((b, i) => (
                              <tr key={i}>
                                <td>{fmtSalary(b.taxable)}</td>
                                <td>${b.rate.toFixed(2)}/$1</td>
                                <td>{fmtSalary(b.tax)}</td>
                              </tr>
                            ))}
                            <tr className="bracket-total">
                              <td>Total</td>
                              <td></td>
                              <td>{fmtSalary(yr.tax_bill)}</td>
                            </tr>
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}

                  {/* Player list */}
                  <div className="proj-player-list">
                    {yr.players.map((p) => (
                      <div
                        key={p.full_name}
                        className={`proj-player-row ${p.is_new ? "proj-player-new" : ""}`}
                      >
                        <span className="proj-player-name">{p.full_name}</span>
                        <span className="proj-player-pos">{p.position}</span>
                        <span className="proj-player-sal">{fmtSalary(p.salary)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="proj-year-footer">
                    {yr.player_count} players · {fmtSalary(yr.total_salary)}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
