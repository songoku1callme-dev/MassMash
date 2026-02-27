import { create } from "zustand";
import { Platform } from "react-native";
import type { SubscriptionTier, SubscriptionInfo } from "../types";
import {
  REVENUECAT_API_KEY_IOS,
  REVENUECAT_API_KEY_ANDROID,
  RC_ENTITLEMENT_ID,
} from "../constants/config";

interface SubscriptionState {
  subscription: SubscriptionInfo;
  isLoading: boolean;
  isPurchasing: boolean;
  initialize: () => Promise<void>;
  checkSubscription: () => Promise<void>;
  purchaseMonthly: () => Promise<boolean>;
  purchaseYearly: () => Promise<boolean>;
  restorePurchases: () => Promise<void>;
}

export const useSubscriptionStore = create<SubscriptionState>((set, get) => ({
  subscription: {
    tier: "free",
    expiry_date: null,
    is_trial: false,
  },
  isLoading: false,
  isPurchasing: false,

  initialize: async () => {
    try {
      // RevenueCat requires native modules - only initialize on native platforms
      if (Platform.OS === "web") return;

      const Purchases = require("react-native-purchases").default;
      const apiKey =
        Platform.OS === "ios"
          ? REVENUECAT_API_KEY_IOS
          : REVENUECAT_API_KEY_ANDROID;

      if (!apiKey) return;

      Purchases.configure({ apiKey });
      await get().checkSubscription();
    } catch (error) {
      console.error("Error initializing RevenueCat:", error);
    }
  },

  checkSubscription: async () => {
    try {
      if (Platform.OS === "web") return;

      const Purchases = require("react-native-purchases").default;
      set({ isLoading: true });

      const customerInfo = await Purchases.getCustomerInfo();
      const entitlement = customerInfo.entitlements.active[RC_ENTITLEMENT_ID];

      if (entitlement) {
        set({
          subscription: {
            tier: "pro" as SubscriptionTier,
            expiry_date: entitlement.expirationDate ?? null,
            is_trial: entitlement.periodType === "TRIAL",
          },
        });
      } else {
        set({
          subscription: {
            tier: "free" as SubscriptionTier,
            expiry_date: null,
            is_trial: false,
          },
        });
      }
    } catch (error) {
      console.error("Error checking subscription:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  purchaseMonthly: async () => {
    try {
      if (Platform.OS === "web") return false;

      const Purchases = require("react-native-purchases").default;
      set({ isPurchasing: true });

      const offerings = await Purchases.getOfferings();
      const monthlyPackage = offerings.current?.monthly;

      if (!monthlyPackage) {
        console.error("Monthly package not found");
        return false;
      }

      await Purchases.purchasePackage(monthlyPackage);
      await get().checkSubscription();
      return true;
    } catch (error: unknown) {
      const purchaseError = error as { userCancelled?: boolean };
      if (!purchaseError.userCancelled) {
        console.error("Error purchasing monthly:", error);
      }
      return false;
    } finally {
      set({ isPurchasing: false });
    }
  },

  purchaseYearly: async () => {
    try {
      if (Platform.OS === "web") return false;

      const Purchases = require("react-native-purchases").default;
      set({ isPurchasing: true });

      const offerings = await Purchases.getOfferings();
      const yearlyPackage = offerings.current?.annual;

      if (!yearlyPackage) {
        console.error("Yearly package not found");
        return false;
      }

      await Purchases.purchasePackage(yearlyPackage);
      await get().checkSubscription();
      return true;
    } catch (error: unknown) {
      const purchaseError = error as { userCancelled?: boolean };
      if (!purchaseError.userCancelled) {
        console.error("Error purchasing yearly:", error);
      }
      return false;
    } finally {
      set({ isPurchasing: false });
    }
  },

  restorePurchases: async () => {
    try {
      if (Platform.OS === "web") return;

      const Purchases = require("react-native-purchases").default;
      set({ isLoading: true });

      await Purchases.restorePurchases();
      await get().checkSubscription();
    } catch (error) {
      console.error("Error restoring purchases:", error);
    } finally {
      set({ isLoading: false });
    }
  },
}));
