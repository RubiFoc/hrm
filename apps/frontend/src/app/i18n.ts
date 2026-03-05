import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      appTitle: "HRM Recruitment Workspace",
      hrWorkspace: "HR Workspace",
      candidateWorkspace: "Candidate Workspace",
      adminWorkspace: "Admin Workspace",
      adminWorkspaceSubtitle: "Admin shell for operational controls and support diagnostics.",
      uploadCv: "Upload CV",
      signProfile: "Confirm profile information",
      registerInterview: "Register for interview",
      adminAccessDeniedTitle: "Admin access denied",
      adminAccessUnauthorizedDescription:
        "You are not authenticated. Sign in and try opening /admin again.",
      adminAccessForbiddenDescription:
        "Your account does not have admin permissions for this workspace.",
      backToWorkspace: "Back to workspace",
      adminCard: {
        users: {
          title: "Staff Users",
          description: "Manage staff accounts and access levels.",
        },
        audit: {
          title: "Audit Signals",
          description: "Review auth and security audit trails.",
        },
        settings: {
          title: "Platform Settings",
          description: "Inspect runtime and release configuration.",
        },
      },
    },
  },
  ru: {
    translation: {
      appTitle: "HRM Платформа найма",
      hrWorkspace: "Рабочее место HR",
      candidateWorkspace: "Кабинет кандидата",
      adminWorkspace: "Админ пространство",
      adminWorkspaceSubtitle: "Админ shell для операционного контроля и диагностики.",
      uploadCv: "Загрузить CV",
      signProfile: "Подтвердить информацию о себе",
      registerInterview: "Зарегистрироваться на интервью",
      adminAccessDeniedTitle: "Доступ в админ раздел запрещён",
      adminAccessUnauthorizedDescription:
        "Вы не аутентифицированы. Войдите в систему и повторите переход в /admin.",
      adminAccessForbiddenDescription:
        "У вашей учётной записи нет прав admin для этого рабочего пространства.",
      backToWorkspace: "Вернуться в рабочее пространство",
      adminCard: {
        users: {
          title: "Сотрудники",
          description: "Управление staff-аккаунтами и уровнями доступа.",
        },
        audit: {
          title: "Аудит сигналы",
          description: "Проверка auth и security audit следов.",
        },
        settings: {
          title: "Настройки платформы",
          description: "Просмотр runtime и release конфигурации.",
        },
      },
    },
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: "ru",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});
