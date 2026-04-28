import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Badge } from "./components/ui/badge";
import type { BadgeVariant } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Select } from "./components/ui/select";
import { Textarea } from "./components/ui/textarea";
import { ApiError, createApi } from "./lib/api";
import { cn, formatDate, roleLabel, statusLabel } from "./lib/utils";
import type {
  Group,
  InlineComment,
  StudentSubmission,
  SubmissionLanguage,
  Task,
  TaskDetail,
  TeacherSubmission,
  TestCaseCreate,
  User,
  UserRole,
} from "./types/api";

type View = "dashboard" | "profile" | "tasks" | "create-task" | "submissions" | "admin";
type Toast = {
  id: number;
  title: string;
  description?: string;
  variant?: "success" | "error";
};
type Notify = (toast: Omit<Toast, "id">) => void;
type Theme = "light" | "dark";

const tokenKey = "codecheck.token";
const themeKey = "codecheck.theme";
const toastDurationMs = 3500;
const refreshIntervalMs = 45_000;
const timeOptions = Array.from({ length: 24 * 12 }, (_, index) => {
  const hours = Math.floor(index / 12)
    .toString()
    .padStart(2, "0");
  const minutes = ((index % 12) * 5).toString().padStart(2, "0");
  return `${hours}:${minutes}`;
});

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenKey));
  const [user, setUser] = useState<User | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [studentSubmissions, setStudentSubmissions] = useState<StudentSubmission[]>([]);
  const [teacherSubmissions, setTeacherSubmissions] = useState<TeacherSubmission[]>([]);
  const [reviewQueueCount, setReviewQueueCount] = useState(0);
  const [taskReviewCounts, setTaskReviewCounts] = useState<Record<number, number>>({});
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [view, setView] = useState<View>("dashboard");
  const [message, setMessage] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [theme, setTheme] = useState<Theme>(() => {
    return localStorage.getItem(themeKey) === "dark" ? "dark" : "light";
  });
  const [isLoading, setIsLoading] = useState(false);
  const isRefreshingRef = useRef(false);

  const api = useMemo(() => createApi(token), [token]);

  async function loadAppData(nextUser?: User) {
    if (!token || isRefreshingRef.current) {
      return;
    }

    isRefreshingRef.current = true;
    setIsLoading(true);
    setMessage(null);
    try {
      const profile = nextUser ?? (await api.me());
      setUser(profile);

      const [groupData, taskData] = await Promise.all([api.groups(), api.tasks()]);
      setGroups(groupData);
      setTasks(taskData);

      if (profile.role === "admin") {
        setUsers(await api.users());
      }

      if (profile.role === "student") {
        setStudentSubmissions(await api.mySubmissions());
        setReviewQueueCount(0);
        setTaskReviewCounts({});
      } else {
        const submissionsByTask = await Promise.all(
          taskData.map((task) => api.taskSubmissions(task.id)),
        );
        const reviewCounts = Object.fromEntries(
          taskData.map((task, index) => [
            task.id,
            submissionsByTask[index].filter(
              (submission) => submission.status === "on_review" && submission.grade === null,
            ).length,
          ]),
        );
        setTaskReviewCounts(reviewCounts);
        setReviewQueueCount(Object.values(reviewCounts).reduce((sum, count) => sum + count, 0));
      }
    } catch (error) {
      handleError(error, setMessage);
      if (error instanceof ApiError && error.status === 401) {
        logout();
      }
    } finally {
      isRefreshingRef.current = false;
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      void loadAppData();
    }
  }, [token]);

  useEffect(() => {
    if (!token || !user) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void loadAppData();
    }, refreshIntervalMs);

    function refreshOnFocus() {
      if (document.visibilityState === "visible") {
        void loadAppData();
      }
    }

    document.addEventListener("visibilitychange", refreshOnFocus);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", refreshOnFocus);
    };
  }, [token, user?.id]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(themeKey, theme);
  }, [theme]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(() => setToast(null), toastDurationMs);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function notify(nextToast: Omit<Toast, "id">) {
    setToast({ ...nextToast, id: Date.now() });
  }

  function acceptToken(nextToken: string) {
    localStorage.setItem(tokenKey, nextToken);
    setToken(nextToken);
  }

  function logout() {
    localStorage.removeItem(tokenKey);
    setToken(null);
    setUser(null);
    setGroups([]);
    setUsers([]);
    setTasks([]);
    setStudentSubmissions([]);
    setTeacherSubmissions([]);
    setReviewQueueCount(0);
    setTaskReviewCounts({});
    setSelectedTask(null);
    setView("dashboard");
  }

  async function openTask(taskId: number) {
    setIsLoading(true);
    setMessage(null);
    try {
      const detail = await api.task(taskId);
      setSelectedTask(detail);
      setView("tasks");
      if (user?.role !== "student") {
        setTeacherSubmissions(await api.taskSubmissions(taskId));
      }
    } catch (error) {
      handleError(error, setMessage);
    } finally {
      setIsLoading(false);
    }
  }

  if (!token || !user) {
    return (
      <AuthScreen
        theme={theme}
        onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
        onToken={acceptToken}
      />
    );
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b bg-card/85 shadow-[0_10px_30px_hsl(222_38%_12%/0.08)] backdrop-blur-xl">
        <div className="app-container flex min-h-16 items-center justify-between gap-4 py-3">
          <div className="min-w-0">
            <p className="text-xl font-black tracking-tight text-primary">CodeCheck</p>
            <p className="truncate text-sm text-muted-foreground">
              {user.full_name} · {roleLabel(user.role)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              className="px-3 sm:px-4"
              variant="outline"
              onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? "Светлая" : "Тёмная"}
            </Button>
            <Button className="px-3 sm:px-4" variant="outline" onClick={logout}>
              Выйти
            </Button>
          </div>
        </div>
      </header>

      <div className="app-container grid gap-5 py-5 lg:grid-cols-[244px_minmax(0,1fr)]">
        <aside className="surface flex gap-1 overflow-x-auto rounded-lg p-2 lg:sticky lg:top-24 lg:block lg:h-fit lg:space-y-1 lg:overflow-visible lg:border-l-4 lg:border-l-primary">
          <NavButton active={view === "dashboard"} onClick={() => setView("dashboard")}>
            Обзор
          </NavButton>
          <NavButton active={view === "profile"} onClick={() => setView("profile")}>
            Профиль
          </NavButton>
          <NavButton active={view === "tasks"} onClick={() => setView("tasks")}>
            Задания
          </NavButton>
          {(user.role === "teacher" || user.role === "admin") && (
            <NavButton active={view === "create-task"} onClick={() => setView("create-task")}>
              Новое задание
            </NavButton>
          )}
          {user.role === "student" && (
            <NavButton active={view === "submissions"} onClick={() => setView("submissions")}>
              Решения
            </NavButton>
          )}
          {user.role === "admin" && (
            <NavButton active={view === "admin"} onClick={() => setView("admin")}>
              Панель администратора
            </NavButton>
          )}
        </aside>

        <main className="min-w-0 space-y-5">
          {message && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-900 shadow-sm dark:border-amber-800 dark:bg-amber-950/90 dark:text-amber-100">
              {message}
            </div>
          )}

          {view === "dashboard" && (
            <Dashboard
              user={user}
              groups={groups}
              tasks={tasks}
              studentSubmissions={studentSubmissions}
              reviewQueueCount={reviewQueueCount}
            />
          )}

          {view === "profile" && (
            <ProfileView
              api={api}
              user={user}
              groups={groups}
              setUser={setUser}
              setMessage={setMessage}
              notify={notify}
              onRefresh={loadAppData}
            />
          )}

          {view === "tasks" && (
            <TasksView
              api={api}
              user={user}
              groups={groups}
              tasks={tasks}
              studentSubmissions={studentSubmissions}
              taskReviewCounts={taskReviewCounts}
              selectedTask={selectedTask}
              teacherSubmissions={teacherSubmissions}
              setMessage={setMessage}
              notify={notify}
              onTaskDeleted={async () => {
                setSelectedTask(null);
                setTeacherSubmissions([]);
                await loadAppData();
              }}
              onOpenTask={openTask}
              onSubmissionsChanged={async () => {
                if (selectedTask) {
                  await openTask(selectedTask.id);
                }
                await loadAppData();
              }}
            />
          )}

          {view === "create-task" && (user.role === "teacher" || user.role === "admin") && (
            <CreateTaskView
              api={api}
              groups={groups}
              setMessage={setMessage}
              notify={notify}
              onCreated={async () => {
                await loadAppData();
                setView("tasks");
              }}
            />
          )}

          {view === "submissions" && (
            <SubmissionsView
              user={user}
              tasks={tasks}
              studentSubmissions={studentSubmissions}
              teacherSubmissions={teacherSubmissions}
              onOpenTask={openTask}
            />
          )}

          {view === "admin" && user.role === "admin" && (
            <AdminView
              api={api}
              users={users}
              groups={groups}
              currentUserId={user.id}
              setMessage={setMessage}
              notify={notify}
              onRefresh={loadAppData}
            />
          )}
        </main>
      </div>
      <ToastMessage toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

function AuthScreen({
  theme,
  onToggleTheme,
  onToken,
}: {
  theme: Theme;
  onToggleTheme: () => void;
  onToken: (token: string) => void;
}) {
  const api = useMemo(() => createApi(null), []);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage(null);
    try {
      const token =
        mode === "login"
          ? await api.login(username, password)
          : await api.register({
              username,
              full_name: fullName,
              password,
            });
      onToken(token.access_token);
    } catch (error) {
      handleError(error, setMessage);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <div className="absolute right-4 top-4">
        <Button variant="outline" onClick={onToggleTheme}>
          {theme === "dark" ? "Светлая" : "Тёмная"}
        </Button>
      </div>
      <Card className="section-shell w-full max-w-[460px]">
        <CardHeader>
          <CardTitle className="text-3xl text-primary">CodeCheck</CardTitle>
          <CardDescription className="leading-6">
            Платформа проверки программных решений.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-5 grid grid-cols-2 rounded-md border bg-muted/60 p-1">
            <Button
              variant={mode === "login" ? "default" : "ghost"}
              onClick={() => setMode("login")}
            >
              Вход
            </Button>
            <Button
              variant={mode === "register" ? "default" : "ghost"}
              onClick={() => setMode("register")}
            >
              Регистрация
            </Button>
          </div>
          <form className="space-y-4" onSubmit={submit}>
            <Field label="Логин">
              <Input value={username} onChange={(event) => setUsername(event.target.value)} />
            </Field>
            {mode === "register" && (
              <Field label="ФИО">
                <Input value={fullName} onChange={(event) => setFullName(event.target.value)} />
              </Field>
            )}
            <Field label="Пароль">
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            {message && <p className="text-sm text-destructive">{message}</p>}
            <Button className="w-full" type="submit" disabled={isSubmitting}>
              {mode === "login" ? "Войти" : "Создать аккаунт"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

function Dashboard({
  user,
  groups,
  tasks,
  studentSubmissions,
  reviewQueueCount,
}: {
  user: User;
  groups: Group[];
  tasks: Task[];
  studentSubmissions: StudentSubmission[];
  reviewQueueCount: number;
}) {
  const userGroup = groups.find((group) => group.id === user.group_id);
  const solvedTaskIds = new Set(studentSubmissions.map((submission) => submission.task_id));
  const studentPendingTasks = tasks.filter((task) => !solvedTaskIds.has(task.id)).length;
  const isStudent = user.role === "student";

  return (
    <section className="space-y-5">
      <div className="section-shell rounded-lg p-5">
        <h1 className="text-2xl font-semibold tracking-tight">Обзор</h1>
        {isStudent && (
          <p className="mt-1 text-sm text-muted-foreground">
            {userGroup ? `Группа: ${userGroup.title}` : "Группа не назначена"}
          </p>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {isStudent ? (
          <>
            <MetricCard label="Задания без решения" value={studentPendingTasks} />
            <MetricCard label="Отправлено решений" value={studentSubmissions.length} />
          </>
        ) : (
          <>
            <MetricCard label="Создано заданий" value={tasks.length} />
            <MetricCard label="Решения ждут оценки" value={reviewQueueCount} />
          </>
        )}
      </div>
    </section>
  );
}

function ProfileView({
  api,
  user,
  groups,
  setUser,
  setMessage,
  notify,
  onRefresh,
}: {
  api: ReturnType<typeof createApi>;
  user: User;
  groups: Group[];
  setUser: (user: User) => void;
  setMessage: (message: string | null) => void;
  notify: Notify;
  onRefresh: () => Promise<void>;
}) {
  const [fullName, setFullName] = useState(user.full_name);
  const [groupId, setGroupId] = useState(user.group_id?.toString() ?? "");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [isProfileSubmitting, setIsProfileSubmitting] = useState(false);
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false);

  async function updateProfile(event: FormEvent) {
    event.preventDefault();
    setIsProfileSubmitting(true);
    setMessage(null);
    try {
      const updatedUser = await api.updateMe({
        full_name: fullName,
        group_id: user.role === "student" && groupId ? Number(groupId) : undefined,
      });
      setUser(updatedUser);
      notify({
        title: "Профиль обновлён",
        description: "Изменения сохранены.",
        variant: "success",
      });
      await onRefresh();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    } finally {
      setIsProfileSubmitting(false);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setIsPasswordSubmitting(true);
    setMessage(null);
    try {
      const updatedUser = await api.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      });
      setUser(updatedUser);
      setOldPassword("");
      setNewPassword("");
      notify({
        title: "Пароль изменён",
        description: "Новый пароль будет использоваться при следующем входе.",
        variant: "success",
      });
    } catch (error) {
      handleActionError(error, setMessage, notify);
    } finally {
      setIsPasswordSubmitting(false);
    }
  }

  return (
    <section className="min-w-0 space-y-5">
      <div className="section-shell rounded-lg p-5">
        <h1 className="text-2xl font-semibold tracking-tight">Профиль</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {user.username} · {roleLabel(user.role)}
        </p>
      </div>

      <div className="grid min-w-0 items-stretch gap-5 xl:grid-cols-2">
        <Card className="flex h-full flex-col">
          <CardHeader className="border-b bg-muted/35">
            <CardTitle>Основные данные</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1">
            <form className="flex flex-1 flex-col space-y-4 pt-5" onSubmit={updateProfile}>
              <Field label="ФИО">
                <Input
                  required
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                />
              </Field>
              {user.role === "student" && (
                <Field label="Группа">
                  <Select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
                    <option value="">Без группы</option>
                    {groups.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.title}
                      </option>
                    ))}
                  </Select>
                </Field>
              )}
              <Button className="mt-auto w-fit" type="submit" disabled={isProfileSubmitting}>
                Сохранить
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="flex h-full flex-col">
          <CardHeader className="border-b bg-muted/35">
            <CardTitle>Пароль</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1">
            <form className="flex flex-1 flex-col space-y-4 pt-5" onSubmit={changePassword}>
              <Field label="Текущий пароль">
                <Input
                  required
                  type="password"
                  value={oldPassword}
                  onChange={(event) => setOldPassword(event.target.value)}
                />
              </Field>
              <Field label="Новый пароль">
                <Input
                  required
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </Field>
              <Button className="mt-auto w-fit" type="submit" disabled={isPasswordSubmitting}>
                Изменить пароль
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function TasksView({
  api,
  user,
  groups,
  tasks,
  studentSubmissions,
  taskReviewCounts,
  selectedTask,
  teacherSubmissions,
  setMessage,
  notify,
  onTaskDeleted,
  onOpenTask,
  onSubmissionsChanged,
}: {
  api: ReturnType<typeof createApi>;
  user: User;
  groups: Group[];
  tasks: Task[];
  studentSubmissions: StudentSubmission[];
  taskReviewCounts: Record<number, number>;
  selectedTask: TaskDetail | null;
  teacherSubmissions: TeacherSubmission[];
  setMessage: (message: string | null) => void;
  notify: Notify;
  onTaskDeleted: () => Promise<void>;
  onOpenTask: (taskId: number) => Promise<void>;
  onSubmissionsChanged: () => Promise<void>;
}) {
  const latestStudentSubmissionByTask = useMemo(() => {
    const byTask = new Map<number, StudentSubmission>();

    for (const submission of studentSubmissions) {
      const current = byTask.get(submission.task_id);
      if (!current || new Date(submission.created_at) > new Date(current.created_at)) {
        byTask.set(submission.task_id, submission);
      }
    }

    return byTask;
  }, [studentSubmissions]);

  function getTaskMarker(task: Task) {
    if (user.role === "student") {
      const latestSubmission = latestStudentSubmissionByTask.get(task.id);
      if (!latestSubmission) {
        return { label: "Нет решения", variant: "warning" as BadgeVariant };
      }
      if (latestSubmission.status === "failed") {
        return { label: "Нужно исправить", variant: "danger" as BadgeVariant };
      }
      return null;
    }

    const reviewCount = taskReviewCounts[task.id] ?? 0;
    if (reviewCount > 0) {
      return {
        label: `${reviewCount} ждут оценки`,
        variant: "warning" as BadgeVariant,
      };
    }

    return null;
  }

  return (
    <section className="min-w-0 space-y-5">
      <Card>
        <CardHeader className="border-b bg-muted/35">
          <CardTitle>Задания</CardTitle>
        </CardHeader>
        <CardContent className="pt-5">
          {tasks.length > 0 ? (
            <div className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {tasks.map((task) => {
                const marker = getTaskMarker(task);

                return (
                  <button
                    key={task.id}
                    className={cn(
                      "grid min-h-28 min-w-0 content-between rounded-lg border bg-card/80 p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/55 hover:bg-muted/55 hover:shadow-md",
                      selectedTask?.id === task.id && "border-primary bg-primary/10 shadow-md",
                    )}
                    onClick={() => onOpenTask(task.id)}
                  >
                    <div className="min-w-0 space-y-2">
                      <div className="flex min-w-0 items-start justify-between gap-2">
                        <p className="min-w-0 truncate font-medium">{task.title}</p>
                        {marker && (
                          <Badge className="shrink-0" variant={marker.variant}>
                            {marker.label}
                          </Badge>
                        )}
                      </div>
                      <p className="line-clamp-2 text-sm text-muted-foreground">{task.text}</p>
                    </div>
                    <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                      {user.role === "student" && task.created_by_full_name && (
                        <p className="truncate">Автор: {task.created_by_full_name}</p>
                      )}
                      <p className="truncate">
                        {task.deadline ? `Срок сдачи: ${formatDate(task.deadline)}` : formatDate(task.deadline)}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : user.role === "student" && user.group_id === null ? (
            <p className="text-sm text-muted-foreground">
              Чтобы увидеть задания, нужно выбрать группу во вкладке «Профиль».
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Заданий пока нет.</p>
          )}
        </CardContent>
      </Card>

      <div className="min-w-0">
        {selectedTask ? (
          <TaskDetailView
            api={api}
            user={user}
            task={selectedTask}
            groups={groups}
            teacherSubmissions={teacherSubmissions}
            setMessage={setMessage}
            notify={notify}
            onDeleted={onTaskDeleted}
            onSubmitted={onSubmissionsChanged}
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Выберите задание</CardTitle>
            </CardHeader>
          </Card>
        )}
      </div>
    </section>
  );
}

function CreateTaskView({
  api,
  groups,
  setMessage,
  notify,
  onCreated,
}: {
  api: ReturnType<typeof createApi>;
  groups: Group[];
  setMessage: (message: string | null) => void;
  notify: Notify;
  onCreated: () => Promise<void>;
}) {
  return (
    <section className="min-w-0 space-y-5">
      <div className="section-shell max-w-[1100px] rounded-lg p-5">
        <h1 className="text-2xl font-semibold tracking-tight">Новое задание</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Текст задания, срок сдачи, группа и автоматические тесты.
        </p>
      </div>
      <TaskCreateForm
        api={api}
        groups={groups}
        setMessage={setMessage}
        notify={notify}
        onCreated={onCreated}
      />
    </section>
  );
}

function TaskCreateForm({
  api,
  groups,
  setMessage,
  notify,
  onCreated,
}: {
  api: ReturnType<typeof createApi>;
  groups: Group[];
  setMessage: (message: string | null) => void;
  notify: Notify;
  onCreated: () => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [deadlineDate, setDeadlineDate] = useState("");
  const [deadlineTime, setDeadlineTime] = useState("23:55");
  const [groupId, setGroupId] = useState("");
  const [testCases, setTestCases] = useState<TestCaseCreate[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateTestCase(index: number, patch: Partial<TestCaseCreate>) {
    setTestCases((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage(null);
    try {
      await api.createTask({
        title,
        text,
        deadline: deadlineDate ? `${deadlineDate}T${deadlineTime}:00` : null,
        group_id: Number(groupId),
        test_cases: testCases,
      });
      setTitle("");
      setText("");
      setDeadlineDate("");
      setDeadlineTime("23:55");
      setGroupId("");
      setTestCases([]);
      notify({
        title: "Задание создано",
        description: "Оно появилось в списке заданий.",
        variant: "success",
      });
      await onCreated();
    } catch (error) {
      handleError(error, setMessage);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="max-w-[1100px]">
      <CardHeader className="border-b bg-muted/35">
        <CardTitle>Параметры задания</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-5 pt-5" onSubmit={submit}>
          <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_240px_320px]">
            <Field label="Название">
              <Input required value={title} onChange={(event) => setTitle(event.target.value)} />
            </Field>
            <Field label="Группа">
              <Select required value={groupId} onChange={(event) => setGroupId(event.target.value)}>
                <option value="">Выберите</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.slug}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Срок сдачи">
              <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_120px]">
                <Input
                  type="date"
                  value={deadlineDate}
                  onChange={(event) => setDeadlineDate(event.target.value)}
                />
                <Select
                  value={deadlineTime}
                  disabled={!deadlineDate}
                  onChange={(event) => setDeadlineTime(event.target.value)}
                >
                  {timeOptions.map((time) => (
                    <option key={time} value={time}>
                      {time}
                    </option>
                  ))}
                </Select>
              </div>
            </Field>
          </div>

          <Field label="Текст задания">
            <Textarea
              required
              className="min-h-[420px] font-mono text-[13px] leading-5"
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
          </Field>

          <div className="space-y-3 rounded-lg border bg-muted/35 p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">Автоматические тесты</p>
              <Button
                className="shrink-0"
                variant="outline"
                onClick={() =>
                  setTestCases((current) => [
                    ...current,
                    { input: "", output: "", is_hidden: false },
                  ])
                }
              >
                Добавить
              </Button>
            </div>
            {testCases.map((testCase, index) => (
              <div key={index} className="min-w-0 space-y-3 rounded-lg border bg-card/80 p-3 shadow-sm">
                <div className="grid min-w-0 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <Textarea
                    className="min-h-28 font-mono text-[13px]"
                    placeholder="stdin"
                    value={testCase.input}
                    onChange={(event) => updateTestCase(index, { input: event.target.value })}
                  />
                  <Textarea
                    className="min-h-28 font-mono text-[13px]"
                    placeholder="stdout"
                    value={testCase.output}
                    onChange={(event) => updateTestCase(index, { output: event.target.value })}
                  />
                </div>
                <label className="flex w-fit items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={testCase.is_hidden}
                    onChange={(event) =>
                      updateTestCase(index, { is_hidden: event.target.checked })
                    }
                  />
                  Скрытый тест
                </label>
              </div>
            ))}
          </div>

          <Button className="w-full sm:w-auto" type="submit" disabled={isSubmitting}>
            Создать
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function TaskDetailView({
  api,
  user,
  task,
  groups,
  teacherSubmissions,
  setMessage,
  notify,
  onDeleted,
  onSubmitted,
}: {
  api: ReturnType<typeof createApi>;
  user: User;
  task: TaskDetail;
  groups: Group[];
  teacherSubmissions: TeacherSubmission[];
  setMessage: (message: string | null) => void;
  notify: Notify;
  onDeleted: () => Promise<void>;
  onSubmitted: () => Promise<void>;
}) {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState<SubmissionLanguage>("python");
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const group = groups.find((item) => item.id === task.group_id);

  async function submitSolution(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      await api.createSubmission({ task_id: task.id, code, language });
      setCode("");
      notify({
        title: "Решение отправлено",
        description: "Отправлено на проверку.",
        variant: "success",
      });
      await onSubmitted();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  async function deleteTask() {
    setMessage(null);
    try {
      await api.deleteTask(task.id);
      setIsDeleteOpen(false);
      notify({
        title: "Задание удалено",
        description: "Список заданий обновлён.",
        variant: "success",
      });
      await onDeleted();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  return (
    <div className="min-w-0 space-y-5">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle>{task.title}</CardTitle>
              <CardDescription className="mt-1">
                {group?.title ?? `Группа #${task.group_id}`} ·{" "}
                {task.created_by_full_name ? `${task.created_by_full_name} · ` : ""}
                {task.deadline ? `Срок сдачи: ${formatDate(task.deadline)}` : formatDate(task.deadline)}
              </CardDescription>
            </div>
            {(user.role === "teacher" || user.role === "admin") && (
              <Button variant="destructive" onClick={() => setIsDeleteOpen(true)}>
                Удалить
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted p-4 text-sm leading-6">
            {task.text}
          </pre>
          <div className="space-y-2">
            <p className="text-sm font-medium">Тесты</p>
            {task.test_cases.map((testCase) => (
              <div
                key={testCase.id}
                className="min-w-0 space-y-2 rounded-lg border bg-muted/35 p-3"
              >
                {testCase.is_hidden && <Badge variant="warning">Скрытый</Badge>}
                <div className="grid min-w-0 gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <pre className="code-panel min-w-0 overflow-auto rounded bg-muted p-2 text-xs">
                    {testCase.input || "Пустой ввод"}
                  </pre>
                  <pre className="code-panel min-w-0 overflow-auto rounded bg-muted p-2 text-xs">
                    {testCase.output || "Пустой вывод"}
                  </pre>
                </div>
              </div>
            ))}
            {task.test_cases.length === 0 && (
              <p className="text-sm text-muted-foreground">Автоматические тесты не добавлены.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {user.role === "student" ? (
        <Card>
          <CardHeader>
            <CardTitle>Отправить решение</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={submitSolution}>
              <Field label="Язык">
                <Select
                  value={language}
                  onChange={(event) => setLanguage(event.target.value as SubmissionLanguage)}
                >
                  <option value="python">Python</option>
                  <option value="cpp">C++</option>
                  <option value="other">Другой</option>
                </Select>
              </Field>
              <Field label="Код">
                <CodeTextarea
                  required
                  value={code}
                  onChange={setCode}
                />
              </Field>
              <Button type="submit">Отправить</Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <TeacherSubmissionsPanel
          api={api}
          task={task}
          submissions={teacherSubmissions}
          setMessage={setMessage}
          notify={notify}
          onChanged={onSubmitted}
        />
      )}

      {isDeleteOpen && (
        <ConfirmDialog
          title="Удалить задание?"
          description="Задание, все автоматические тесты и решения по этому заданию будут удалены без возможности восстановления."
          confirmLabel="Удалить"
          onCancel={() => setIsDeleteOpen(false)}
          onConfirm={deleteTask}
        />
      )}
    </div>
  );
}

function TeacherSubmissionsPanel({
  api,
  task,
  submissions,
  setMessage,
  notify,
  onChanged,
}: {
  api: ReturnType<typeof createApi>;
  task: TaskDetail;
  submissions: TeacherSubmission[];
  setMessage: (message: string | null) => void;
  notify: Notify;
  onChanged: () => Promise<void>;
}) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const [grade, setGrade] = useState("");
  const [finalComment, setFinalComment] = useState("");
  const active = submissions.find((submission) => submission.id === activeId) ?? submissions[0];

  useEffect(() => {
    if (active) {
      setActiveId(active.id);
      setGrade(active.grade?.toString() ?? "");
      setFinalComment(active.final_comment ?? "");
    }
  }, [active?.id]);

  async function submitGrade(event: FormEvent) {
    event.preventDefault();
    if (!active) {
      return;
    }

    setMessage(null);
    try {
      await api.gradeSubmission(active.id, {
        grade: Number(grade),
        final_comment: finalComment,
      });
      notify({
        title: "Оценка сохранена",
        description: "Решение получило итоговый статус.",
        variant: "success",
      });
      await onChanged();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Решения по заданию</CardTitle>
      </CardHeader>
      <CardContent>
        {submissions.length === 0 ? (
          <p className="text-sm text-muted-foreground">Решений пока нет.</p>
        ) : (
          <div className="min-w-0 space-y-4">
            <div className="grid max-h-[260px] min-w-0 gap-2 overflow-y-auto pr-1 md:grid-cols-2 xl:grid-cols-3">
              {submissions.map((submission) => {
                const isLate = isSubmissionLate(submission, task);

                return (
                  <button
                    key={submission.id}
                    className={cn(
                      "w-full min-w-0 rounded-lg border bg-card/70 p-3 text-left text-sm shadow-sm transition-all hover:border-primary/50 hover:bg-muted/55",
                      active?.id === submission.id && "border-primary bg-primary/10 shadow-md",
                    )}
                    onClick={() => setActiveId(submission.id)}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <p className="truncate font-medium">
                        {submission.student_full_name ?? "Студент"}
                      </p>
                      {isLate && (
                        <Badge className="shrink-0" variant="danger">
                          После срока
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {statusLabel(submission.status)} · {formatDate(submission.created_at)}
                    </p>
                  </button>
                );
              })}
            </div>
            {active && (
              <div className="min-w-0 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={active.status} />
                  <Badge variant="outline">{active.language}</Badge>
                  {active.grade !== null && <Badge variant="secondary">{active.grade}/54</Badge>}
                  {isSubmissionLate(active, task) && (
                    <Badge variant="danger">Решение отправлено после срока сдачи</Badge>
                  )}
                </div>
                <CodeViewer code={active.code} comments={active.inline_comments} />
                {active.test_result && <ResultBlock title="Автоматические тесты" value={active.test_result} />}
                {active.llm_comment && <ResultBlock title="LLM-анализ" value={active.llm_comment} />}
                <form
                  className="grid min-w-0 gap-3"
                  onSubmit={submitGrade}
                >
                  <div className="w-24">
                    <Field label="Оценка">
                      <Input
                        required
                        type="number"
                        min="1"
                        max="54"
                        value={grade}
                        onChange={(event) => setGrade(event.target.value)}
                      />
                    </Field>
                  </div>
                  <Field label="Финальный комментарий">
                    <Textarea
                      required
                      className="min-h-36"
                      value={finalComment}
                      onChange={(event) => setFinalComment(event.target.value)}
                    />
                  </Field>
                  <div className="flex justify-end">
                    <Button className="h-9 px-3" type="submit">
                      Оценить
                    </Button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SubmissionsView({
  user,
  tasks,
  studentSubmissions,
  teacherSubmissions,
  onOpenTask,
}: {
  user: User;
  tasks: Task[];
  studentSubmissions: StudentSubmission[];
  teacherSubmissions: TeacherSubmission[];
  onOpenTask: (taskId: number) => Promise<void>;
}) {
  const submissions = user.role === "student" ? studentSubmissions : teacherSubmissions;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Решения</CardTitle>
        <CardDescription>{user.role === "student" ? "История решений." : "Проверка решений."}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {submissions.map((submission) => {
          const task = tasks.find((item) => item.id === submission.task_id);
          return (
            <div
              key={submission.id}
              className="grid gap-3 rounded-lg border bg-card/70 p-4 shadow-sm md:grid-cols-[1fr_auto]"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{task?.title ?? `Задание #${submission.task_id}`}</p>
                  <StatusBadge status={submission.status} />
                  {submission.grade !== null && (
                    <Badge variant="secondary">{submission.grade}/54</Badge>
                  )}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {submission.language} · {formatDate(submission.created_at)}
                </p>
                {submission.final_comment && (
                  <p className="mt-2 text-sm">{submission.final_comment}</p>
                )}
              </div>
              <Button variant="outline" onClick={() => onOpenTask(submission.task_id)}>
                Открыть задание
              </Button>
            </div>
          );
        })}
        {submissions.length === 0 && (
          <p className="text-sm text-muted-foreground">Данных пока нет.</p>
        )}
      </CardContent>
    </Card>
  );
}

function AdminView({
  api,
  users,
  groups,
  currentUserId,
  setMessage,
  notify,
  onRefresh,
}: {
  api: ReturnType<typeof createApi>;
  users: User[];
  groups: Group[];
  currentUserId: number;
  setMessage: (message: string | null) => void;
  notify: Notify;
  onRefresh: () => Promise<void>;
}) {
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");

  async function createGroup(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      await api.createGroup({ slug, title });
      setSlug("");
      setTitle("");
      notify({
        title: "Группа создана",
        description: "Список групп обновлён.",
        variant: "success",
      });
      await onRefresh();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  async function deleteGroup(id: number) {
    setMessage(null);
    try {
      await api.deleteGroup(id);
      notify({
        title: "Группа удалена",
        description: "Список групп обновлён.",
        variant: "success",
      });
      await onRefresh();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  async function updateRole(userId: number, role: UserRole) {
    setMessage(null);
    try {
      await api.updateUser(userId, { role });
      notify({
        title: "Роль изменена",
        description: "Права пользователя обновлены.",
        variant: "success",
      });
      await onRefresh();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  async function deleteUser(userId: number) {
    setMessage(null);
    try {
      await api.deleteUser(userId);
      notify({
        title: "Пользователь удалён",
        description: "Список пользователей обновлён.",
        variant: "success",
      });
      await onRefresh();
    } catch (error) {
      handleActionError(error, setMessage, notify);
    }
  }

  const groupById = new Map(groups.map((group) => [group.id, group]));

  return (
    <section className="min-w-0 space-y-5">
      <div className="section-shell rounded-lg p-5">
        <h1 className="text-2xl font-semibold tracking-tight">Панель администратора</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Пользователи, роли и учебные группы.
        </p>
      </div>

      <Card>
        <CardHeader className="border-b bg-muted/35">
          <CardTitle>Новая группа</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid min-w-0 gap-3 pt-5 md:grid-cols-[220px_minmax(0,1fr)_auto]"
            onSubmit={createGroup}
          >
            <Field label="Код группы">
              <Input required value={slug} onChange={(event) => setSlug(event.target.value)} />
            </Field>
            <Field label="Название">
              <Input required value={title} onChange={(event) => setTitle(event.target.value)} />
            </Field>
            <div className="flex items-end">
              <Button className="w-full md:w-auto" type="submit">
                Создать
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <CardHeader className="border-b bg-muted/35">
            <CardTitle>Группы</CardTitle>
            <CardDescription>{groups.length} всего</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[560px] space-y-2 overflow-y-auto pt-5">
            {groups.map((group) => (
              <div
                key={group.id}
                className="flex min-w-0 items-center justify-between gap-3 rounded-lg border bg-card/70 p-3 shadow-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{group.title}</p>
                  <p className="text-xs text-muted-foreground">
                    #{group.id} · код {group.slug}
                  </p>
                </div>
                <Button className="shrink-0" variant="outline" onClick={() => deleteGroup(group.id)}>
                  Удалить
                </Button>
              </div>
            ))}
            {groups.length === 0 && (
              <p className="text-sm text-muted-foreground">Группы ещё не созданы.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b bg-muted/35">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Пользователи</CardTitle>
                <CardDescription>{users.length} всего</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="max-h-[680px] overflow-y-auto pt-5">
            <div className="space-y-2">
              {users.map((item) => {
                const group = item.group_id ? groupById.get(item.group_id) : null;

                return (
                  <div
                    key={item.id}
                    className="grid min-w-0 gap-3 rounded-lg border bg-card/70 p-3 shadow-sm lg:grid-cols-[minmax(0,1fr)_190px_110px]"
                  >
                    <div className="min-w-0">
                      <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <p className="truncate font-medium">{item.full_name}</p>
                        <Badge variant="outline">{roleLabel(item.role)}</Badge>
                      </div>
                      <p className="mt-1 truncate text-sm text-muted-foreground">
                        {item.username} · {group?.title ?? "группа не назначена"}
                      </p>
                    </div>
                    <Select
                      value={item.role}
                      onChange={(event) => updateRole(item.id, event.target.value as UserRole)}
                    >
                      <option value="student">Студент</option>
                      <option value="teacher">Преподаватель</option>
                      <option value="admin">Администратор</option>
                    </Select>
                    <Button
                      className="w-full"
                      variant="destructive"
                      disabled={item.id === currentUserId}
                      onClick={() => deleteUser(item.id)}
                    >
                      Удалить
                    </Button>
                  </div>
                );
              })}
              {users.length === 0 && (
                <p className="text-sm text-muted-foreground">Пользователей пока нет.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      {label}
      {children}
    </label>
  );
}

function CodeTextarea({
  value,
  onChange,
  required,
}: {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  const lineCount = Math.max(1, value.split("\n").length);

  return (
    <div className="grid min-h-[420px] min-w-0 grid-cols-[56px_minmax(0,1fr)] overflow-hidden rounded-lg border bg-card/90 shadow-inner focus-within:ring-2 focus-within:ring-ring">
      <div className="code-panel select-none overflow-hidden border-r bg-muted/70 py-3 text-right font-mono text-[13px] leading-5 text-muted-foreground">
        {Array.from({ length: lineCount }, (_, index) => (
          <div key={index} className="px-3">
            {index + 1}
          </div>
        ))}
      </div>
      <textarea
        required={required}
        className="code-panel min-h-[420px] w-full min-w-0 resize-y border-0 bg-card/90 px-3 py-3 font-mono text-[13px] leading-5 outline-none"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function CodeViewer({
  code,
  comments,
}: {
  code: string;
  comments?: InlineComment[];
}) {
  const lines = code.length > 0 ? code.split("\n") : [""];
  const highlightedLines = new Set<number>();
  const rowHeightPx = 24;
  const gutterWidthPx = 56;
  const codeMinWidthPx = 760;
  const commentWidthPx = 300;

  for (const comment of comments ?? []) {
    const line = Math.max(1, comment.line_start);
    const end = Math.max(line, comment.line_end ?? line);
    for (let lineNumber = line; lineNumber <= end; lineNumber += 1) {
      highlightedLines.add(lineNumber);
    }
  }

  return (
    <div className="code-panel min-h-[420px] max-h-[640px] min-w-0 overflow-auto rounded-lg border bg-card/90 shadow-inner">
      <div
        className="relative"
        style={{
          minWidth: gutterWidthPx + codeMinWidthPx,
          minHeight: 420,
          height: Math.max(420, lines.length * rowHeightPx),
        }}
      >
        <div
          className="absolute inset-y-0 left-0 border-r bg-muted/70"
          style={{ width: gutterWidthPx }}
        />
        {lines.map((line, index) => {
          const lineNumber = index + 1;
          const isHighlighted = highlightedLines.has(lineNumber);

          return (
            <div
              key={lineNumber}
              className={cn(
                "absolute left-0 grid grid-cols-[56px_minmax(0,1fr)] font-mono text-[13px] leading-6",
                isHighlighted && "bg-amber-50 dark:bg-amber-950/40",
              )}
              style={{
                top: index * rowHeightPx,
                height: rowHeightPx,
                width: "100%",
                minWidth: gutterWidthPx + codeMinWidthPx,
              }}
            >
              <div
                className={cn(
                  "select-none border-r px-3 text-right text-muted-foreground",
                  isHighlighted && "bg-amber-100/70 dark:bg-amber-900/50",
                )}
              >
                {lineNumber}
              </div>
              <pre className="overflow-visible whitespace-pre px-3 text-foreground">
                {line || " "}
              </pre>
            </div>
          );
        })}
        {(comments ?? []).map((comment, index) => (
          <div
            key={`${comment.line_start}-${index}`}
            className="absolute rounded border border-amber-200 bg-amber-100/95 px-2 py-1 font-sans text-xs leading-5 text-amber-950 shadow-sm dark:border-amber-700 dark:bg-amber-950/95 dark:text-amber-100"
            style={{
              top: (Math.max(1, comment.line_start) - 1) * rowHeightPx + 2,
              right: 12,
              width: commentWidthPx,
            }}
          >
            <span className="mr-2 font-medium text-amber-800 dark:text-amber-300">
              {formatCommentRange(comment)}
            </span>
            {comment.text}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatCommentRange(comment: InlineComment) {
  const end = comment.line_end ?? comment.line_start;
  return end > comment.line_start ? `${comment.line_start}-${end}` : comment.line_start;
}

function isSubmissionLate(submission: TeacherSubmission, task: TaskDetail) {
  return Boolean(task.deadline && new Date(submission.created_at) > new Date(task.deadline));
}

function ToastMessage({
  toast,
  onClose,
}: {
  toast: Toast | null;
  onClose: () => void;
}) {
  if (!toast) {
    return null;
  }

  const isError = toast.variant === "error";

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4">
      <div
        className={cn(
          "pointer-events-auto grid w-full max-w-md gap-1 rounded-lg border bg-card px-4 py-3 shadow-lg",
          isError
            ? "border-red-200 bg-red-50 text-red-950 dark:border-red-800 dark:bg-red-950 dark:text-red-100"
            : "border-emerald-200 bg-emerald-50 text-emerald-950 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
        )}
        role="status"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-semibold">{toast.title}</p>
          <button
            className="shrink-0 rounded px-1 text-lg leading-none opacity-70 hover:opacity-100"
            onClick={onClose}
            aria-label="Закрыть уведомление"
          >
            ×
          </button>
        </div>
        {toast.description && <p className="text-sm opacity-85">{toast.description}</p>}
      </div>
    </div>
  );
}

function ConfirmDialog({
  title,
  description,
  confirmLabel,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function confirm() {
    setIsSubmitting(true);
    await onConfirm();
    setIsSubmitting(false);
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-slate-950/40 px-4">
      <div className="w-full max-w-md rounded-lg border bg-card/95 p-5 shadow-2xl backdrop-blur">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Отмена
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={isSubmitting}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="section-shell">
      <CardHeader className="pt-6">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-4xl text-primary">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function NavButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={cn(
        "flex h-10 w-full items-center rounded-md px-3 text-sm font-semibold transition-all hover:bg-muted/70",
        active && "bg-primary text-primary-foreground shadow-sm shadow-primary/25 hover:bg-primary",
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant: BadgeVariant =
    status === "passed"
      ? "success"
      : status === "failed"
        ? "danger"
        : status === "analyzing"
          ? "warning"
          : "secondary";

  return <Badge variant={variant}>{statusLabel(status)}</Badge>;
}

function ResultBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{title}</p>
      <pre className="code-panel min-h-32 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border bg-muted/55 p-4 text-sm">
        {value}
      </pre>
    </div>
  );
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Не удалось выполнить действие";
}

function handleError(error: unknown, setMessage: (message: string | null) => void) {
  setMessage(getErrorMessage(error));
}

function handleActionError(
  error: unknown,
  setMessage: (message: string | null) => void,
  notify: Notify,
) {
  const message = getErrorMessage(error);
  setMessage(message);
  notify({
    title: "Действие не выполнено",
    description: message,
    variant: "error",
  });
}

export default App;
