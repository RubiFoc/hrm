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
        staff: {
          title: "Staff Users",
          description: "Manage staff accounts and access levels.",
        },
        employeeKeys: {
          title: "Employee Keys",
          description: "Generate, review, and revoke employee registration keys.",
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
      adminEmployeeKeys: {
        title: "Employee Registration Keys",
        subtitle: "Manage employee key lifecycle with create/list/revoke operations.",
        loading: "Loading employee keys...",
        empty: "No employee keys found for current filters.",
        createSuccess: "Employee key created: {{key}}",
        revokeSuccess: "Employee key revoked successfully.",
        create: {
          targetRole: "Target role",
          ttlSeconds: "TTL seconds",
          submit: "Create key",
        },
        filters: {
          search: "Search by key id or employee key",
          targetRole: "Target role",
          status: "Status",
          createdBy: "Created by staff ID",
          any: "Any",
          apply: "Apply",
          reset: "Reset",
        },
        table: {
          employeeKey: "Employee key",
          targetRole: "Target role",
          status: "Status",
          expiresAt: "Expires at",
          usedAt: "Used at",
          revokedAt: "Revoked at",
          createdBy: "Created by",
          actions: "Actions",
        },
        status: {
          active: "Active",
          used: "Used",
          expired: "Expired",
          revoked: "Revoked",
        },
        actions: {
          revoke: "Revoke",
        },
        errors: {
          key_not_found: "Employee key was not found.",
          key_already_used: "Employee key is already used.",
          key_already_expired: "Employee key is already expired.",
          key_already_revoked: "Employee key is already revoked.",
          unsupported_role: "Selected role is not supported.",
          validation_failed: "Request validation failed. Please check entered values.",
          http_404: "Requested resource was not found.",
          http_409: "Operation conflicts with key lifecycle rules.",
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
        staff: {
          title: "Сотрудники",
          description: "Управление staff-аккаунтами и уровнями доступа.",
        },
        employeeKeys: {
          title: "Ключи регистрации",
          description: "Создание, просмотр и отзыв ключей регистрации сотрудников.",
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
      adminEmployeeKeys: {
        title: "Ключи регистрации сотрудников",
        subtitle: "Управление жизненным циклом ключей: create/list/revoke.",
        loading: "Загрузка ключей регистрации...",
        empty: "По текущим фильтрам ключи не найдены.",
        createSuccess: "Ключ регистрации создан: {{key}}",
        revokeSuccess: "Ключ регистрации успешно отозван.",
        create: {
          targetRole: "Целевая роль",
          ttlSeconds: "TTL в секундах",
          submit: "Создать ключ",
        },
        filters: {
          search: "Поиск по key id или employee key",
          targetRole: "Целевая роль",
          status: "Статус",
          createdBy: "Created by staff ID",
          any: "Любой",
          apply: "Применить",
          reset: "Сбросить",
        },
        table: {
          employeeKey: "Employee key",
          targetRole: "Целевая роль",
          status: "Статус",
          expiresAt: "Истекает",
          usedAt: "Использован",
          revokedAt: "Отозван",
          createdBy: "Кем создан",
          actions: "Действия",
        },
        status: {
          active: "Активен",
          used: "Использован",
          expired: "Истёк",
          revoked: "Отозван",
        },
        actions: {
          revoke: "Отозвать",
        },
        errors: {
          key_not_found: "Ключ регистрации не найден.",
          key_already_used: "Ключ регистрации уже использован.",
          key_already_expired: "Срок действия ключа регистрации истёк.",
          key_already_revoked: "Ключ регистрации уже отозван.",
          unsupported_role: "Выбранная роль не поддерживается.",
          validation_failed: "Ошибка валидации запроса. Проверьте введённые значения.",
          http_404: "Запрошенный ресурс не найден.",
          http_409: "Операция конфликтует с правилами жизненного цикла ключа.",
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
