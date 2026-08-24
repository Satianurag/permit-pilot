import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, IntakePayload } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function IntakeModal({ open, onClose }: Props) {
  const navigate = useNavigate();
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

  if (!open) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await api.intake(form);
      onClose();
      navigate(`/cases/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Intake failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-30 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-pp-navy">New permit intake</h2>
        <p className="text-sm text-slate-600">
          Packet text is PII-redacted before storage. BBL/BIN resolve against live NYC Open Data.
        </p>
        {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{error}</p>}
        <form className="space-y-3" onSubmit={submit}>
          <input
            required
            className="w-full border border-pp-border rounded-md px-3 py-2 text-sm"
            placeholder="Address"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              className="border border-pp-border rounded-md px-3 py-2 text-sm"
              placeholder="BBL"
              value={form.bbl}
              onChange={(e) => setForm({ ...form, bbl: e.target.value })}
            />
            <input
              className="border border-pp-border rounded-md px-3 py-2 text-sm"
              placeholder="BIN (optional)"
              value={form.bin}
              onChange={(e) => setForm({ ...form, bin: e.target.value })}
            />
          </div>
          <input
            required
            className="w-full border border-pp-border rounded-md px-3 py-2 text-sm"
            placeholder="Work type"
            value={form.work_type}
            onChange={(e) => setForm({ ...form, work_type: e.target.value })}
          />
          <textarea
            className="w-full border border-pp-border rounded-md px-3 py-2 text-sm min-h-24"
            placeholder="Applicant packet (SSN/email/phone will be redacted)…"
            value={form.packet_text}
            onChange={(e) => setForm({ ...form, packet_text: e.target.value })}
          />
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
