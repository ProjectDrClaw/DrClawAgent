import type { TFunction } from "i18next";
import type { AgentSummary } from "../api/types/agents";

export const DEFAULT_AGENT_ID = "default";
/** 历史/新建未定制时的占位名；命中则走 i18n（现为 Dr.Claw）。 */
export const DEFAULT_AGENT_DISPLAY_NAME = "Default Agent";
const DEFAULT_AGENT_PLACEHOLDER_NAMES = new Set([
  DEFAULT_AGENT_DISPLAY_NAME,
  "Default",
  "Dr.Claw",
]);

/** UI label for an agent; `default` id uses i18n, others use API `name` (fallback: id). */
export function getAgentDisplayName(
  agent: Pick<AgentSummary, "id" | "name">,
  t: TFunction,
): string {
  // For default agent, preserve i18n unless explicitly customized
  if (agent.id === DEFAULT_AGENT_ID) {
    // If name is customized (not a product placeholder), show custom name
    if (agent.name && !DEFAULT_AGENT_PLACEHOLDER_NAMES.has(agent.name)) {
      return agent.name;
    }
    // Otherwise, fall back to localized default name
    return t("agent.defaultDisplayName");
  }
  // For other agents, use user-defined name or fallback to id
  return agent.name || agent.id;
}
