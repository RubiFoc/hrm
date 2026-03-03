import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      appTitle: "HRM Recruitment Workspace",
      hrWorkspace: "HR Workspace",
      candidateWorkspace: "Candidate Workspace",
      uploadCv: "Upload CV",
      signProfile: "Confirm profile information",
      registerInterview: "Register for interview",
    },
  },
  ru: {
    translation: {
      appTitle: "HRM Платформа найма",
      hrWorkspace: "Рабочее место HR",
      candidateWorkspace: "Кабинет кандидата",
      uploadCv: "Загрузить CV",
      signProfile: "Подтвердить информацию о себе",
      registerInterview: "Зарегистрироваться на интервью",
    },
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: "ru",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});
