import { Avatar, Flex } from "antd";
import { useChatAgentIdentity } from "../useChatAgentIdentity";

/** 助手消息气泡顶部的头像 + 昵称行 */
export default function ChatAgentIdentityHeader() {
  const { nick, avatarSrc } = useChatAgentIdentity();

  return (
    <Flex align="center" gap={8} style={{ marginBottom: 8 }}>
      {avatarSrc &&
        (typeof avatarSrc === "string" ? (
          <Avatar src={avatarSrc} />
        ) : (
          avatarSrc
        ))}
      {typeof nick === "string" ? <span>{nick}</span> : nick}
    </Flex>
  );
}
