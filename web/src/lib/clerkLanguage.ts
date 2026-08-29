import { DepartmentReview } from "./api";

export const DEPT_LABELS: Record<string, string> = {
  zoning: "Zoning",
  building: "Buildings",
  fire: "Fire",
  utilities: "Water & sewer",
  landmarks: "Landmarks",
  housing: "Housing",
  critic: "Citation check",
};

export function departmentLabel(department: string): string {
  return DEPT_LABELS[department] ?? department.replaceAll("_", " ");
}

export function generatedByBadge(generatedBy?: string): string | null {
  if (generatedBy === "engine_fallback") return "City records only";
  return null;
}

export function generatedByHint(generatedBy?: string): string | null {
  if (generatedBy === "engine_fallback") {
    return "Automatic review unavailable. City records are attached for you to read.";
  }
  return null;
}

export function datasetLabel(datasetId: string): string {
  const names: Record<string, string> = {
    "64uk-42ks": "PLUTO (zoning)",
    "rbx6-tga4": "DOB NOW permits",
    "w9ak-ipjd": "DOB NOW filings",
    "3h2n-5cm9": "DOB violations (legacy)",
    "855j-jady": "DOB safety violations",
    "skr7-cxt3": "DEP ECB violations",
    "gpmc-yuvp": "Landmarks",
    "bi53-yph3": "FDNY violations (historical)",
    "wvxf-dwi5": "HPD violations",
    "5zhs-2jue": "Building footprints",
  };
  return names[datasetId] ?? datasetId;
}

export function hitlKindLabel(kind: string): string {
  if (kind === "send_claim") return "Request for the applicant";
  if (kind === "record_decision") return "Ready for your decision";
  return "Needs your confirmation";
}

export function collectObjections(reviews: DepartmentReview[]) {
  return reviews.flatMap((review) =>
    (review.objections ?? [])
      .filter((item) => item.status === "open" || item.status === "new")
      .map((item) => ({
        ...item,
        department: item.department || review.department,
      })),
  );
}

export const HINT_STORAGE_KEY = "pp-queue-hint-dismissed";
