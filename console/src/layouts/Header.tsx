import { Layout, Space, message } from "antd";
import LanguageSwitcher from "../components/LanguageSwitcher/index";
import ThemeToggleButton from "../components/ThemeToggleButton";
import CodingModeToggle from "../components/CodingModeToggle";
import styles from "./index.module.less";
import api from "../api";
import { getUsername } from "../api/config";
import { useTheme } from "../contexts/ThemeContext";
import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Slot } from "../plugins/registry/Slot";
import { isDesktopApp } from "../tauri/backendRuntime";
import { UserOutlined } from "@ant-design/icons";

const { Header: AntHeader } = Layout;

export default function Header() {
  const { isDark } = useTheme();
  const onDesktop = isDesktopApp();
  const [version, setVersion] = useState<string>("");
  const username = getUsername();
  const logoClicksRef = useRef<number[]>([]);

  useEffect(() => {
    api
      .getVersion()
      .then((res) => setVersion(res?.version ?? ""))
      .catch(() => {});
  }, []);

  // 隐藏手势：桌面端 3 秒内连点 Logo 8 次打开 DevTools
  const handleLogoClick = () => {
    if (!onDesktop) return;
    const now = Date.now();
    const windowStart = now - 3000;
    logoClicksRef.current = logoClicksRef.current.filter(
      (time) => time > windowStart,
    );
    logoClicksRef.current.push(now);
    if (logoClicksRef.current.length >= 8) {
      logoClicksRef.current = [];
      invoke("open_devtools")
        .then(() => message.success("DevTools opened"))
        .catch((err: unknown) => {
          const errMsg =
            err instanceof Error
              ? err.message
              : typeof err === "string"
                ? err
                : JSON.stringify(err);
          console.error("Failed to open DevTools:", errMsg);
          message.error(`DevTools error: ${errMsg}`);
        });
    }
  };

  return (
    <AntHeader className={styles.header}>
      <div className={styles.logoWrapper} onClick={handleLogoClick}>
        {/*
          Slot lets a plugin replace the brand logo (e.g. a per-agent
          branding override). When no plugin registers a replacement —
          or when the registered render returns null — the host default
          <img> below paints.
        */}
        <Slot name="header.logo" kind="replace">
          <img
            src={isDark ? "/logo-dark.png" : "/logo-light.png"}
            alt="Dr.Claw"
            className={styles.logoImg}
          />
        </Slot>
        <div className={styles.logoDivider} />
        {version && (
          <span
            className={`${styles.versionBadge} ${styles.versionBadgeDefault}`}
          >
            v{version}
          </span>
        )}
      </div>
      <Slot name="header.left" kind="fill" />
      <Space size="middle" align="center" className={styles.headerActions}>
        <Slot name="header.right" kind="fill" />
        <div className={styles.headerCodingControl}>
          <CodingModeToggle />
        </div>
        {username && (
          <>
            <div className={styles.headerDivider} />
            <div className={styles.headerUser}>
              <UserOutlined />
              <span>{username}</span>
            </div>
          </>
        )}
        <div className={styles.headerDivider} />
        <LanguageSwitcher />
        <ThemeToggleButton />
      </Space>
    </AntHeader>
  );
}
