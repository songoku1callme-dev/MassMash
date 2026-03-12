/**
 * Capacitor Native Integration Hooks
 *
 * Provides React hooks for native mobile features:
 * - Network status detection (offline banner)
 * - Push notification registration
 * - Haptic feedback (quiz, confetti)
 * - Status bar styling
 * - App lifecycle events
 * - Share functionality
 *
 * These hooks gracefully degrade on web — they only activate
 * when running inside a Capacitor native shell (iOS/Android).
 */

import { useEffect, useState, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';

// ── Network Status ─────────────────────────────────────────

/** Whether the device currently has internet connectivity. */
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [networkType, setNetworkType] = useState<string>('unknown');

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) {
      // On web, use the browser's navigator.onLine
      setIsOnline(navigator.onLine);
      const handleOnline = () => setIsOnline(true);
      const handleOffline = () => setIsOnline(false);
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }

    // Native: use @capacitor/network
    let cleanup: (() => void) | undefined;

    (async () => {
      try {
        const { Network } = await import('@capacitor/network');
        const status = await Network.getStatus();
        setIsOnline(status.connected);
        setNetworkType(status.connectionType);

        const listener = await Network.addListener(
          'networkStatusChange',
          (s) => {
            setIsOnline(s.connected);
            setNetworkType(s.connectionType);
          },
        );
        cleanup = () => listener.remove();
      } catch {
        // Plugin not available — stay online
      }
    })();

    return () => cleanup?.();
  }, []);

  return { isOnline, networkType };
}

// ── Haptic Feedback ────────────────────────────────────────

/** Trigger haptic feedback on native devices (no-op on web). */
export function useHaptics() {
  const triggerImpact = useCallback(async (style: 'light' | 'medium' | 'heavy' = 'medium') => {
    if (!Capacitor.isNativePlatform()) return;
    try {
      const { Haptics, ImpactStyle } = await import('@capacitor/haptics');
      const styleMap = {
        light: ImpactStyle.Light,
        medium: ImpactStyle.Medium,
        heavy: ImpactStyle.Heavy,
      };
      await Haptics.impact({ style: styleMap[style] });
    } catch {
      // Plugin not available
    }
  }, []);

  const triggerNotification = useCallback(async (type: 'success' | 'warning' | 'error' = 'success') => {
    if (!Capacitor.isNativePlatform()) return;
    try {
      const { Haptics, NotificationType } = await import('@capacitor/haptics');
      const typeMap = {
        success: NotificationType.Success,
        warning: NotificationType.Warning,
        error: NotificationType.Error,
      };
      await Haptics.notification({ type: typeMap[type] });
    } catch {
      // Plugin not available
    }
  }, []);

  return { triggerImpact, triggerNotification };
}

// ── Status Bar ─────────────────────────────────────────────

/** Configure the native status bar appearance. */
export function useStatusBar() {
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    (async () => {
      try {
        const { StatusBar, Style } = await import('@capacitor/status-bar');
        await StatusBar.setStyle({ style: Style.Dark });
        if (Capacitor.getPlatform() === 'android') {
          await StatusBar.setBackgroundColor({ color: '#0f172a' });
        }
      } catch {
        // Plugin not available
      }
    })();
  }, []);
}

// ── App Lifecycle ──────────────────────────────────────────

/** Listen for app state changes (foreground/background). */
export function useAppLifecycle(
  onResume?: () => void,
  onPause?: () => void,
) {
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    let cleanupResume: (() => void) | undefined;
    let cleanupPause: (() => void) | undefined;

    (async () => {
      try {
        const { App } = await import('@capacitor/app');

        if (onResume) {
          const listener = await App.addListener('appStateChange', (state) => {
            if (state.isActive) onResume();
          });
          cleanupResume = () => listener.remove();
        }

        if (onPause) {
          const listener = await App.addListener('appStateChange', (state) => {
            if (!state.isActive) onPause();
          });
          cleanupPause = () => listener.remove();
        }
      } catch {
        // Plugin not available
      }
    })();

    return () => {
      cleanupResume?.();
      cleanupPause?.();
    };
  }, [onResume, onPause]);
}

// ── Share ──────────────────────────────────────────────────

/** Native share dialog for quiz results, achievements, etc. */
export function useNativeShare() {
  const share = useCallback(async (opts: { title: string; text: string; url?: string }) => {
    if (!Capacitor.isNativePlatform()) {
      // Web fallback: use navigator.share if available
      if (navigator.share) {
        await navigator.share(opts);
        return;
      }
      // Last resort: copy to clipboard
      await navigator.clipboard.writeText(opts.url || opts.text);
      return;
    }

    try {
      const { Share } = await import('@capacitor/share');
      await Share.share({
        title: opts.title,
        text: opts.text,
        url: opts.url,
        dialogTitle: opts.title,
      });
    } catch {
      // Plugin not available or user cancelled
    }
  }, []);

  return { share };
}

// ── Push Notifications ─────────────────────────────────────

/** Register for push notifications and return the device token. */
export function usePushNotifications(
  onToken?: (token: string) => void,
) {
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    let cleanup: (() => void) | undefined;

    (async () => {
      try {
        const { PushNotifications } = await import(
          '@capacitor/push-notifications'
        );

        const permResult = await PushNotifications.requestPermissions();
        if (permResult.receive !== 'granted') return;

        await PushNotifications.register();

        const listener = await PushNotifications.addListener(
          'registration',
          (token) => {
            onToken?.(token.value);
          },
        );
        cleanup = () => listener.remove();
      } catch {
        // Plugin not available
      }
    })();

    return () => cleanup?.();
  }, [onToken]);
}

// ── Platform Detection ─────────────────────────────────────

/** Returns the current platform: 'web', 'ios', or 'android'. */
export function usePlatform() {
  return Capacitor.getPlatform() as 'web' | 'ios' | 'android';
}

/** Whether the app is running inside a native Capacitor shell. */
export function useIsNative() {
  return Capacitor.isNativePlatform();
}
