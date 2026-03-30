import { z } from "zod";

export const KingdomAdditionalDataSchema = z.object({
  current_governor: z.number().int(),
  target_governor: z.number().int(),
  skipped_governors: z.number().int(),
  power_ok: z.union([z.boolean(), z.string()]),
  kills_ok: z.union([z.boolean(), z.string()]),
  reconstruction_success: z.union([z.boolean(), z.string()]),
  remaining_sec: z.number(),
  ch_verification_mode: z.boolean().default(false),
  ch_current_governor: z.number().int().default(0),
  ch_total_governors: z.number().int().default(0),
  current_time: z
    .string()
    .datetime({ offset: true })
    .default("2025-01-27T22:09:30.591099+01:00"),
});
export type KingdomAdditionalData = z.infer<typeof KingdomAdditionalDataSchema>;
