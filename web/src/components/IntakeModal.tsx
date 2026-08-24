import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ModalDialog from "./ModalDialog";
import { api, IntakePayload } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { bblError, binError, boroughFromBbl, digitsOnly } from "../lib/nyc";

const EMPTY_FORM: IntakePayload = {
  address: "",
  bbl: "",
  bin: "",
  work_type: "",
  owner: "",
  borough: "",
  packet_text: "",
};

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

export default function IntakeModal({ open, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<IntakePayload>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const boroughLocked = Boolean(boroughFromBbl(form.bbl));

  useEffect(() => {
    if (!open) return;
    setForm(EMPTY_FORM);
    setError(null);
    setLoading(false);
    const timer = window.setTimeout(() => firstFieldRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [open]);

  const onBbl = (raw: string) => {
    const bbl = digitsOnly(raw).slice(0, 10);
    setForm({ ...form, bbl, borough: boroughFromBbl(bbl) ?? form.borough });
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
        Packet text is PII-redacted before storage. BBL first digit fills borough (1–5).
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
          <input
            ref={firstFieldRef}
            id="intake-address"
            required
            className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
        </div>
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
