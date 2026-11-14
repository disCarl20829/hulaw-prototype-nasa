import { useEffect, useState, type FormEvent } from "react";
import { lastCompletedMonth, MIN_BASELINE_YEAR, MIN_END_MONTH, monthsEnding, resolvePeriod, validatePeriod } from "../services/hulaw-api";
import type { AppliedPeriod, DataQuery } from "../types";

interface Props {
  applied: AppliedPeriod;     // the period currently shown in the data
  isDefault: boolean;         // true when no custom period is set
  busy?: boolean;             // data is loading
  onApply: (query: DataQuery) => void;
}

/** Chooses the 12-month period and the baseline years. Applying reloads the data for every page. */
export default function DateRangeControls({ applied, isDefault, busy = false, onApply }: Props) {
  const [endMonth, setEndMonth] = useState(applied.endMonth);
  const [start, setStart] = useState(String(applied.baselineStart));
  const [end, setEnd] = useState(String(applied.baselineEnd));
  const [baselineTouched, setBaselineTouched] = useState(!isDefault);
  const [error, setError] = useState<string | null>(null);

  // Follow the applied period when it changes elsewhere (another page, reset, new data).
  useEffect(() => {
    setEndMonth(applied.endMonth); setStart(String(applied.baselineStart)); setEnd(String(applied.baselineEnd));
    setBaselineTouched(!isDefault); setError(null);
  }, [applied.endMonth, applied.baselineStart, applied.baselineEnd, isDefault]);

  function changeEndMonth(value: string) {
    setEndMonth(value); setError(null);
    // Until the baseline is edited by hand, keep it as the 5 years before the chosen period.
    if (!baselineTouched && /^\d{4}-\d{2}$/.test(value)) {
      const next = resolvePeriod({ endMonth: value });
      setStart(String(next.baselineStart)); setEnd(String(next.baselineEnd));
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const draft: AppliedPeriod = { endMonth, baselineStart: Number(start), baselineEnd: Number(end) };
    const problem = validatePeriod(draft);
    if (problem) { setError(problem); return; }
    const standard = resolvePeriod({});
    const same = draft.endMonth === standard.endMonth && draft.baselineStart === standard.baselineStart && draft.baselineEnd === standard.baselineEnd;
    onApply(same ? {} : draft);
  }

  const span = /^\d{4}-\d{2}$/.test(endMonth) ? monthsEnding(endMonth) : null;
  const changed = endMonth !== applied.endMonth || Number(start) !== applied.baselineStart || Number(end) !== applied.baselineEnd;

  return <form className="panel date-range-panel" aria-label="Period and baseline controls" onSubmit={submit}>
    <div className="date-range-heading"><div><span className="eyebrow">REFERENCE PERIOD</span><h3>Period and baseline</h3></div><span className={`date-range-status ${isDefault ? "" : "custom"}`}>{isDefault ? "LATEST" : "CUSTOM"}</span></div>
    <div className="date-range-fields">
      <fieldset><legend>Period (12 months)</legend>
        <label>Last month<input type="month" value={endMonth} min={MIN_END_MONTH} max={lastCompletedMonth()} onChange={(e) => changeEndMonth(e.target.value)} required /></label>
        <span className="date-range-hint">{span ? `${span[0]} to ${span[11]}` : "Choose a month"}</span>
      </fieldset>
      <fieldset><legend>Baseline years</legend>
        <label>From<input type="number" inputMode="numeric" min={MIN_BASELINE_YEAR} max={2100} step={1} value={start} onChange={(e) => { setStart(e.target.value); setBaselineTouched(true); setError(null); }} required /></label>
        <label>To<input type="number" inputMode="numeric" min={MIN_BASELINE_YEAR} max={2100} step={1} value={end} onChange={(e) => { setEnd(e.target.value); setBaselineTouched(true); setError(null); }} required /></label>
      </fieldset>
    </div>
    {error && <p className="date-range-error" role="alert">{error}</p>}
    <div className="date-range-actions">
      <button type="submit" disabled={busy || !changed}>{busy ? "Loading…" : "Apply"}</button>
      <button type="button" className="secondary" disabled={busy || isDefault} onClick={() => onApply({})}>Reset to latest</button>
    </div>
    <p className="note">Rainfall and vegetation are compared with the same months in the baseline years (3 to 10 years). Soil wetness always uses the 20 years before the period.</p>
  </form>;
}
