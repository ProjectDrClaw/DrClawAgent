/** 从显示名提取首字母（支持中英文） */
export function getAgentLetter(displayName: string): string {
  const trimmed = displayName.trim();
  if (!trimmed) return "?";
  const first = [...trimmed][0];
  return /[a-z]/i.test(first) ? first.toUpperCase() : first;
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * 生成首字母头像的 SVG data URL。
 * SDK ResponseCard 使用 antd Avatar 的 src 属性，只接受 URL 字符串。
 */
export function getAgentLetterAvatarUrl(
  displayName: string,
  options?: {
    size?: number;
    /** 背景色，默认使用系统主题色 */
    backgroundColor?: string;
  },
): string {
  const size = options?.size ?? 64;
  // 调用方应传入 theme.colorPrimary；此处仅作兜底
  const backgroundColor = options?.backgroundColor ?? "#2657C9";
  const letter = escapeXml(getAgentLetter(displayName));
  const fontSize = Math.round(size * 0.45);
  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`,
    `<circle cx="${size / 2}" cy="${size / 2}" r="${
      size / 2
    }" fill="${backgroundColor}"/>`,
    `<text x="50%" y="50%" dy="0.35em" text-anchor="middle" fill="#ffffff"`,
    ` font-family="Inter, sans-serif" font-size="${fontSize}" font-weight="600">${letter}</text>`,
    `</svg>`,
  ].join("");
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
