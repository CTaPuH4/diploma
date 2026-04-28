export type UserRole = "student" | "teacher" | "admin";

export type SubmissionStatus =
  | "submitted"
  | "analyzing"
  | "on_review"
  | "passed"
  | "failed";

export type SubmissionLanguage = "python" | "cpp" | "other";

export type Token = {
  access_token: string;
  token_type: "bearer";
};

export type User = {
  id: number;
  username: string;
  full_name: string;
  role: UserRole;
  group_id: number | null;
};

export type Group = {
  id: number;
  slug: string;
  title: string;
};

export type TestCase = {
  id: number;
  input: string;
  output: string;
  is_hidden: boolean;
};

export type TestCaseCreate = {
  input: string;
  output: string;
  is_hidden: boolean;
};

export type Task = {
  id: number;
  title: string;
  text: string;
  deadline: string | null;
  group_id: number;
  created_by_id: number;
  created_by_full_name: string | null;
};

export type TaskDetail = Task & {
  test_cases: TestCase[];
};

export type TaskCreate = {
  title: string;
  text: string;
  deadline: string | null;
  group_id: number;
  test_cases: TestCaseCreate[];
};

export type InlineComment = {
  line_start: number;
  line_end: number | null;
  text: string;
};

export type SubmissionBase = {
  task_id: number;
  code: string;
  language: SubmissionLanguage;
};

export type StudentSubmission = SubmissionBase & {
  id: number;
  status: SubmissionStatus;
  final_comment: string | null;
  grade: number | null;
  created_at: string;
  inline_comments: InlineComment[];
};

export type TeacherSubmission = StudentSubmission & {
  user_id: number;
  test_result: string | null;
  llm_comment: string | null;
  student_full_name: string | null;
};

export type ApiErrorPayload = {
  detail?: string;
};
