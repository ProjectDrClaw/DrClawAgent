import { Card, Select, Alert, Input } from "antd";
import { useTranslation } from "react-i18next";
import type { TranscriptionProvider } from "../useVoiceTranscription";
import styles from "../index.module.less";

interface ProviderSelectCardProps {
  availableProviders: TranscriptionProvider[];
  selectedProviderId: string;
  onProviderChange: (id: string) => void;
  transcriptionModel: string;
  onTranscriptionModelChange: (model: string) => void;
}

export function ProviderSelectCard({
  availableProviders,
  selectedProviderId,
  onProviderChange,
  transcriptionModel,
  onTranscriptionModelChange,
}: ProviderSelectCardProps) {
  const { t } = useTranslation();

  return (
    <Card className={styles.card}>
      <h3 className={styles.cardTitle}>
        {t("voiceTranscription.providerLabel")}
      </h3>
      <p className={styles.cardDescription}>
        {t("voiceTranscription.providerDescription")}
      </p>

      {availableProviders.length === 0 ? (
        <Alert
          type="warning"
          showIcon
          message={t("voiceTranscription.noProvidersWarning")}
        />
      ) : (
        <Select
          value={selectedProviderId || undefined}
          onChange={onProviderChange}
          placeholder={t("voiceTranscription.providerPlaceholder")}
          style={{ width: "100%", maxWidth: 400 }}
        >
          {availableProviders.map((p) => (
            <Select.Option key={p.id} value={p.id}>
              {p.name}
            </Select.Option>
          ))}
        </Select>
      )}

      <h3 className={styles.cardTitle} style={{ marginTop: 20 }}>
        {t("voiceTranscription.modelLabel")}
      </h3>
      <p className={styles.cardDescription}>
        {t("voiceTranscription.modelDescription")}
      </p>
      <Input
        value={transcriptionModel}
        onChange={(e) => onTranscriptionModelChange(e.target.value)}
        placeholder={t("voiceTranscription.modelPlaceholder")}
        style={{ maxWidth: 400 }}
      />
    </Card>
  );
}
