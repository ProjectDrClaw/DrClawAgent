import dingtalk from "@/assets/channels/dingtalk.png";
import voice from "@/assets/channels/voice.png";
import sip from "@/assets/channels/sip.png";
import qq from "@/assets/channels/qq.png";
import feishu from "@/assets/channels/feishu.png";
import xiaoyi from "@/assets/channels/xiaoyi.png";
import telegram from "@/assets/channels/telegram.png";
import mqtt from "@/assets/channels/mqtt.png";
import imessage from "@/assets/channels/imessage.png";
import discord from "@/assets/channels/discord.png";
import mattermost from "@/assets/channels/mattermost.png";
import matrix from "@/assets/channels/matrix.png";
import consoleIcon from "@/assets/channels/console.png";
import wecom from "@/assets/channels/wecom.png";
import wechat from "@/assets/channels/wechat.png";
import onebot from "@/assets/channels/onebot.png";
import yuanbao from "@/assets/channels/yuanbao.png";
import defaultImg from "@/assets/channels/default.png";

/** 各 channel 离线图标 URL 映射（slack 老库无本地图，暂用 CDN） */
export const CHANNEL_ICON_URLS: Record<string, string> = {
  dingtalk,
  voice,
  sip,
  qq,
  feishu,
  xiaoyi,
  telegram,
  slack:
    "https://gw.alicdn.com/imgextra/i2/O1CN01JcOK7v1GqHhRjG0fy_!!6000000000673-2-tps-512-512.png",
  mqtt,
  imessage,
  discord,
  mattermost,
  matrix,
  console: consoleIcon,
  wecom,
  wechat,
  onebot,
  yuanbao,
};

export const CHANNEL_DEFAULT_ICON_URL = defaultImg;

/** Get the icon URL for a channel, with a default fallback. */
export function getChannelIconUrl(channelKey: string): string {
  return CHANNEL_ICON_URLS[channelKey] ?? CHANNEL_DEFAULT_ICON_URL;
}

/** Predefined background colors for letter-avatar icons. */
const LETTER_ICON_COLORS: Record<string, string> = {
  console: "#2657C9",
  onebot: "#6ECB63",
  dingtalk: "#3370FF",
  feishu: "#3370FF",
  qq: "#12B7F5",
  telegram: "#2AABEE",
  slack: "#4A154B",
  discord: "#5865F2",
  wecom: "#07C160",
  wechat: "#07C160",
  mqtt: "#660066",
  mattermost: "#0058CC",
  matrix: "#0DBD8B",
  imessage: "#34C759",
  voice: "#F44336",
  xiaoyi: "#CF1322",
  yuanbao: "#2657C9",
  openim: "#1C64F2",
};

/** A palette of fallback colors for channels without a predefined color. */
const FALLBACK_COLORS = [
  "#FF6B6B",
  "#4ECDC4",
  "#45B7D1",
  "#96CEB4",
  "#FFEAA7",
  "#DDA0DD",
  "#98D8C8",
  "#F7DC6F",
  "#BB8FCE",
  "#85C1E9",
  "#F0B27A",
  "#82E0AA",
];

/** Get the background color for a channel's letter-avatar icon. */
export function getChannelLetterColor(channelKey: string): string {
  if (LETTER_ICON_COLORS[channelKey]) {
    return LETTER_ICON_COLORS[channelKey];
  }
  // Deterministic fallback based on string hash
  let hash = 0;
  for (let i = 0; i < channelKey.length; i++) {
    hash = ((hash << 5) - hash + channelKey.charCodeAt(i)) | 0;
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

/** Get the display letter(s) for a channel's letter-avatar icon. */
export function getChannelLetter(channelKey: string): string {
  return channelKey.charAt(0).toUpperCase();
}
