import { useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../../stores/agentStore";
import { ChatScalar } from "../../plugins/registry/slotKeys";
import { useChatScalarSnapshot } from "../../plugins/registry/useChatExtensions";
import { resolveLocalized } from "../../plugins/registry/types";
import {
  resolveChatAgentIdentity,
  resolveChatColorPrimary,
} from "./chatAgentIdentity";

/** 订阅 agent store，返回当前智能体在聊天 UI 中应展示的昵称与头像 */
export function useChatAgentIdentity() {
  const { t, i18n } = useTranslation();
  const { selectedAgent, agents } = useAgentStore();
  const extScalar = useChatScalarSnapshot();

  return useMemo(() => {
    const colorPrimary = resolveChatColorPrimary(
      extScalar[ChatScalar.themeColorPrimary]?.value,
    );
    const base = resolveChatAgentIdentity(
      selectedAgent,
      agents,
      t,
      colorPrimary,
    );
    const locale = i18n.language;
    const extNick = resolveLocalized(
      extScalar[ChatScalar.welcomeNick]?.value,
      locale,
    );
    const extAvatar = resolveLocalized(
      extScalar[ChatScalar.welcomeAvatar]?.value,
      locale,
    );

    return {
      nick: (extNick ?? base.nick) as ReactNode,
      avatarSrc: (extAvatar ?? base.avatarSrc) as string | ReactNode,
    };
  }, [selectedAgent, agents, t, i18n.language, extScalar]);
}
