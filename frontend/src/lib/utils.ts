export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value?: string | null) {
  if (!value) {
    return "Без срока сдачи";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Europe/Moscow",
  }).format(new Date(value)) + " МСК";
}

export function roleLabel(role: string) {
  const labels: Record<string, string> = {
    student: "Студент",
    teacher: "Преподаватель",
    admin: "Администратор",
  };

  return labels[role] ?? role;
}

export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    submitted: "Отправлено",
    analyzing: "Анализ",
    on_review: "На проверке",
    passed: "Зачтено",
    failed: "Не зачтено",
  };

  return labels[status] ?? status;
}
