import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";

// Landing & Auth
import { LandingPage } from "./pages/landing/LandingPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { VerifyEmailPage } from "./pages/auth/VerifyEmailPage";
import { ForgotPasswordPage } from "./pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/auth/ResetPasswordPage";
import { WorkspaceSetupPage } from "./pages/onboarding/WorkspaceSetupPage";

// Protected App Pages
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { ProductListPage } from "./pages/products/ProductListPage";
import { ProductDetailPage } from "./pages/products/ProductDetailPage";
import { ProductComparisonPage } from "./pages/products/ProductComparisonPage";
import { CategoriesPage } from "./pages/categories/CategoriesPage";
import { PlatformsPage } from "./pages/platforms/PlatformsPage";
import { WatchlistPage } from "./pages/watchlist/WatchlistPage";
import { AlertsPage } from "./pages/alerts/AlertsPage";
import { NotificationsPage } from "./pages/notifications/NotificationsPage";
import { ReportsListPage } from "./pages/reports/ReportsListPage";
import { ReportGenerationPage } from "./pages/reports/ReportGenerationPage";
import { ReportDetailPage } from "./pages/reports/ReportDetailPage";
import { DataSourcesPage } from "./pages/data_sources/DataSourcesPage";
import { GlobalSearchPage } from "./pages/search/GlobalSearchPage";
import { SettingsPage } from "./pages/settings/SettingsPage";

// Route Guard component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <Routes>
      {/* Public Landing */}
      <Route path="/" element={<LandingPage />} />

      {/* Auth Routes with AuthLayout as parent route */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* Onboarding */}
      <Route
        path="/workspace-setup"
        element={
          <ProtectedRoute>
            <WorkspaceSetupPage />
          </ProtectedRoute>
        }
      />

      {/* Protected App Routes with AppLayout */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/products" element={<ProductListPage />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />
        <Route path="/product-comparison" element={<ProductComparisonPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
        <Route path="/platforms" element={<PlatformsPage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/reports" element={<ReportsListPage />} />
        <Route path="/reports/:id" element={<ReportDetailPage />} />
        <Route path="/report-generation" element={<ReportGenerationPage />} />
        <Route path="/data-sources" element={<DataSourcesPage />} />
        <Route path="/search" element={<GlobalSearchPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
