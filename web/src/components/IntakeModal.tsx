import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, IntakePayload } from "../lib/api";
import { errorMessage } from "../lib/errors";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

export default function IntakeModal({ open, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const titleId = useId();
  const [form, setForm] = useState<IntakePayload>({
    address: "",
    bbl: "",
    bin: "",
    work_type: "",
    owner: "",
    borough: "",
    packet_text: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    firstFieldRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await api.intake(form);
      onClose();
      onCreated?.();
      navigate(`/cases/${created.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-30 bg-black/40 flex items-center justify-center p-4" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="text-xl font-semibold text-pp-navy">
          New permit intake
        </h2>
        <p className="text-sm text-slate-600">
          Packet text is PII-redacted before storage. BBL/BIN resolve against live NYC Open Data.
        </p>
        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2" role="alert">
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
                BBL
              </label>
              <input
                id="intake-bbl"
                required
                className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
                value={form.bbl}
                onChange={(e) => setForm({ ...form, bbl: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="intake-bin" className="block text-sm font-medium text-slate-700">
                BIN (optional)
              </label>
              <input
                id="intake-bin"
                className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
                value={form.bin}
                onChange={(e) => setForm({ ...form, bin: e.target.value })}
              />
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
      </div>
    </div>
  );
}
