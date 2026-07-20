import { describe, it, expect } from "vitest";
import { providerIcon } from "./providerIcon";
import defaultImg from "@/assets/providers/default.jpg";
import openai from "@/assets/providers/openai.png";
import kimi from "@/assets/providers/kimi.png";

describe("providerIcon", () => {
  it("returns the local openai asset for the openai provider", () => {
    expect(providerIcon("openai")).toBe(openai);
  });

  it("returns the same asset for kimi-cn and kimi-intl (alias grouping)", () => {
    const cn = providerIcon("kimi-cn");
    const intl = providerIcon("kimi-intl");
    expect(cn).toBe(intl);
    expect(cn).toBe(kimi);
  });

  it("returns the fallback asset for an unknown provider", () => {
    expect(providerIcon("unknown-provider")).toBe(defaultImg);
    expect(providerIcon("")).toBe(defaultImg);
  });

  it("always returns a non-empty string for every supported provider", () => {
    const known = [
      "modelscope",
      "aliyun-codingplan",
      "aliyun-codingplan-intl",
      "aliyun-tokenplan",
      "deepseek",
      "gemini",
      "azure-openai",
      "anthropic",
      "ollama",
      "minimax-cn",
      "minimax",
      "dashscope",
      "lmstudio",
      "siliconflow-cn",
      "siliconflow-intl",
      "qwenpaw-local",
      "zhipu-cn",
      "zhipu-intl",
      "zhipu-cn-codingplan",
      "zhipu-intl-codingplan",
      "openrouter",
      "opencode",
      "kilo",
      "github-models",
      "volcengine-cn",
      "volcengine-cn-codingplan",
      "mimo-tokenplan",
      "openai-response",
    ];
    for (const p of known) {
      const url = providerIcon(p);
      expect(typeof url).toBe("string");
      expect(url.length).toBeGreaterThan(0);
      expect(url).not.toBe(defaultImg);
    }
  });
});
