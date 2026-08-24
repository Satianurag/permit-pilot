/** NYC BBL borough digit — PLUTO / DOB convention. */
export const BOROUGH_BY_DIGIT: Record<string, string> = {
  "1": "Manhattan",
  "2": "Bronx",
  "3": "Brooklyn",
  "4": "Queens",
  "5": "Staten Island",
};

export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export function boroughFromBbl(bbl: string): string | undefined {
  return BOROUGH_BY_DIGIT[digitsOnly(bbl)[0] ?? ""];
}

export function bblError(bbl: string): string | null {
  const digits = digitsOnly(bbl);
  if (!digits) return "Enter the 10-digit BBL.";
  if (digits.length !== 10) return "BBL must be 10 digits (borough + block + lot).";
  if (!BOROUGH_BY_DIGIT[digits[0]]) return "First BBL digit must be 1–5 (NYC borough).";
  return null;
}

export function binError(bin: string): string | null {
  const digits = digitsOnly(bin);
  if (!digits) return null;
  if (digits.length !== 7) return "BIN is 7 digits when provided.";
  return null;
}

