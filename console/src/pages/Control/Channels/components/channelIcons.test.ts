import { describe, it, expect } from "vitest";
import {
  getChannelIconUrl,
  getChannelLetterColor,
  CHANNEL_DEFAULT_ICON_URL,
  CHANNEL_ICON_URLS,
} from "./channelIcons";

describe("getChannelIconUrl", () => {
  it("returns local asset for known channel 'dingtalk'", () => {
    const url = getChannelIconUrl("dingtalk");
    expect(url).toBe(CHANNEL_ICON_URLS.dingtalk);
    expect(typeof url).toBe("string");
    expect(url.length).toBeGreaterThan(0);
  });

  it("returns local asset for known channel 'discord'", () => {
    const url = getChannelIconUrl("discord");
    expect(url).toBe(CHANNEL_ICON_URLS.discord);
  });

  it("returns CHANNEL_DEFAULT_ICON_URL for unknown channel", () => {
    const url = getChannelIconUrl("unknown_channel");
    expect(url).toBe(CHANNEL_DEFAULT_ICON_URL);
  });

  it("CHANNEL_DEFAULT_ICON_URL is a non-empty string", () => {
    expect(CHANNEL_DEFAULT_ICON_URL).toBeTruthy();
    expect(typeof CHANNEL_DEFAULT_ICON_URL).toBe("string");
  });
});

describe("getChannelLetterColor", () => {
  it("returns predefined color '#2657C9' for known channel 'console'", () => {
    expect(getChannelLetterColor("console")).toBe("#2657C9");
  });

  it("returns predefined color '#5865F2' for known channel 'discord'", () => {
    expect(getChannelLetterColor("discord")).toBe("#5865F2");
  });

  it("returns a color string starting with '#' for unknown channel 'my_custom_bot'", () => {
    const color = getChannelLetterColor("my_custom_bot");
    expect(typeof color).toBe("string");
    expect(color).toMatch(/^#/);
  });

  it("returns the same color on repeated calls for the same unknown channel (deterministic hash)", () => {
    const color1 = getChannelLetterColor("my_custom_bot");
    const color2 = getChannelLetterColor("my_custom_bot");
    expect(color1).toBe(color2);
  });
});
