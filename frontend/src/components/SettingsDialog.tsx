import { useState, useEffect } from "react";
import { X, Save, CheckCircle, AlertCircle } from "lucide-react";
import { getSettings, updateSettings } from "@/services/api";
import type { SettingsData, SettingsUpdate, VoiceSettings } from "@/types";

interface Props {
  open: boolean;
  onClose: () => void;
  voiceSettings: VoiceSettings;
  onVoiceSettingsChange: (settings: VoiceSettings) => void;
  voices: SpeechSynthesisVoice[];
}

const providers = [
  { value: "dummy", label: "Dummy (Platzhalter-Antworten)" },
  { value: "openai", label: "OpenAI (GPT)" },
  { value: "gemini", label: "Google Gemini" },
  { value: "anthropic", label: "Anthropic Claude" },
];

export function SettingsDialog({ open, onClose, voiceSettings, onVoiceSettingsChange, voices }: Props) {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [form, setForm] = useState<SettingsUpdate>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      getSettings()
        .then((data) => {
          setSettings(data);
          setForm({ llm_provider: data.llm_provider });
        })
        .catch(() => setError("Einstellungen konnten nicht geladen werden."));
    }
  }, [open]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const data = await updateSettings(form);
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-100">Einstellungen</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-5">
          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1.5">
              LLM Provider
            </label>
            <select
              value={form.llm_provider || settings?.llm_provider || "dummy"}
              onChange={(e) => setForm({ ...form, llm_provider: e.target.value })}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              {providers.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* OpenAI Settings */}
          <fieldset className="space-y-3 border border-zinc-800 rounded-lg p-3">
            <legend className="text-sm font-medium text-zinc-400 px-2">OpenAI</legend>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">API Key</label>
              <input
                type="password"
                placeholder={settings?.openai_api_key_set ? "••••••• (gesetzt)" : "sk-..."}
                onChange={(e) => setForm({ ...form, openai_api_key: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Model</label>
              <input
                type="text"
                defaultValue={settings?.openai_model || "gpt-4o-mini"}
                onChange={(e) => setForm({ ...form, openai_model: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Base URL</label>
              <input
                type="text"
                defaultValue={settings?.openai_base_url || "https://api.openai.com/v1"}
                onChange={(e) => setForm({ ...form, openai_base_url: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </fieldset>

          {/* Gemini Settings */}
          <fieldset className="space-y-3 border border-zinc-800 rounded-lg p-3">
            <legend className="text-sm font-medium text-zinc-400 px-2">Google Gemini</legend>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">API Key</label>
              <input
                type="password"
                placeholder={settings?.gemini_api_key_set ? "••••••• (gesetzt)" : "AI..."}
                onChange={(e) => setForm({ ...form, gemini_api_key: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Model</label>
              <input
                type="text"
                defaultValue={settings?.gemini_model || "gemini-1.5-flash"}
                onChange={(e) => setForm({ ...form, gemini_model: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </fieldset>

          {/* Anthropic Settings */}
          <fieldset className="space-y-3 border border-zinc-800 rounded-lg p-3">
            <legend className="text-sm font-medium text-zinc-400 px-2">Anthropic Claude</legend>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">API Key</label>
              <input
                type="password"
                placeholder={settings?.anthropic_api_key_set ? "••••••• (gesetzt)" : "sk-ant-..."}
                onChange={(e) => setForm({ ...form, anthropic_api_key: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Model</label>
              <input
                type="text"
                defaultValue={settings?.anthropic_model || "claude-3-5-sonnet-20241022"}
                onChange={(e) => setForm({ ...form, anthropic_model: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </fieldset>

          {/* Voice I/O Settings */}
          <fieldset className="space-y-3 border border-zinc-800 rounded-lg p-3">
            <legend className="text-sm font-medium text-zinc-400 px-2">Sprache / Voice</legend>

            {/* Recognition Language */}
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Erkennungssprache</label>
              <select
                value={voiceSettings.recognitionLang}
                onChange={(e) =>
                  onVoiceSettingsChange({ ...voiceSettings, recognitionLang: e.target.value })
                }
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="de-DE">Deutsch (de-DE)</option>
                <option value="en-US">English (en-US)</option>
                <option value="en-GB">English (en-GB)</option>
                <option value="fr-FR">Francais (fr-FR)</option>
                <option value="es-ES">Espanol (es-ES)</option>
                <option value="it-IT">Italiano (it-IT)</option>
                <option value="ja-JP">Japanese (ja-JP)</option>
                <option value="zh-CN">Chinese (zh-CN)</option>
              </select>
            </div>

            {/* TTS Voice */}
            <div>
              <label className="block text-xs text-zinc-500 mb-1">TTS Stimme</label>
              <select
                value={voiceSettings.voiceURI}
                onChange={(e) =>
                  onVoiceSettingsChange({ ...voiceSettings, voiceURI: e.target.value })
                }
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="">Standard (Browser-Standard)</option>
                {voices.map((v) => (
                  <option key={v.voiceURI} value={v.voiceURI}>
                    {v.name} ({v.lang})
                  </option>
                ))}
              </select>
            </div>

            {/* Speed */}
            <div>
              <label className="block text-xs text-zinc-500 mb-1">
                Geschwindigkeit: {voiceSettings.rate.toFixed(1)}x
              </label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={voiceSettings.rate}
                onChange={(e) =>
                  onVoiceSettingsChange({ ...voiceSettings, rate: parseFloat(e.target.value) })
                }
                className="w-full accent-blue-600"
              />
            </div>

            {/* Pitch */}
            <div>
              <label className="block text-xs text-zinc-500 mb-1">
                Tonhoehe: {voiceSettings.pitch.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={voiceSettings.pitch}
                onChange={(e) =>
                  onVoiceSettingsChange({ ...voiceSettings, pitch: parseFloat(e.target.value) })
                }
                className="w-full accent-blue-600"
              />
            </div>

            {/* Auto-Read toggle */}
            <div className="flex items-center justify-between">
              <label className="text-xs text-zinc-500">Antworten automatisch vorlesen</label>
              <button
                type="button"
                onClick={() =>
                  onVoiceSettingsChange({ ...voiceSettings, autoRead: !voiceSettings.autoRead })
                }
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  voiceSettings.autoRead ? "bg-blue-600" : "bg-zinc-700"
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    voiceSettings.autoRead ? "translate-x-[18px]" : "translate-x-[2px]"
                  }`}
                />
              </button>
            </div>
          </fieldset>

          {/* Error/Success Messages */}
          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 px-3 py-2 rounded-lg">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          {saved && (
            <div className="flex items-center gap-2 text-emerald-400 text-sm bg-emerald-900/20 px-3 py-2 rounded-lg">
              <CheckCircle size={16} />
              Einstellungen gespeichert!
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Save size={14} />
            {saving ? "Speichern..." : "Speichern"}
          </button>
        </div>
      </div>
    </div>
  );
}
