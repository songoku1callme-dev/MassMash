import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'de.lumnos.app',
  appName: 'Lumnos',
  webDir: 'dist',
  server: {
    // Production: uses built files from dist/
    // Native apps use HTTPS scheme for secure contexts
    androidScheme: 'https',
    iosScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#0f172a', // Lumnos Dark BG
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    Keyboard: {
      resize: 'body',
      style: 'dark',
    },
    StatusBar: {
      style: 'dark', // Light text on dark background
      backgroundColor: '#0f172a',
    },
  },
};

export default config;
