"use client";

import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { api } from "../lib/api";

type TaskStatus = "running" | "done" | "error";
type Download = { label: string; url: string };
export type ResearchTask = {
  id: string;
  title: string;
  status: TaskStatus;
  progress: number;
  stage: string;
  message: string;
  result?: string;
  downloads?: Download[];
  error?: string;
  startedAt: number;
};
type ToolRequest = { feature: string; text: string; target_language?: string; model?: string; analysis_mode?: string };
type ProgressResponse = {
  status: "queued" | "running" | "done" | "error";
  progress: number;
  stage: string;
  message: string;
  result?: { summary?: string; downloads?: Download[]; balance?: number };
  error?: string;
};
type ToolProgressResponse = {
  status: "queued" | "running" | "done" | "error";
  progress: number;
  stage: string;
  message: string;
  result?: { summary?: string; balance?: number };
  error?: string;
};
type TaskContextValue = {
  tasks: ResearchTask[];
  submitting: boolean;
  startResearch: (form: FormData, title: string) => Promise<void>;
  startTool: (payload: ToolRequest, title: string) => void;
};

const TaskContext = createContext<TaskContextValue | null>(null);

function updateTask(tasks: ResearchTask[], incoming: ResearchTask) {
  return [incoming, ...tasks.filter((task) => task.id !== incoming.id)].slice(0, 12);
}

function announceBalance(balance?: number) {
  if (typeof balance === "number") {
    window.dispatchEvent(new CustomEvent("zhenzhi:balance", { detail: balance }));
  }
}

export function ResearchTaskProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<ResearchTask[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const patchTask = useCallback((id: string, patch: Partial<ResearchTask>) => {
    setTasks((current) => current.map((task) => task.id === id ? { ...task, ...patch } : task));
  }, []);

  const pollResearch = useCallback(async (taskId: string) => {
    const started = Date.now();
    while (Date.now() - started < 30 * 60 * 1000) {
      await new Promise((resolve) => window.setTimeout(resolve, 1800));
      try {
        const progress = await api<ProgressResponse>(`/api/v1/agent/progress/${taskId}`);
        const status: TaskStatus = progress.status === "done" ? "done" : progress.status === "error" ? "error" : "running";
        patchTask(taskId, {
          status,
          progress: progress.progress,
          stage: progress.stage,
          message: progress.message,
          result: progress.result?.summary,
          downloads: progress.result?.downloads,
          error: progress.error,
        });
        announceBalance(progress.result?.balance);
        if (status !== "running") return;
      } catch (reason) {
        patchTask(taskId, {
          status: "error",
          stage: "无法读取任务进度",
          message: "任务可能仍在后台运行，但当前无法恢复进度。",
          error: reason instanceof Error ? reason.message : "进度查询失败",
        });
        return;
      }
    }
    patchTask(taskId, {
      status: "error",
      stage: "等待超时",
      message: "任务已等待 30 分钟，请检查模型服务或重新提交。",
      error: "进度轮询超时",
    });
  }, [patchTask]);

  const pollTool = useCallback(async (taskId: string) => {
    const started = Date.now();
    while (Date.now() - started < 30 * 60 * 1000) {
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      try {
        const progress = await api<ToolProgressResponse>(`/api/v1/tools/tasks/${taskId}`);
        const status: TaskStatus = progress.status === "done" ? "done" : progress.status === "error" ? "error" : "running";
        patchTask(taskId, {
          status,
          progress: progress.progress,
          stage: progress.stage,
          message: progress.message,
          result: progress.result?.summary,
          error: progress.error,
        });
        announceBalance(progress.result?.balance);
        if (status !== "running") return;
      } catch (reason) {
        patchTask(taskId, {
          status: "error",
          stage: "无法读取任务进度",
          message: "任务可能仍在后台运行，但当前无法恢复进度。",
          error: reason instanceof Error ? reason.message : "进度查询失败",
        });
        return;
      }
    }
    patchTask(taskId, {
      status: "error",
      stage: "等待超时",
      message: "任务已等待 30 分钟，请检查模型服务或重新提交。",
      error: "进度轮询超时",
    });
  }, [patchTask]);

  const startResearch = useCallback(async (form: FormData, title: string) => {
    setSubmitting(true);
    const clientId = crypto.randomUUID();
    setTasks((current) => updateTask(current, {
      id: clientId,
      title,
      status: "running",
      progress: 0,
      stage: "正在上传",
      message: "上传进度来自浏览器实际发送字节数。",
      startedAt: Date.now(),
    }));
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("请先登录后再提交文献任务");
      const body = await new Promise<{ task_id: string }>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open("POST", "/api/v1/agent/research");
        request.setRequestHeader("Authorization", `Bearer ${token}`);
        request.upload.onprogress = (event) => {
          if (!event.lengthComputable) return;
          patchTask(clientId, {
            progress: Math.max(1, Math.min(15, Math.round(event.loaded / event.total * 15))),
            stage: "正在上传文献",
            message: `${Math.round(event.loaded / event.total * 100)}% 已上传`,
          });
        };
        request.onload = () => {
          let response: { task_id?: string; detail?: string } = {};
          try { response = JSON.parse(request.responseText) as { task_id?: string; detail?: string }; } catch { /* handled as an invalid response below */ }
          if (request.status < 200 || request.status >= 300 || !response.task_id) {
            reject(new Error(response.detail ?? `提交失败（HTTP ${request.status}）`));
            return;
          }
          resolve({ task_id: response.task_id });
        };
        request.onerror = () => reject(new Error("上传连接中断，请检查网络和后端服务"));
        request.onabort = () => reject(new Error("上传已取消"));
        request.send(form);
      });
      const task: ResearchTask = {
        id: body.task_id,
        title,
        status: "running",
        progress: 0,
        stage: "任务已提交",
        message: "后台正在接收任务进度；切换页面不会中断处理。",
        startedAt: Date.now(),
      };
      setTasks((current) => updateTask(current.filter((item) => item.id !== clientId), task));
      void pollResearch(task.id);
    } catch (reason) {
      patchTask(clientId, {
        status: "error",
        stage: "提交失败",
        message: reason instanceof Error ? reason.message : "上传失败",
        error: reason instanceof Error ? reason.message : "上传失败",
      });
      throw reason;
    } finally {
      setSubmitting(false);
    }
  }, [pollResearch]);

  const startTool = useCallback((payload: ToolRequest, title: string) => {
    const clientId = crypto.randomUUID();
    const task: ResearchTask = {
      id: clientId,
      title,
      status: "running",
      progress: 0,
      stage: "请求已发送",
      message: "正在等待真实模型响应；切换页面不会丢失结果。",
      startedAt: Date.now(),
    };
    setTasks((current) => updateTask(current, task));
    void api<{ task_id: string }>("/api/v1/tools/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then(({ task_id }) => {
      setTasks((current) => updateTask(current.filter((item) => item.id !== clientId), {
        ...task,
        id: task_id,
        stage: "任务已提交",
        message: "后台正在执行；切换页面不会中断处理。",
      }));
      void pollTool(task_id);
    }).catch((reason: unknown) => {
      patchTask(clientId, {
        status: "error",
        stage: "任务失败",
        message: reason instanceof Error ? reason.message : "任务失败，请检查服务状态",
        error: reason instanceof Error ? reason.message : "未知错误",
      });
    });
  }, [patchTask, pollTool]);

  const value = useMemo(() => ({ tasks, submitting, startResearch, startTool }), [tasks, submitting, startResearch, startTool]);
  return <TaskContext.Provider value={value}>{children}<ResearchTaskDock tasks={tasks} /></TaskContext.Provider>;
}

export function useResearchTasks() {
  const value = useContext(TaskContext);
  if (!value) throw new Error("useResearchTasks 必须在 ResearchTaskProvider 内使用");
  return value;
}

function ResearchTaskDock({ tasks }: { tasks: ResearchTask[] }) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const task = tasks.find((item) => item.status === "running") ?? tasks.find((item) => !dismissed.includes(item.id));
  if (!task) return null;

  return <aside className={`taskDock ${task.status}`} aria-live="polite">
    <div className="taskDockHeader">
      <span>{task.status === "running" ? "后台任务进行中" : task.status === "done" ? "任务已完成" : "任务未完成"}</span>
      {task.status !== "running" && <button onClick={() => setDismissed((value) => [...value, task.id])} aria-label="关闭任务通知">×</button>}
    </div>
    <strong>{task.title}</strong>
    {task.status !== "error" && <div className="taskDockProgress"><span className={task.progress === 0 && task.status === "running" ? "indeterminate" : ""} style={{ width: task.progress === 0 && task.status === "running" ? "35%" : `${Math.min(100, Math.max(4, task.progress))}%` }} /></div>}
    <small>{task.stage} · {task.message}</small>
    {task.error && <small className="taskDockError">{task.error}</small>}
    {task.result && <p>{task.result}</p>}
    {(task.downloads?.length || task.result) && <div className="taskDockLinks">
      {task.downloads?.map((item) => <a key={item.url} href={item.url}>{item.label} ↓</a>)}
      {task.result && <a href={`data:text/markdown;charset=utf-8,${encodeURIComponent(task.result)}`} download="真知任务结果.md">下载结果 ↓</a>}
    </div>}
  </aside>;
}
