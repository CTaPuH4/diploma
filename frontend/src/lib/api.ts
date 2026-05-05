import type {
  Group,
  StudentSubmission,
  SubmissionBase,
  Task,
  TaskCreate,
  TaskDetail,
  TeacherSubmission,
  Token,
  User,
  UserRole,
} from "../types/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type ValidationErrorItem = {
  msg?: string;
  loc?: Array<string | number>;
  type?: string;
};

const fieldLabels: Record<string, string> = {
  username: "Логин",
  password: "Пароль",
  old_password: "Текущий пароль",
  new_password: "Новый пароль",
  full_name: "ФИО",
  group_id: "Группа",
  title: "Название",
  text: "Текст",
  deadline: "Срок сдачи",
  test_cases: "Автоматические тесты",
  input: "Входные данные",
  output: "Выходные данные",
  code: "Код",
  language: "Язык",
  task_id: "Задание",
  final_comment: "Финальный комментарий",
  grade: "Оценка",
  slug: "Код группы",
  role: "Роль",
};

function fieldLabel(item: ValidationErrorItem) {
  const loc = item.loc ?? [];
  const field = loc[loc.length - 1];
  return typeof field === "string" ? (fieldLabels[field] ?? field) : "Поле";
}

function localizeValidationError(item: ValidationErrorItem) {
  const label = fieldLabel(item);
  const type = item.type ?? "";
  const msg = item.msg ?? "";

  if (type.includes("missing") || msg === "Field required") {
    return `${label}: обязательное поле`;
  }
  if (type.includes("int_parsing") || msg.includes("valid integer")) {
    return `${label}: введите целое число`;
  }
  if (type.includes("datetime") || msg.includes("valid datetime")) {
    return `${label}: неверный формат даты и времени`;
  }
  if (type.includes("greater_than_equal")) {
    return `${label}: значение слишком маленькое`;
  }
  if (type.includes("less_than_equal")) {
    return `${label}: значение слишком большое`;
  }
  if (type.includes("enum")) {
    return `${label}: недопустимое значение`;
  }
  if (msg) {
    return `${label}: ${msg}`;
  }

  return `${label}: неверное значение`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail
              .map((item: ValidationErrorItem) => localizeValidationError(item))
              .filter(Boolean)
              .join("; ")
          : "Ошибка запроса";
    throw new ApiError(response.status, detail);
  }

  return data as T;
}

export function createApi(token: string | null) {
  async function request<T>(path: string, init: RequestInit = {}) {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type") && init.body) {
      headers.set("Content-Type", "application/json");
    }
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
    });

    return parseResponse<T>(response);
  }

  return {
    login(username: string, password: string) {
      const body = new URLSearchParams({ username, password });
      return request<Token>("/auth/login", {
        method: "POST",
        body,
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
    },
    register(payload: {
      username: string;
      full_name: string;
      password: string;
    }) {
      return request<Token>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    me() {
      return request<User>("/users/me");
    },
    updateMe(payload: { full_name?: string; group_id?: number | null }) {
      return request<User>("/users/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    changePassword(payload: { old_password: string; new_password: string }) {
      return request<User>("/users/change-password", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    users() {
      return request<User[]>("/users/");
    },
    updateUser(id: number, payload: { full_name?: string; role?: UserRole; group_id?: number }) {
      return request<User>(`/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    deleteUser(id: number) {
      return request<void>(`/users/${id}`, { method: "DELETE" });
    },
    groups() {
      return request<Group[]>("/groups/");
    },
    createGroup(payload: { slug: string; title: string }) {
      return request<Group>("/groups/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    deleteGroup(id: number) {
      return request<void>(`/groups/${id}`, { method: "DELETE" });
    },
    tasks() {
      return request<Task[]>("/tasks/");
    },
    task(id: number) {
      return request<TaskDetail>(`/tasks/${id}`);
    },
    createTask(payload: TaskCreate) {
      return request<Task>("/tasks/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    deleteTask(id: number) {
      return request<void>(`/tasks/${id}`, { method: "DELETE" });
    },
    createSubmission(payload: SubmissionBase) {
      return request<StudentSubmission>("/submissions/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    mySubmissions() {
      return request<StudentSubmission[]>("/submissions/me");
    },
    taskSubmissions(taskId: number) {
      return request<TeacherSubmission[]>(`/submissions/task/${taskId}`);
    },
    submission(id: number) {
      return request<TeacherSubmission>(`/submissions/${id}`);
    },
    gradeSubmission(id: number, payload: { final_comment: string; grade: number }) {
      return request<TeacherSubmission>(`/submissions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
  };
}
