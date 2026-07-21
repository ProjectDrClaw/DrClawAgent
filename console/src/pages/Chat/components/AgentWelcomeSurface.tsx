import { WelcomePrompts } from "@agentscope-ai/chat";
import type { WelcomeRenderProps } from "../../../plugins/registry/types";

interface AgentWelcomeSurfaceProps extends WelcomeRenderProps {
  avatar: WelcomeRenderProps["avatar"];
}

/** 欢迎页展示智能体头像；不写 welcome.avatar，避免与 ResponseCard 内置头像重复 */
export default function AgentWelcomeSurface({
  greeting,
  description,
  prompts,
  onSubmit,
  avatar,
}: AgentWelcomeSurfaceProps) {
  return (
    <WelcomePrompts
      greeting={greeting as string | undefined}
      avatar={avatar as string | undefined}
      description={description as string | undefined}
      prompts={prompts as Parameters<typeof WelcomePrompts>[0]["prompts"]}
      onClick={(query) => onSubmit({ query })}
    />
  );
}
