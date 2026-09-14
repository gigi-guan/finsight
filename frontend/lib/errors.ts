import { ApiError } from "@/lib/api/client";

/** Normalize unknown catch values into a user-facing message. */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
