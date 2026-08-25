import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ModalDialog from "./ModalDialog";
import { useToast } from "./Toast";
import { api, AddressMatch, IntakePayload } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { BOROUGH_BY_DIGIT, bblError, binError, boroughFromBbl, digitsOnly } from "../lib/nyc";

const EMPTY_FORM: IntakePayload = {
  address: "",
  bbl: "",
  bin: "",
  work_type: "",
  owner: "",
  borough: "",
  packet_text: "",
};

const BOROUGH_OPTIONS = Object.values(BOROUGH_BY_DIGIT);

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Could not read the plan PDF"));
        return;
      }
      const base64 = result.split(",", 2)[1];
      if (!base64) {
        reject(new Error("Could not encode the plan PDF"));
        return;
      }
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Could not read the plan PDF"));
    reader.readAsDataURL(file);
  });
}

export default function IntakeModal({ open, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const { push } = useToast();
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<IntakePayload>(EMPTY_FORM);
  const [lookupBorough, setLookupBorough] = useState("Manhattan");
  const [matches, setMatches] = useState<AddressMatch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const boroughLocked = Boolean(boroughFromBbl(form.bbl));

  useEffect(() => {
    if (!open) return;
    setForm(EMPTY_FORM);
    setMatches([]);
    setError(null);
    setLoading(false);
    setLookupLoading(false);
    const timer = window.setTimeout(() => firstFieldRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [open]);

  const onBbl = (raw: string) => {
    const bbl = digitsOnly(raw).slice(0, 10);
    setForm({ ...form, bbl, borough: boroughFromBbl(bbl) ?? form.borough });
  };

  const applyMatch = (match: AddressMatch) => {
    setForm((current) => ({
      ...current,
      address: match.address,
      bbl: match.bbl,
      bin: match.bin || current.bin,
      borough: match.borough,
      owner: match.owner || current.owner,
    }));
    setMatches([]);
    push(`BBL ${match.bbl} filled from NYC Open Data (PLUTO).`, "success");
  };

  const lookupAddress = async () => {
    if (!form.address.trim()) {
      setError("Enter a street address before lookup.");
      return;
    }
    setLookupLoading(true);
    setError(null);
    setMatches([]);
    try {
      const result = await api.resolveAddress(form.address.trim(), lookupBorough);
      setMatches(result.matches);
      if (result.matches.length === 1) applyMatch(result.matches[0]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLookupLoading(false);
    }
  };

  const onPlanFile = async (file: File | null) => {
    if (!file) {
      setForm({ ...form, plan_filename: null, plan_content_type: null, plan_pdf_base64: null });
      return;
    }
    if (file.type !== "application/pdf") {
      setError("Plan upload must be a PDF file.");
      return;
    }
    try {
      const base64 = await readFileAsBase64(file);
      setForm({
        ...form,
        plan_filename: file.name,
        plan_content_type: file.type,
        plan_pdf_base64: base64,
      });
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const bblIssue = bblError(form.bbl);
    const binIssue = binError(form.bin ?? "");
    if (bblIssue || binIssue) {
      setError(bblIssue ?? binIssue);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const created = await api.intake({
        ...form,
        borough: form.borough || boroughFromBbl(form.bbl) || null,
      });
      push(`Case created for ${created.address}. Distribution is running.`, "success");
      onClose();
      onCreated?.();
      navigate(`/cases/${created.id}?tab=distribution&from=tasks`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalDialog open={open} title="New permit intake" onClose={onClose}>
      <p className="text-sm text-slate-600 -mt-2 mb-3">
        Look up the address on NYC Open Data (PLUTO) or enter BBL manually. Packet text is PII-redacted before storage.
      </p>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2 mb-3" role="alert">
          {error}
        </p>
      )}
      <form className="space-y-3" onSubmit={submit}>
        <div>
          <label htmlFor="intake-address" className="block text-sm font-medium text-slate-700">
            Address
          </label>
          <div className="mt-1 flex flex-col sm:flex-row gap-2">
            <input
              ref={firstFieldRef}
              id="intake-address"
              required
              className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
            <select
              aria-label="Borough for address lookup"
              className="border border-pp-border rounded-md px-3 py-2 text-sm"
              value={lookupBorough}
              onChange={(e) => setLookupBorough(e.target.value)}
            >
              {BOROUGH_OPTIONS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={lookupLoading}
              onClick={lookupAddress}
              className="px-3 py-2 text-sm rounded-md border border-pp-border whitespace-nowrap disabled:opacity-50"
            >
              {lookupLoading ? "Looking up…" : "Look up BBL"}
            </button>
          </div>
        </div>
        {matches.length > 1 && (
          <ul className="rounded-md border border-pp-border bg-slate-50 text-sm divide-y divide-pp-border">
            {matches.map((match) => (
              <li key={match.bbl}>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 hover:bg-white"
                  onClick={() => applyMatch(match)}
                >
                  {match.address} · BBL {match.bbl}
                  {match.bin ? ` · BIN ${match.bin}` : ""}
                  {match.zoning_district ? ` · ${match.zoning_district}` : ""}
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label htmlFor="intake-bbl" className="block text-sm font-medium text-slate-700">
              BBL (10 digits)
            </label>
            <input
              id="intake-bbl"
              required
              inputMode="numeric"
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm font-mono"
              value={form.bbl}
              onChange={(e) => onBbl(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="intake-bin" className="block text-sm font-medium text-slate-700">
              BIN (optional, 7 digits)
            </label>
            <input
              id="intake-bin"
              inputMode="numeric"
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm font-mono"
              value={form.bin}
              onChange={(e) => setForm({ ...form, bin: digitsOnly(e.target.value).slice(0, 7) })}
            />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label htmlFor="intake-owner" className="block text-sm font-medium text-slate-700">
              Owner
            </label>
            <input
              id="intake-owner"
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
              value={form.owner ?? ""}
              onChange={(e) => setForm({ ...form, owner: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="intake-borough" className="block text-sm font-medium text-slate-700">
              Borough
            </label>
            <input
              id="intake-borough"
              readOnly={boroughLocked}
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm read-only:bg-slate-50"
              value={form.borough ?? ""}
              onChange={(e) => setForm({ ...form, borough: e.target.value })}
            />
            {boroughLocked && <p className="mt-1 text-xs text-slate-500">Filled from BBL borough digit.</p>}
          </div>
        </div>
        <div>
          <label htmlFor="intake-work" className="block text-sm font-medium text-slate-700">
            Work type
          </label>
          <input
            id="intake-work"
            required
            className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
            value={form.work_type}
            onChange={(e) => setForm({ ...form, work_type: e.target.value })}
          />
        </div>
        <div>
          <label htmlFor="intake-packet" className="block text-sm font-medium text-slate-700">
            Applicant packet
          </label>
          <textarea
            id="intake-packet"
            className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm min-h-24"
            placeholder="SSN, email, and phone will be redacted automatically."
            value={form.packet_text}
            onChange={(e) => setForm({ ...form, packet_text: e.target.value })}
          />
        </div>
        <div>
          <label htmlFor="intake-plan" className="block text-sm font-medium text-slate-700">
            Plan PDF (optional)
          </label>
          <input
            id="intake-plan"
            type="file"
            accept="application/pdf"
            className="mt-1 block w-full text-sm text-slate-600"
            onChange={(e) => void onPlanFile(e.target.files?.[0] ?? null)}
          />
          {form.plan_filename && (
            <p className="mt-1 text-xs text-slate-500">Attached: {form.plan_filename}</p>
          )}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-md border border-pp-border">
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm rounded-md bg-pp-accent text-white disabled:opacity-50"
          >
            {loading ? "Running distribution…" : "Create case"}
          </button>
        </div>
      </form>
    </ModalDialog>
  );
}
