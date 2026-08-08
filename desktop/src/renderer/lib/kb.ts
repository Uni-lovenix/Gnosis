/**
 * Wrapper around window.kb for type-safety inside the renderer.
 */
import type { KBAPI } from "../../shared/types";

export const kb: KBAPI = (window as unknown as { kb: KBAPI }).kb;