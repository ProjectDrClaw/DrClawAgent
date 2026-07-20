import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Form } from "antd";
import { useAppMessage } from "../../../hooks/useAppMessage";
import {
  LockOutlined,
  UserOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from "@ant-design/icons";
import { authApi } from "../../../api/modules/auth";
import { setAuthToken, setUsername } from "../../../api/config";
import styles from "./index.module.less";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const [usernameFocused, setUsernameFocused] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { message } = useAppMessage();

  useEffect(() => {
    authApi
      .getStatus()
      .then((res) => {
        if (!res.enabled) {
          navigate("/chat", { replace: true });
          return;
        }
        setHasUsers(res.has_users);
        if (!res.has_users) {
          setIsRegister(true);
        }
      })
      .catch(() => {});
  }, [navigate]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const raw = searchParams.get("redirect") || "/chat";
      const redirect =
        raw.startsWith("/") && !raw.startsWith("//") ? raw : "/chat";

      if (isRegister) {
        const res = await authApi.register(values.username, values.password);
        setAuthToken(res.token);
        setUsername(res.username);
        message.success(t("login.registerSuccess"));
        navigate(redirect, { replace: true });
      } else {
        const res = await authApi.login(values.username, values.password);
        setAuthToken(res.token);
        setUsername(res.username);
        message.success(t("login.loginSuccess"));
        navigate(redirect, { replace: true });
      }
    } catch (err) {
      let errorMsg = t("login.failed");
      if (err instanceof Error) {
        errorMsg = err.message;
      } else if (isRegister) {
        errorMsg = t("login.registerFailed");
      }
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#F1F5F9",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        WebkitFontSmoothing: "antialiased",
        padding: 24,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 960,
          minHeight: 620,
          borderRadius: 20,
          display: "flex",
          overflow: "hidden",
          boxShadow:
            "0 30px 60px -15px rgba(0, 0, 0, 0.08), 0 8px 20px -5px rgba(38, 87, 201, 0.06), inset 0 1px 0px rgba(255, 255, 255, 0.9)",
        }}
      >
        {/* 左侧配图区 */}
        <div
          style={{
            flex: 1.1,
            background:
              "linear-gradient(145deg, #2657C9 0%, #1a3b9f 60%, #0f2570 100%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            padding: "56px 48px",
            overflow: "hidden",
          }}
        >
          {/* 背景装饰 - 微纹路 */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage:
                "radial-gradient(rgba(255,255,255,0.08) 1.5px, transparent 1.5px)",
              backgroundSize: "28px 28px",
              zIndex: 0,
            }}
          />
          {/* 装饰光晕 */}
          <div
            style={{
              position: "absolute",
              width: 400,
              height: 400,
              background:
                "radial-gradient(ellipse, rgba(100, 160, 255, 0.35) 0%, transparent 70%)",
              top: -80,
              right: -80,
              borderRadius: "50%",
              zIndex: 0,
            }}
          />

          {/* 左侧内容区 */}
          <div
            style={{
              position: "relative",
              zIndex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            {/* 顶部标语 */}
            <div
              style={{
                color: "rgba(255, 255, 255, 0.75)",
                fontSize: 13,
                fontWeight: 500,
                letterSpacing: 3,
                textTransform: "uppercase",
                marginBottom: 32,
              }}
            >
              AI · Medical Intelligence
            </div>

            {/* 医生插图 */}
            <div
              style={{
                width: "100%",
                maxWidth: 360,
                height: "auto",
                borderRadius: 12,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 36,
                border: "1px solid rgba(255,255,255,0.1)",
                boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
                overflow: "hidden",
              }}
              className={styles.floatImg}
            >
              <img
                src="/login.png"
                alt="医生插图"
                style={{
                  width: "100%",
                  height: "auto",
                  objectFit: "cover",
                }}
              />
            </div>

            {/* 主标题 */}
            <div
              style={{
                color: "#ffffff",
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: -0.5,
                lineHeight: 1.4,
                marginBottom: 4,
              }}
            >
              赋能每一位医生
            </div>
            <div
              style={{
                color: "#ffffff",
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: -0.5,
                lineHeight: 1.4,
                marginBottom: 12,
              }}
            >
              让诊疗更高效、更精准
            </div>

            {/* 描述文字 */}
            <div
              style={{
                color: "rgba(255, 255, 255, 0.6)",
                fontSize: 14,
                fontWeight: 400,
                lineHeight: 1.7,
              }}
            >
              全医疗场景覆盖 · 多模态AI分析
              <br />
              实时运营洞察 · 智能决策支持
            </div>
          </div>
        </div>

        {/* 右侧登录表单 */}
        <div
          style={{
            flex: 0.9,
            backgroundColor: "rgba(255, 255, 255, 0.92)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "56px 48px",
          }}
        >
          {/* Logo */}
          <div
            style={{
              fontSize: 44,
              lineHeight: 1,
              marginBottom: 16,
              letterSpacing: -1.5,
            }}
          >
            <span
              style={{ color: "#2657C9", fontWeight: 700, fontStyle: "italic" }}
            >
              Dr.
            </span>
            <span
              style={{ color: "#111111", fontWeight: 900, fontStyle: "italic" }}
            >
              Claw
            </span>
          </div>

          {/* 副标题 */}
          <div
            style={{
              fontSize: 13,
              color: "#5A6480",
              marginBottom: 48,
              fontWeight: 500,
              letterSpacing: 0.3,
            }}
          >
            {isRegister ? "请注册您的账户" : "欢迎回来，请登录您的账户"}
          </div>

          {!hasUsers && (
            <p
              style={{
                margin: "0 0 16px",
                color: "#666",
                fontSize: 13,
              }}
            >
              {t("login.firstUserHint")}
            </p>
          )}

          <Form
            layout="vertical"
            onFinish={onFinish}
            autoComplete="off"
            style={{ width: "100%" }}
          >
            <Form.Item name="username" style={{ marginBottom: 16 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  background: usernameFocused
                    ? "#ffffff"
                    : "rgba(238, 243, 255, 0.65)",
                  borderRadius: 8,
                  padding: "0 16px",
                  height: 52,
                  border: usernameFocused
                    ? "1px solid rgba(38, 87, 201, 0.35)"
                    : "1px solid rgba(38, 87, 201, 0.1)",
                  boxShadow: usernameFocused
                    ? "0 0 0 4px rgba(38, 87, 201, 0.08)"
                    : "none",
                  transition:
                    "border-color 0.3s, background-color 0.3s, box-shadow 0.3s",
                }}
              >
                <div
                  style={{
                    color: usernameFocused ? "#2657C9" : "#5A6480",
                    fontSize: 20,
                    marginRight: 12,
                    transition: "color 0.3s",
                  }}
                >
                  <UserOutlined />
                </div>
                <input
                  type="text"
                  placeholder=""
                  autoFocus
                  onFocus={() => setUsernameFocused(true)}
                  onBlur={() => setUsernameFocused(false)}
                  style={{
                    flex: 1,
                    border: "none",
                    background: "transparent",
                    outline: "none",
                    fontSize: 15,
                    fontWeight: 500,
                    color: "#111111",
                    padding: 0,
                    fontFamily:
                      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  }}
                />
              </div>
            </Form.Item>

            <Form.Item name="password" style={{ marginBottom: 0 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  background: passwordFocused
                    ? "#ffffff"
                    : "rgba(238, 243, 255, 0.65)",
                  borderRadius: 8,
                  padding: "0 16px",
                  height: 52,
                  border: passwordFocused
                    ? "1px solid rgba(38, 87, 201, 0.35)"
                    : "1px solid rgba(38, 87, 201, 0.1)",
                  boxShadow: passwordFocused
                    ? "0 0 0 4px rgba(38, 87, 201, 0.08)"
                    : "none",
                  transition:
                    "border-color 0.3s, background-color 0.3s, box-shadow 0.3s",
                }}
              >
                <div
                  style={{
                    color: passwordFocused ? "#2657C9" : "#5A6480",
                    fontSize: 20,
                    marginRight: 12,
                    transition: "color 0.3s",
                  }}
                >
                  <LockOutlined />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder=""
                  onFocus={() => setPasswordFocused(true)}
                  onBlur={() => setPasswordFocused(false)}
                  style={{
                    flex: 1,
                    border: "none",
                    background: "transparent",
                    outline: "none",
                    fontSize: 15,
                    fontWeight: 500,
                    color: "#111111",
                    padding: 0,
                    fontFamily:
                      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  }}
                />
                <div
                  style={{
                    color: passwordFocused ? "#2657C9" : "#5A6480",
                    fontSize: 20,
                    marginLeft: 12,
                    cursor: "pointer",
                    transition: "color 0.3s, transform 0.2s",
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.transform = "scale(1.1)";
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.transform = "scale(1)";
                  }}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                </div>
              </div>
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, marginTop: 32 }}>
              <button
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
                  height: 52,
                  background:
                    "linear-gradient(135deg, #2657C9 0%, #1a46b8 100%)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 26,
                  fontSize: 16,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  letterSpacing: 1,
                  position: "relative",
                  overflow: "hidden",
                  transition:
                    "transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s",
                  boxShadow: "0 4px 12px rgba(38, 87, 201, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                onMouseEnter={(e) => {
                  if (!loading) {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow =
                      "0 8px 24px -4px rgba(38, 87, 201, 0.35)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loading) {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow =
                      "0 4px 12px rgba(38, 87, 201, 0.3)";
                  }
                }}
              >
                {loading ? (
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <div className={styles.spinner} />
                    <span>加载中...</span>
                  </div>
                ) : isRegister ? (
                  t("login.register")
                ) : (
                  "登 录"
                )}
              </button>
            </Form.Item>
          </Form>

          {/* 底部链接 */}
          <div
            style={{
              marginTop: 24,
              fontSize: 12,
              color: "#9EA8C2",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            遇到问题？请联系{" "}
            <a
              href="#"
              style={{
                color: "#2657C9",
                textDecoration: "none",
                fontWeight: 500,
              }}
            >
              系统管理员
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
