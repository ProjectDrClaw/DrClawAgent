import React, { useState } from "react";
import { providerIcon } from "./providerIcon";
import {
  getProviderLetterColor,
  getProviderLetter,
} from "./providerLetterIcon";
import defaultImg from "@/assets/providers/default.jpg";

/** 未知 provider 时 providerIcon() 返回的默认图 */
const DEFAULT_FALLBACK_URL = defaultImg;

interface ProviderIconProps {
  providerId: string;
  size?: number;
}

/**
 * 渲染 provider 图标：优先本地图，失败或未知时回退为首字母头像。
 */
export const ProviderIcon: React.FC<ProviderIconProps> = ({
  providerId,
  size = 32,
}) => {
  const rawUrl = providerIcon(providerId);
  const imageUrl = rawUrl === DEFAULT_FALLBACK_URL ? undefined : rawUrl;
  const [imageFailed, setImageFailed] = useState(false);

  const borderRadius = size * 0.25;

  if (imageUrl && !imageFailed) {
    return (
      <img
        src={imageUrl}
        alt={providerId}
        width={size}
        height={size}
        style={{ borderRadius, objectFit: "cover", flexShrink: 0 }}
        onError={() => setImageFailed(true)}
      />
    );
  }

  const backgroundColor = getProviderLetterColor(providerId);
  const letter = getProviderLetter(providerId);
  const fontSize = size * 0.45;

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius,
        backgroundColor,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#fff",
        fontSize,
        fontWeight: 600,
        fontFamily: "Inter, sans-serif",
        userSelect: "none",
        flexShrink: 0,
      }}
      title={providerId}
    >
      {letter}
    </div>
  );
};
