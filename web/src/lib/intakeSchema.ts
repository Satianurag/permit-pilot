import { z } from "zod";

export const intakeSchema = z.object({
  address: z.string().trim().min(3, "Enter a street address"),
  bbl: z.string().regex(/^\d{10}$/, "BBL must be 10 digits"),
  bin: z.string().regex(/^$|^\d{7}$/, "BIN must be 7 digits"),
  work_type: z.string().trim().min(3, "Describe the proposed work"),
  owner: z.string().optional(),
  borough: z.string().optional(),
  packet_text: z.string().optional(),
});

export type IntakeFields = z.infer<typeof intakeSchema>;
