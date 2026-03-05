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
        open: "Open",
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
      adminStaff: {
        title: "Staff Management",
        subtitle: "Manage role and active-state for staff accounts with server-side filters.",
        loading: "Loading staff list...",
        empty: "No staff accounts found for current filters.",
        updateSuccess: "Staff account updated successfully.",
        filters: {
          search: "Search by login or email",
          role: "Role",
          isActive: "Status",
          any: "Any",
          active: "Active",
          inactive: "Inactive",
          apply: "Apply",
          reset: "Reset",
        },
        table: {
          login: "Login",
          email: "Email",
          role: "Role",
          active: "Active",
          actions: "Actions",
        },
        roles: {
          admin: "Admin",
          hr: "HR",
          manager: "Manager",
          employee: "Employee",
          leader: "Leader",
          accountant: "Accountant",
        },
        status: {
          active: "Active",
          inactive: "Inactive",
        },
        actions: {
          save: "Save",
        },
        errors: {
          staff_not_found: "Staff account was not found.",
          unsupported_role: "Selected role is not supported.",
          empty_patch: "No changes were provided for update.",
          self_modification_forbidden:
            "You cannot demote or deactivate your own admin account.",
          last_admin_protection:
            "Operation blocked: the last active admin account must remain active.",
          validation_failed: "Request validation failed. Please check entered values.",
          http_404: "Requested resource was not found.",
          http_409: "Operation conflicts with a safety policy rule.",
          http_422: "Request validation failed. Please check entered values.",
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
        open: "Открыть",
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
      adminStaff: {
        title: "Управление сотрудниками",
        subtitle: "Управление ролью и активностью staff-аккаунтов с серверными фильтрами.",
        loading: "Загрузка списка сотрудников...",
        empty: "По текущим фильтрам сотрудники не найдены.",
        updateSuccess: "Данные сотрудника успешно обновлены.",
        filters: {
          search: "Поиск по login или email",
          role: "Роль",
          isActive: "Статус",
          any: "Любой",
          active: "Активные",
          inactive: "Неактивные",
          apply: "Применить",
          reset: "Сбросить",
        },
        table: {
          login: "Логин",
          email: "Email",
          role: "Роль",
          active: "Активен",
          actions: "Действия",
        },
        roles: {
          admin: "Админ",
          hr: "HR",
          manager: "Менеджер",
          employee: "Сотрудник",
          leader: "Руководитель",
          accountant: "Бухгалтер",
        },
        status: {
          active: "Активен",
          inactive: "Неактивен",
        },
        actions: {
          save: "Сохранить",
        },
        errors: {
          staff_not_found: "Staff-аккаунт не найден.",
          unsupported_role: "Выбранная роль не поддерживается.",
          empty_patch: "Для обновления не переданы изменения.",
          self_modification_forbidden:
            "Нельзя понизить свою роль admin или деактивировать собственный аккаунт.",
          last_admin_protection:
            "Операция заблокирована: последний активный admin должен оставаться активным.",
          validation_failed: "Ошибка валидации запроса. Проверьте введённые значения.",
          http_404: "Запрошенный ресурс не найден.",
          http_409: "Операция конфликтует с правилом безопасности.",
          http_422: "Ошибка валидации запроса. Проверьте введённые значения.",
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
