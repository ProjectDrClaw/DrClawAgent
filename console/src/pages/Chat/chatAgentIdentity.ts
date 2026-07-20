import type { TFunction } from "i18next";
import type { AgentSummary } from "../../api/types/agents";
import {
  DEFAULT_AGENT_ID,
  getAgentDisplayName,
} from "../../utils/agentDisplayName";
import { getAgentLetterAvatarUrl } from "../../utils/agentLetterAvatar";
import defaultConfig from "./OptionsPanel/defaultConfig";

export interface ChatAgentIdentity {
  nick: string;
  avatarSrc: string;
}

/** 解析聊天 UI 当前生效的主题色（插件覆盖 > 默认配置） */
export function resolveChatColorPrimary(extColorPrimary?: string): string {
  return extColorPrimary ?? defaultConfig.theme.colorPrimary;
}

/** 根据当前智能体解析聊天气泡/欢迎页使用的昵称与头像 URL */
export function resolveChatAgentIdentity(
  selectedAgent: string,
  agents: AgentSummary[],
  t: TFunction,
  colorPrimary: string = defaultConfig.theme.colorPrimary,
): ChatAgentIdentity {
  if (selectedAgent === DEFAULT_AGENT_ID) {
    return { nick: "Dr.Claw", avatarSrc: "/avatar.png" };
  }

  const currentAgent = agents.find((a) => a.id === selectedAgent);
  const nick = getAgentDisplayName(
    currentAgent ?? { id: selectedAgent, name: selectedAgent },
    t,
  );

  return {
    nick,
    avatarSrc: getAgentLetterAvatarUrl(nick, { backgroundColor: colorPrimary }),
  };
}
