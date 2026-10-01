"use client";
import { useEffect, useRef, useState } from "react";
import { put } from "@vercel/blob/client";
import type {
  Asset,
  Content,
  JobData,
  Output,
  Settings,
} from "@/lib/contracts";
import { MediaPreview } from "./MediaPreview";

type Job = JobData & {
  id: string;
  project_id: string;
  status: string;
  created_at: number;
  attempt: number;
  outputs: (Output & { url: string })[];
  events: { created_at: number; phase: string }[];
};
type Status = {
  mode: string;
  app_name: string;
  max_bytes: number;
  worker_online: boolean;
  seed_loaded: boolean;
  workers: {
    id: string;
    online: boolean;
    capabilities: Record<string, boolean>;
  }[];
};
type View =
  | "Contenido"
  | "Mis Reels"
  | "Editar"
  | "Biblioteca"
  | "Publicación"
  | "Ajustes";
const phases: Record<string, string> = {
  queued: "En cola",
  leased: "Preparando equipo",
  downloading: "Preparando archivos",
  probing: "Analizando video",
  transcribing: "Transcribiendo voz",
  planning: "Planificando edición",
  cutting: "Preparando cortes",
  rendering: "Componiendo video",
  qa: "Verificando exportación",
  uploading: "Guardando resultado",
  preview_ready: "Borrador disponible",
  final_ready: "Final disponible",
  failed: "Necesita atención",
  canceled: "Cancelado",
  cancel_requested: "Cancelando",
  reviewed: "Revisado",
};
const terminal = ["preview_ready", "final_ready", "failed", "canceled"];
const date = (stamp: number) =>
  new Date(stamp).toLocaleString("es-PY", {
    dateStyle: "short",
    timeStyle: "short",
  });
const uid = () => crypto.randomUUID();
async function api<T = unknown>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch("/api/" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      [data.error, ...(data.details || [])].filter(Boolean).join(" "),
    );
  return data;
}
export default function Studio() {
  const [view, setView] = useState<View>("Contenido"),
    [items, setItems] = useState<Content[]>([]),
    [assets, setAssets] = useState<Asset[]>([]),
    [jobs, setJobs] = useState<Job[]>([]),
    [status, setStatus] = useState<Status>();
  const [selected, setSelected] = useState("DEMO-TECNICA"),
    [jobId, setJobId] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [upload, setUpload] = useState<number | null>(null);
  const [assetId, setAssetId] = useState(""),
    [engine, setEngine] = useState<"ffmpeg" | "remotion">("remotion"),
    [mode, setMode] = useState<"recording" | "graphics">("recording"),
    [music, setMusic] = useState(""),
    [preserve, setPreserve] = useState(true);
  const [scenes, setScenes] = useState<Settings["scenes"]>([]),
    [words, setWords] = useState<NonNullable<Settings["words"]>>([]),
    [wordPage, setWordPage] = useState(0),
    [tab, setTab] = useState("Guion"),
    [reviewed, setReviewed] = useState(false);
  const [newTitle, setNewTitle] = useState(""),
    [newScript, setNewScript] = useState(""),
    [caption, setCaption] = useState(""),
    [script, setScript] = useState("");
  const [rights, setRights] = useState(""),
    [tags, setTags] = useState(""),
    [libraryType, setLibraryType] = useState("images");
  const video = useRef<HTMLVideoElement>(null),
    hydrated = useRef("");
  const item = items.find((c) => c.id === selected),
    current = jobs.find((j) => j.id === jobId),
    recording = assets.find((a) => a.id === assetId);
  const active = current && !terminal.includes(current.status);
  const result = current?.outputs[0];
  const projectJobs = current
    ? jobs.filter((j) => j.project_id === current.project_id)
    : [];
  const final = projectJobs.find((j) => j.status === "final_ready");
  async function refresh() {
    const [c, a, j, s] = await Promise.all([
      api<Content[]>("content"),
      api<Asset[]>("assets"),
      api<Job[]>("jobs"),
      api<Status>("status"),
    ]);
    setItems(c);
    setAssets(a);
    setJobs(j);
    setStatus(s);
  }
  useEffect(() => {
    let live = true;
    const tick = () =>
      refresh().catch((e) => {
        if (live) setError(e.message);
      });
    tick();
    const interval = setInterval(tick, 3500);
    return () => {
      live = false;
      clearInterval(interval);
    };
  }, []);
  useEffect(() => {
    if (item) {
      setCaption(item.caption);
      setScript(item.script);
    }
  }, [selected, items.length]);
  useEffect(() => {
    if (current?.report && hydrated.current !== current.id) {
      setWords(current.report.words.map((w) => ({ ...w })));
      setWordPage(0);
      hydrated.current = current.id;
    }
  }, [current]);
  async function act(task: () => Promise<void>) {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await task();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar.");
    } finally {
      setBusy(false);
    }
  }
  function choose(c: Content) {
    setSelected(c.id);
    setJobId("");
    setAssetId("");
    setWords([]);
    setScenes(c.id === "DEMO-TECNICA" ? [] : c.scenes);
    setMode("recording");
    setScript(c.script);
    setCaption(c.caption);
    setView("Editar");
    setTab("Guion");
    hydrated.current = "";
  }
  function openJob(j: Job) {
    setSelected(j.content.id);
    setJobId(j.id);
    setAssetId(j.settings.asset_id || "");
    setMode(j.settings.source_mode);
    setEngine(j.settings.engine);
    setScenes(j.settings.scenes);
    setMusic(j.settings.music_asset_id || "");
    setPreserve(j.settings.preserve_pauses);
    setView("Editar");
    setReviewed(false);
    hydrated.current = "";
  }
  async function uploadFile(file: File, library = false) {
    await act(async () => {
      if (file.size > (status?.max_bytes || 1024 ** 3))
        throw new Error("El archivo supera el límite configurado.");
      if (library && !rights.trim())
        throw new Error(
          "Indicá primero la procedencia y los derechos del recurso.",
        );
      const mime =
        file.type ||
        (
          {
            mov: "video/quicktime",
            m4v: "video/mp4",
            wav: "audio/wav",
            m4a: "audio/mp4",
          } as Record<string, string>
        )[file.name.split(".").pop()!.toLowerCase()];
      const reserved = await api<{
        id: string;
        key: string;
        mode: string;
        token?: string;
      }>("assets", "POST", {
        name: file.name,
        mime,
        size: file.size,
        rights: library ? rights : "Grabación propia subida por el propietario",
        approved: library,
        tags: library
          ? tags
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          : [],
        demo: library,
      });
      setUpload(0);
      try {
        if (reserved.mode === "remote") {
          await put(reserved.key, file, {
            access: "private",
            token: reserved.token!,
            contentType: mime,
            multipart: true,
            onUploadProgress: (e) => setUpload(Math.round(e.percentage)),
          });
          await api(`assets/${reserved.id}/complete`, "POST", {});
        } else
          await new Promise<void>((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("PUT", `/api/assets/${reserved.id}/file`);
            xhr.setRequestHeader("Content-Type", mime);
            xhr.upload.onprogress = (e) => {
              if (e.lengthComputable)
                setUpload(Math.round((e.loaded / e.total) * 100));
            };
            xhr.onload = () =>
              xhr.status < 300
                ? resolve()
                : reject(new Error("No se pudo guardar la subida."));
            xhr.onerror = () =>
              reject(new Error("Se perdió la conexión durante la subida."));
            xhr.send(file);
          });
        if (!library) {
          setAssetId(reserved.id);
          setMode("recording");
          setJobId("");
          setWords([]);
        }
        setNotice(
          library
            ? "Recurso guardado y aprobado."
            : "Grabación guardada. Ya podés generar un borrador.",
        );
      } finally {
        setUpload(null);
      }
    });
  }
  async function generate(kind: "preview" | "final") {
    await act(async () => {
      if (!item) throw new Error("Elegí un contenido.");
      const settings: Partial<Settings> = {
        engine,
        source_mode: mode,
        kind,
        scenes,
        preserve_pauses: preserve,
        duration: 8,
      };
      if (mode === "recording") settings.asset_id = assetId;
      if (music) {
        settings.music_asset_id = music;
        settings.music_volume = 0.1;
      }
      if (
        current?.report &&
        mode === "recording" &&
        current.settings.asset_id === assetId
      ) {
        settings.words = words;
        settings.source_sha256 = current.report.source_sha256;
        settings.parent_job_id = current.id;
      } else if (current) settings.parent_job_id = current.id;
      const j = await api<Job>("jobs", "POST", {
        content_id: item.id,
        settings,
        intent_key: uid(),
      });
      setJobId(j.id);
      setReviewed(false);
      setNotice("Trabajo en cola. Podés seguir usando Studio.");
    });
  }
  const badge = (j: Job) => (
    <span
      className={
        "badge " +
        (j.status.endsWith("_ready")
          ? "good"
          : j.status === "failed"
            ? "bad"
            : "")
      }
    >
      {j.reviewed ? "Revisado" : phases[j.status] || j.status}
    </span>
  );
  const contentCopy = (
    <>
      <div className="eyebrow">
        {item?.source_version} · {item?.id}
      </div>
      <h2>{item?.title}</h2>
      {item?.demo_gate && (
        <div className="warning">
          {item.demo_gate}
          <label>
            <input
              type="checkbox"
              checked={item.demo_approved}
              onChange={(e) =>
                act(async () => {
                  await api(`content/${selected}`, "PATCH", {
                    demo_approved: e.target.checked,
                  });
                })
              }
            />{" "}
            Verifiqué la demostración y sus afirmaciones
          </label>
        </div>
      )}
      <div className="tabs" role="tablist">
        {["Guion", "Plan visual", "Versiones"].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Guion" && (
        <>
          <label>
            Guion de esta versión
            <textarea
              rows={8}
              value={script}
              onChange={(e) => setScript(e.target.value)}
            />
          </label>
          <button
            className="text-button"
            disabled={busy}
            onClick={() =>
              act(async () => {
                await api(`content/${selected}`, "PATCH", { script });
                setNotice("Guion guardado; original conservado.");
              })
            }
          >
            Guardar versión del guion
          </button>
          {item?.hooks.map((h, i) => (
            <div className="hook" key={i}>
              <span>Hook {i + 1}</span>
              <p>{h}</p>
            </div>
          ))}
        </>
      )}
      {tab === "Plan visual" && (
        <>
          <p className="prewrap">
            {typeof item?.visual_plan === "string"
              ? item.visual_plan
              : JSON.stringify(item?.visual_plan, null, 2) ||
                "Sin plan visual original. Se conservará la cámara."}
          </p>
          <p className="muted">
            El guion no se convierte en subtítulos: se transcribe lo que
            realmente se escucha.
          </p>
        </>
      )}
      {tab === "Versiones" && (
        <div className="version-list">
          {projectJobs.length ? (
            projectJobs.map((j) => (
              <button key={j.id} onClick={() => openJob(j)}>
                <span>
                  {j.settings.kind === "final" ? "Final" : "Borrador"} ·{" "}
                  {date(j.created_at)}
                </span>
                {badge(j)}
              </button>
            ))
          ) : (
            <p className="muted">
              Las versiones aparecerán después del primer render.
            </p>
          )}
        </div>
      )}
    </>
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("Contenido");
          }}
        >
          <span className="brand-mark">D</span>
          <span>
            {status?.app_name || "DentFlow Studio"}
            <small>DE LA IDEA AL REEL</small>
          </span>
        </a>
        <nav aria-label="Navegación principal">
          {(
            [
              "Contenido",
              "Mis Reels",
              "Editar",
              "Biblioteca",
              "Publicación",
              "Ajustes",
            ] as View[]
          ).map((v, i) => (
            <button
              key={v}
              className={view === v ? "selected" : ""}
              onClick={() => setView(v)}
            >
              <span className="nav-number">0{i + 1}</span>
              {v}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div
            className={"status-dot " + (status?.worker_online ? "online" : "")}
          />
          <strong>
            {status?.worker_online ? "Equipo conectado" : "Esperando equipo"}
          </strong>
          <p>
            {status?.mode === "REMOTE_STUDIO"
              ? "Studio remoto · medios privados"
              : "Studio local · en tu computadora"}
          </p>
          <button onClick={() => setView("Ajustes")}>
            Ver estado del motor →
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span className="breadcrumb">
            Tu espacio de producción <span>/</span> {view}
          </span>
          <span className="pill">
            {status?.mode === "REMOTE_STUDIO" ? "Privado" : "Local"}{" "}
            <span>●</span>
          </span>
        </header>
        <div className="page">
          <div className="page-title">
            <div>
              <div className="eyebrow">DENTFLOW / STUDIO V3</div>
              <h1>
                {view === "Contenido"
                  ? "Una idea. Un buen Reel."
                  : view === "Editar"
                    ? "Dale forma a tu grabación."
                    : view === "Mis Reels"
                      ? "Tus Reels, cada versión."
                      : view === "Biblioteca"
                        ? "Recursos con propósito."
                        : view === "Publicación"
                          ? "Listos para tu revisión."
                          : "Tu equipo de edición."}
              </h1>
              <p>
                {view === "Contenido"
                  ? "Elegí qué vas a contar. El motor se ocupa del montaje."
                  : view === "Editar"
                    ? "Subí, generá un borrador y ajustá lo que haga falta."
                    : view === "Biblioteca"
                      ? "Usá imágenes, clips y música que tengas permiso de publicar."
                      : "Todo el avance queda guardado en tu espacio privado."}
              </p>
            </div>
            {view === "Contenido" && (
              <button
                className="primary"
                onClick={() =>
                  document
                    .getElementById("new-reel")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                + Nuevo Reel
              </button>
            )}
          </div>
          {error && (
            <div className="alert" role="alert">
              {error}
              <button aria-label="Cerrar error" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
            </div>
          )}
          {!status && <div className="skeleton" aria-label="Cargando Studio" />}
          {status && !status.worker_online && (
            <div className="offline">
              ◷{" "}
              <div>
                <strong>El equipo de edición está desconectado</strong>
                <p>
                  Podés preparar tus Reels. Los trabajos quedan en cola hasta
                  que abras el worker en tu PC.
                </p>
              </div>
            </div>
          )}
          {view === "Contenido" && (
            <>
              {!status?.seed_loaded && (
                <div className="seed-banner">
                  <div>
                    <strong>Tu biblioteca V3 está pendiente de importar</strong>
                    <p>
                      No se encontró el seed de 18 Reels y 3 alternativas. La
                      demo técnica permite probar el editor mientras lo agregás.
                    </p>
                  </div>
                  <label className="button">
                    Importar contenido
                    <input
                      type="file"
                      accept=".json"
                      className="file-hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f)
                          act(async () => {
                            const r = await api<{ imported: number }>(
                              "content/import",
                              "POST",
                              JSON.parse(await f.text()),
                            );
                            setNotice(
                              `${r.imported} fichas importadas. Los originales se conservaron.`,
                            );
                          });
                      }}
                    />
                  </label>
                </div>
              )}
              {[...new Set(items.map((c) => c.week))]
                .sort((a, b) => a - b)
                .map((week) => (
                  <section key={week}>
                    <div className="section-line">
                      <h2>{week ? `Semana ${week}` : "Tu mesa de trabajo"}</h2>
                      <span>
                        {items.filter((c) => c.week === week).length} contenidos
                      </span>
                    </div>
                    <div className="content-grid">
                      {items
                        .filter((c) => c.week === week)
                        .map((c) => (
                          <article className="content-card" key={c.id}>
                            <div className="card-top">
                              <span>{c.id}</span>
                              <span className="badge">
                                {c.id === "DEMO-TECNICA"
                                  ? "Demo técnica"
                                  : c.status === "planned"
                                    ? "Por preparar"
                                    : c.status}
                              </span>
                            </div>
                            <div className="card-art">
                              <span>
                                {c.week ? String(c.week).padStart(2, "0") : "↗"}
                              </span>
                              <p>
                                {c.id === "DEMO-TECNICA"
                                  ? "DEL RAW AL REEL"
                                  : "UNA IDEA QUE MERECE CONTARSE"}
                              </p>
                            </div>
                            <h3>{c.title}</h3>
                            <p>{c.hooks[0] || c.script.slice(0, 145)}</p>
                            {c.demo_gate && (
                              <small className="gate">
                                Demostración pendiente
                              </small>
                            )}
                            <button onClick={() => choose(c)}>
                              Preparar este Reel <span>→</span>
                            </button>
                          </article>
                        ))}
                    </div>
                  </section>
                ))}
              <section className="panel new-reel" id="new-reel">
                <div>
                  <div className="eyebrow">¿TENÉS OTRA IDEA?</div>
                  <h2>Empezá desde tu guion</h2>
                  <p>
                    La edición básica conserva tu cámara. Los gráficos se
                    agregan con tu aprobación.
                  </p>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    act(async () => {
                      const c = await api<Content>("content", "POST", {
                        title: newTitle,
                        script: newScript,
                      });
                      setNewTitle("");
                      setNewScript("");
                      await refresh();
                      choose(c);
                    });
                  }}
                >
                  <label>
                    Título
                    <input
                      required
                      maxLength={160}
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder="La idea central de tu Reel"
                    />
                  </label>
                  <label>
                    Guion o brief
                    <textarea
                      value={newScript}
                      onChange={(e) => setNewScript(e.target.value)}
                      rows={3}
                      placeholder="¿Qué querés explicar?"
                    />
                  </label>
                  <button className="primary" disabled={busy}>
                    Crear contenido
                  </button>
                </form>
              </section>
            </>
          )}
          {view === "Editar" && item && (
            <>
              <div className="editor-grid">
                <section className="panel script-panel">{contentCopy}</section>
                <section className="panel setup-panel">
                  <div className="eyebrow">PREPARAR MONTAJE</div>
                  <h2>Tres pasos, tu borrador.</h2>
                  <div className="step-label">
                    <span>1</span>
                    <h3>Tu grabación</h3>
                  </div>
                  <div className="source-toggle">
                    <button
                      aria-pressed={mode === "recording"}
                      onClick={() => {
                        setMode("recording");
                        if (item.id === "DEMO-TECNICA") setScenes([]);
                      }}
                    >
                      Con cámara
                    </button>
                    <button
                      aria-pressed={mode === "graphics"}
                      onClick={() => {
                        setMode("graphics");
                        setEngine("remotion");
                        setScenes(item.scenes);
                      }}
                    >
                      Solo gráficos
                    </button>
                  </div>
                  {mode === "recording" ? (
                    <>
                      <label
                        className={"dropzone " + (recording ? "has-file" : "")}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault();
                          const f = e.dataTransfer.files[0];
                          if (f && !busy) uploadFile(f);
                        }}
                      >
                        <span className="upload-icon">↑</span>
                        <strong>
                          {recording ? recording.name : "Arrastrá tu video acá"}
                        </strong>
                        <span>
                          {recording
                            ? `${(recording.size / 1024 ** 2).toFixed(1)} MB · Guardado`
                            : "o elegí un archivo · MP4, MOV, WebM"}
                        </span>
                        <input
                          aria-label="Subir grabación"
                          disabled={busy || !!active}
                          type="file"
                          accept="video/mp4,video/quicktime,video/webm,.mov,.m4v"
                          onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) uploadFile(f);
                          }}
                        />
                      </label>
                      {upload !== null && (
                        <>
                          <progress value={upload} max={100} />
                          <p role="status">Subiendo: {upload}%</p>
                        </>
                      )}
                      {assets.some((a) => a.mime.startsWith("video/")) && (
                        <label>
                          O reutilizá una grabación
                          <select
                            value={assetId}
                            onChange={(e) => {
                              setAssetId(e.target.value);
                              setJobId("");
                              setWords([]);
                            }}
                          >
                            <option value="">Elegir grabación</option>
                            {assets
                              .filter((a) => a.mime.startsWith("video/"))
                              .map((a) => (
                                <option value={a.id} key={a.id}>
                                  {a.name}
                                </option>
                              ))}
                          </select>
                        </label>
                      )}
                      {recording?.sha256 && (
                        <details>
                          <summary>Identidad de la fuente</summary>
                          <code className="hash">
                            SHA256 {recording.sha256}
                          </code>
                          <p>
                            El worker verificará duración y codecs antes del
                            render.
                          </p>
                        </details>
                      )}
                    </>
                  ) : (
                    <div className="info">
                      Composición de 8 segundos. Requiere escenas aprobadas que
                      cubran toda la duración. Sin voz, no se inventan
                      subtítulos.
                    </div>
                  )}
                  <div className="step-label">
                    <span>2</span>
                    <h3>Estilo y sonido</h3>
                  </div>
                  <label>
                    Motor
                    <select
                      value={engine}
                      disabled={mode === "graphics"}
                      onChange={(e) => {
                        setEngine(e.target.value as "ffmpeg" | "remotion");
                        if (e.target.value === "ffmpeg") setMusic("");
                      }}
                    >
                      <option value="remotion">
                        Educativo Remotion · gráficos animados
                      </option>
                      <option value="ffmpeg">
                        Básico FFmpeg · cámara y subtítulos
                      </option>
                    </select>
                  </label>
                  <label>
                    Música
                    <select
                      value={music}
                      disabled={engine === "ffmpeg"}
                      onChange={(e) => setMusic(e.target.value)}
                    >
                      <option value="">Sin música · voz protagonista</option>
                      {assets
                        .filter(
                          (a) =>
                            a.mime.startsWith("audio/") &&
                            a.approved &&
                            a.rights,
                        )
                        .map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={preserve}
                      onChange={(e) => setPreserve(e.target.checked)}
                    />{" "}
                    Conservar pausas de la grabación
                  </label>
                  <div className="step-label">
                    <span>3</span>
                    <h3>Primer borrador</h3>
                  </div>
                  <p className="muted">
                    Preview 360 × 640 para revisar. El final se exporta a 1080 ×
                    1920.
                  </p>
                  <button
                    className="primary full"
                    disabled={
                      busy || !!active || (mode === "recording" && !assetId)
                    }
                    onClick={() => generate("preview")}
                  >
                    {busy ? "Preparando…" : "Generar borrador"} <span>→</span>
                  </button>
                </section>
              </div>
              {current && (
                <section className="panel result-panel">
                  <div className="section-line">
                    <div>
                      <div className="eyebrow">TU MONTAJE</div>
                      <h2>{phases[current.status] || current.status}</h2>
                    </div>
                    {badge(current)}
                  </div>
                  <div className="result-grid">
                    <div className="preview-stage">
                      {result ? (
                        <MediaPreview identity={result.id} url={result.url} />
                      ) : (
                        <div className="preview-empty">
                          <span>9:16</span>
                          <strong>
                            {current.status === "failed"
                              ? "Vamos a corregirlo."
                              : "Tu Reel aparece aquí."}
                          </strong>
                          <p>
                            {active
                              ? "El worker informará cada fase al completarla."
                              : "No hay salida disponible en este intento."}
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="review-panel">
                      <ol className="pipeline">
                        {current.events
                          .filter(
                            (v, i, a) => i === 0 || v.phase !== a[i - 1].phase,
                          )
                          .map((v, i) => (
                            <li key={i}>
                              <span />
                              {phases[v.phase] || v.phase}
                              <time>
                                {new Date(
                                  Number(v.created_at),
                                ).toLocaleTimeString("es-PY")}
                              </time>
                            </li>
                          ))}
                      </ol>
                      {current.error && (
                        <div className="alert">{current.error}</div>
                      )}
                      {active && (
                        <button
                          disabled={
                            busy || current.status === "cancel_requested"
                          }
                          onClick={() =>
                            act(async () => {
                              await api(
                                `jobs/${current.id}/cancel`,
                                "POST",
                                {},
                              );
                            })
                          }
                        >
                          Cancelar trabajo
                        </button>
                      )}
                      {["failed", "canceled"].includes(current.status) && (
                        <button
                          className="primary"
                          disabled={busy}
                          onClick={() =>
                            act(async () => {
                              const j = await api<Job>(
                                `jobs/${current.id}/retry`,
                                "POST",
                                { intent_key: uid() },
                              );
                              setJobId(j.id);
                            })
                          }
                        >
                          Reintentar en una nueva versión
                        </button>
                      )}
                      {result && (
                        <>
                          <div className="export-meta">
                            <span>{result.resolution.join(" × ")}</span>
                            <span>H.264 / AAC</span>
                            <span>{result.duration.toFixed(1)} s</span>
                            <span>30 fps</span>
                          </div>
                          <a
                            className="button"
                            href={`${result.url}&download=1`}
                          >
                            Descargar{" "}
                            {result.kind === "final" ? "final" : "preview"}
                          </a>
                          {current.status === "preview_ready" && (
                            <button
                              className="primary"
                              disabled={busy}
                              onClick={() => generate("final")}
                            >
                              Generar final 1080p
                            </button>
                          )}
                          <p className="muted">
                            Cada render crea una versión nueva. Revisá voz,
                            cifras y cortes antes de publicar.
                          </p>
                        </>
                      )}
                      {current.warnings?.length ? (
                        <details className="warnings">
                          <summary>
                            {current.warnings.length} observaciones de revisión
                          </summary>
                          <ul>
                            {current.warnings.map((w, i) => (
                              <li key={i}>{w}</li>
                            ))}
                          </ul>
                        </details>
                      ) : null}
                      {current.report && (
                        <details>
                          <summary>Tiempos de fuente → montaje</summary>
                          {current.report.time_map.map((r, i) => (
                            <p key={i}>
                              {r.source_start.toFixed(2)}–
                              {r.source_end.toFixed(2)} s →{" "}
                              {r.output_start.toFixed(2)}–
                              {r.output_end.toFixed(2)} s
                            </p>
                          ))}
                        </details>
                      )}
                    </div>
                  </div>
                </section>
              )}
              <section className="panel">
                <div className="section-line">
                  <div>
                    <div className="eyebrow">REVISIÓN EDITORIAL</div>
                    <h2>Gráficos que acompañan tu idea</h2>
                  </div>
                  <button
                    disabled={busy}
                    onClick={() =>
                      setScenes([
                        ...scenes,
                        {
                          id: uid(),
                          match_text: "",
                          purpose: "Aclarar la idea hablada",
                          reason: "Selección manual del propietario",
                          template: "QuestionHook",
                          params: { title: "", theme: "dark", items: [] },
                          approved: false,
                          demo: true,
                          duration: 4,
                          layout: "card",
                        },
                      ])
                    }
                  >
                    + Agregar gráfico
                  </button>
                </div>
                {!scenes.length && (
                  <p className="muted">
                    Se conserva tu cámara. Podés agregar un gráfico y vincularlo
                    a una frase que hayas dicho.
                  </p>
                )}
                <div className="scenes">
                  {scenes.map((s, i) => {
                    const decision = current?.report?.decisions.find(
                      (d) => d.id === s.id,
                    );
                    const change = (patch: Partial<typeof s>) =>
                      setScenes(
                        scenes.map((x, n) =>
                          n === i ? { ...x, ...patch } : x,
                        ),
                      );
                    return (
                      <article className="scene-editor" key={s.id}>
                        <div className="section-line">
                          <strong>Apoyo {i + 1}</strong>
                          <span className="badge">
                            {decision?.status === "resolved"
                              ? "Coincidencia resuelta"
                              : decision?.status === "omitted"
                                ? "Omitido · conservar cámara"
                                : s.approved
                                  ? "Aprobado por vos"
                                  : "Por revisar"}
                          </span>
                          <button
                            className="text-button"
                            onClick={() =>
                              setScenes(scenes.filter((_, n) => n !== i))
                            }
                          >
                            Quitar
                          </button>
                        </div>
                        <div className="fields">
                          <label>
                            Plantilla
                            <select
                              value={s.template || "ScreenshotFocus"}
                              onChange={(e) =>
                                change({
                                  template: e.target.value as typeof s.template,
                                })
                              }
                            >
                              {[
                                "QuestionHook",
                                "AnimatedMessages",
                                "CRMHighlight",
                                "StepDiagram",
                                "ScreenshotFocus",
                                "SummaryCTA",
                              ].map((t) => (
                                <option key={t}>{t}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Título del gráfico
                            <input
                              maxLength={86}
                              value={s.params?.title || ""}
                              onChange={(e) =>
                                change({
                                  params: {
                                    theme: "dark",
                                    items: [],
                                    ...s.params,
                                    title: e.target.value,
                                  },
                                })
                              }
                            />
                          </label>
                          <label>
                            Al decir esta frase
                            <input
                              disabled={!!s.source_time}
                              value={s.match_text}
                              placeholder="Al menos tres palabras, una sola vez"
                              onChange={(e) =>
                                change({ match_text: e.target.value })
                              }
                            />
                          </label>
                          <label>
                            Recurso autorizado
                            <select
                              value={s.asset_id || ""}
                              onChange={(e) =>
                                change({
                                  asset_id: e.target.value || undefined,
                                  template: e.target.value
                                    ? "ScreenshotFocus"
                                    : s.template,
                                })
                              }
                            >
                              <option value="">
                                Solo gráfico de plantilla
                              </option>
                              {assets
                                .filter(
                                  (a) =>
                                    a.approved &&
                                    a.rights &&
                                    !a.mime.startsWith("audio/"),
                                )
                                .map((a) => (
                                  <option key={a.id} value={a.id}>
                                    {a.name}
                                  </option>
                                ))}
                            </select>
                          </label>
                        </div>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={!!s.source_time}
                            onChange={(e) =>
                              change({
                                source_time: e.target.checked
                                  ? [
                                      0,
                                      Math.min(
                                        4,
                                        current?.report?.source_duration || 4,
                                      ),
                                    ]
                                  : undefined,
                              })
                            }
                          />{" "}
                          Ubicar manualmente en la fuente
                        </label>
                        {s.source_time && (
                          <div className="fields timing">
                            <label>
                              Inicio fuente (s)
                              <input
                                type="number"
                                min={0}
                                step="0.1"
                                value={s.source_time[0]}
                                onChange={(e) =>
                                  change({
                                    source_time: [
                                      Number(e.target.value),
                                      s.source_time![1],
                                    ],
                                  })
                                }
                              />
                            </label>
                            <label>
                              Fin fuente (s)
                              <input
                                type="number"
                                min={0}
                                step="0.1"
                                value={s.source_time[1]}
                                onChange={(e) =>
                                  change({
                                    source_time: [
                                      s.source_time![0],
                                      Number(e.target.value),
                                    ],
                                  })
                                }
                              />
                            </label>
                          </div>
                        )}
                        {s.template === "SummaryCTA" && (
                          <label>
                            Llamada a la acción
                            <input
                              maxLength={54}
                              value={s.params?.cta || ""}
                              onChange={(e) =>
                                change({
                                  params: {
                                    theme: "dark",
                                    items: [],
                                    ...s.params,
                                    cta: e.target.value,
                                  },
                                })
                              }
                            />
                          </label>
                        )}
                        {[
                          "AnimatedMessages",
                          "CRMHighlight",
                          "StepDiagram",
                        ].includes(s.template || "") && (
                          <>
                            <label>
                              Elementos (etiqueta | valor, uno por línea; máximo
                              cuatro)
                              <textarea
                                value={(s.params?.items || [])
                                  .map((x) => `${x.label} | ${x.value}`)
                                  .join("\n")}
                                onChange={(e) =>
                                  change({
                                    params: {
                                      theme: "dark",
                                      ...s.params,
                                      items: e.target.value
                                        .split("\n")
                                        .slice(0, 4)
                                        .map((v, n) => {
                                          const [label, ...value] =
                                            v.split("|");
                                          return {
                                            label: label.trim(),
                                            value: value.join("|").trim(),
                                            at_seconds: n * 0.4,
                                          };
                                        }),
                                    },
                                  })
                                }
                              />
                            </label>
                          </>
                        )}
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={s.approved}
                            onChange={(e) =>
                              change({ approved: e.target.checked })
                            }
                          />{" "}
                          Aprobar este apoyo visual (datos ilustrativos)
                        </label>
                        {Boolean(decision?.warning) && (
                          <p className="warning">{String(decision?.warning)}</p>
                        )}
                        {Boolean(decision?.output_time) && (
                          <p className="muted">
                            Salida:{" "}
                            {(decision?.output_time as number[])
                              .map((v) => v.toFixed(2))
                              .join("–")}{" "}
                            s
                          </p>
                        )}
                      </article>
                    );
                  })}
                </div>
                {current?.report && (
                  <>
                    <div className="section-line">
                      <h2>Subtítulos: corregí lo que escuchás</h2>
                      <span>{words.length} palabras</span>
                    </div>
                    {!words.length ? (
                      <p className="muted">
                        No hay palabras transcritas. No se generarán subtítulos
                        inventados.
                      </p>
                    ) : (
                      <>
                        <p className="muted">
                          Tiempos de la grabación original. Se remapean al
                          aplicar los cortes. Prestá atención a nombres, cifras
                          y negaciones.
                        </p>
                        <div className="word-list">
                          {words
                            .slice(wordPage * 30, wordPage * 30 + 30)
                            .map((w, n) => (
                              <div key={wordPage * 30 + n}>
                                <span>{w.start.toFixed(2)} s</span>
                                <input
                                  aria-label={`Palabra ${wordPage * 30 + n + 1}`}
                                  value={w.text}
                                  maxLength={120}
                                  onChange={(e) =>
                                    setWords(
                                      words.map((x, i) =>
                                        i === wordPage * 30 + n
                                          ? { ...x, text: e.target.value }
                                          : x,
                                      ),
                                    )
                                  }
                                />
                              </div>
                            ))}
                        </div>
                        <div className="pager">
                          <button
                            disabled={!wordPage}
                            onClick={() => setWordPage(wordPage - 1)}
                          >
                            Anterior
                          </button>
                          <span>
                            {wordPage + 1} / {Math.ceil(words.length / 30)}
                          </span>
                          <button
                            disabled={(wordPage + 1) * 30 >= words.length}
                            onClick={() => setWordPage(wordPage + 1)}
                          >
                            Siguiente
                          </button>
                        </div>
                      </>
                    )}
                    <button
                      className="primary"
                      disabled={busy || !!active}
                      onClick={() => generate("preview")}
                    >
                      Aplicar cambios y regenerar borrador
                    </button>
                  </>
                )}
              </section>
            </>
          )}
          {view === "Mis Reels" && (
            <section className="panel">
              <div className="section-line">
                <h2>Historial de montajes</h2>
                <span>{jobs.length} versiones</span>
              </div>
              {!jobs.length ? (
                <div className="empty">
                  <h3>Tu primer Reel empieza con una idea.</h3>
                  <p>Elegí un contenido y subí tu grabación.</p>
                  <button
                    className="primary"
                    onClick={() => setView("Contenido")}
                  >
                    Ver contenido
                  </button>
                </div>
              ) : (
                <div className="job-list">
                  {jobs.map((j) => (
                    <button key={j.id} onClick={() => openJob(j)}>
                      <div>
                        <strong>{j.content.title}</strong>
                        <small>
                          {date(Number(j.created_at))} · {j.settings.engine} ·{" "}
                          {j.settings.kind === "final" ? "Final" : "Borrador"}
                        </small>
                      </div>
                      {badge(j)}
                      <span>→</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}
          {view === "Biblioteca" && (
            <>
              <section className="panel">
                <h2>Agregar un recurso</h2>
                <p className="muted">
                  El recurso queda disponible solo para tus proyectos. No subas
                  datos de pacientes.
                </p>
                <div className="fields">
                  <label>
                    Procedencia y derechos
                    <input
                      value={rights}
                      onChange={(e) => setRights(e.target.value)}
                      placeholder="Propio / licencia y alcance de uso"
                    />
                  </label>
                  <label>
                    Etiquetas semánticas
                    <input
                      value={tags}
                      onChange={(e) => setTags(e.target.value)}
                      placeholder="seguimiento, estado, agenda"
                    />
                  </label>
                </div>
                <label className="button">
                  Subir y aprobar recurso
                  <input
                    className="file-hidden"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,video/mp4,audio/mpeg,audio/wav,audio/mp4,.m4a"
                    disabled={busy}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) uploadFile(f, true);
                    }}
                  />
                </label>
                {upload !== null && <progress max={100} value={upload} />}
              </section>
              <div className="tabs">
                {[
                  ["images", "Imágenes"],
                  ["video", "Videos"],
                  ["audio", "Música"],
                ].map(([v, l]) => (
                  <button
                    key={v}
                    aria-pressed={libraryType === v}
                    onClick={() => setLibraryType(v)}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <div className="asset-grid">
                {assets
                  .filter((a) =>
                    a.mime.startsWith(
                      libraryType === "images" ? "image/" : libraryType + "/",
                    ),
                  )
                  .map((a) => (
                    <article className="panel asset-card" key={a.id}>
                      {a.mime.startsWith("image/") ? (
                        <img src={`/api/assets/${a.id}/file`} alt={a.name} />
                      ) : a.mime.startsWith("audio/") ? (
                        <audio controls src={`/api/assets/${a.id}/file`} />
                      ) : (
                        <video
                          controls
                          preload="metadata"
                          src={`/api/assets/${a.id}/file`}
                        />
                      )}
                      <h3>{a.name}</h3>
                      <p>{a.rights || "Derechos pendientes"}</p>
                      <div className="tags">
                        {a.tags.map((t) => (
                          <span key={t}>{t}</span>
                        ))}
                      </div>
                      <span className="badge">
                        {a.approved ? "Aprobado" : "Por revisar"}
                      </span>
                    </article>
                  ))}
              </div>
            </>
          )}
          {view === "Publicación" && (
            <>
              <section className="panel">
                <h2>Publicación manual, después de revisar</h2>
                <p>
                  Reproducí el final completo con sonido. Comprobá voz,
                  piel/color, textos y zonas seguras en el teléfono.
                </p>
                <label>
                  Contenido
                  <select
                    value={selected}
                    onChange={(e) => {
                      setSelected(e.target.value);
                      const c = items.find((x) => x.id === e.target.value);
                      setCaption(c?.caption || "");
                    }}
                  >
                    {items.map((c) => (
                      <option value={c.id} key={c.id}>
                        {c.id} · {c.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Caption y hashtags
                  <textarea
                    rows={6}
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                  />
                </label>
                <div className="actions">
                  <button
                    disabled={busy}
                    onClick={() =>
                      act(async () => {
                        await api(`content/${selected}`, "PATCH", { caption });
                        setNotice("Caption guardado.");
                      })
                    }
                  >
                    Guardar caption
                  </button>
                  <button
                    onClick={() =>
                      act(async () => {
                        await navigator.clipboard.writeText(caption);
                        setNotice("Caption copiado.");
                      })
                    }
                  >
                    Copiar caption
                  </button>
                </div>
                <div className="fields">
                  <label>
                    Fecha de publicación propuesta
                    <input
                      type="date"
                      value={item?.date || ""}
                      onChange={(e) =>
                        act(async () => {
                          await api(`content/${selected}`, "PATCH", {
                            date: e.target.value,
                          });
                        })
                      }
                    />
                  </label>
                  <label>
                    Estado manual
                    <select
                      value={item?.status || "planned"}
                      onChange={(e) =>
                        act(async () => {
                          await api(`content/${selected}`, "PATCH", {
                            status: e.target.value,
                          });
                        })
                      }
                    >
                      {[
                        ["planned", "Planificado"],
                        ["needs_recording", "Por grabar"],
                        ["review", "En revisión"],
                        ["approved", "Aprobado"],
                        ["scheduled", "Agendado manualmente"],
                        ["published", "Publicado manualmente"],
                      ].map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </section>
              {jobs
                .filter(
                  (j) =>
                    j.content.id === selected && j.status === "final_ready",
                )
                .map((j) => (
                  <section className="panel" key={j.id}>
                    <div className="section-line">
                      <h3>Final · {date(Number(j.created_at))}</h3>
                      {badge(j)}
                    </div>
                    {j.outputs[0] && (
                      <MediaPreview
                        className="publication-video"
                        identity={j.outputs[0].id}
                        url={j.outputs[0].url}
                      />
                    )}
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={j.reviewed || reviewed}
                        disabled={j.reviewed}
                        onChange={(e) => setReviewed(e.target.checked)}
                      />{" "}
                      Vi y escuché el video completo; revisé las afirmaciones y
                      el texto.
                    </label>
                    <button
                      className="primary"
                      disabled={!reviewed || busy || j.reviewed}
                      onClick={() =>
                        act(async () => {
                          await api(`jobs/${j.id}/approve`, "POST", {
                            reviewed: true,
                          });
                          setNotice(
                            "Marcado como listo para publicación manual.",
                          );
                        })
                      }
                    >
                      Aprobar revisión
                    </button>
                    {j.outputs[0] && (
                      <a
                        className="button"
                        href={`${j.outputs[0].url}&download=1`}
                      >
                        Descargar MP4
                      </a>
                    )}
                  </section>
                ))}
            </>
          )}
          {view === "Ajustes" && (
            <div className="settings-grid">
              <section className="panel">
                <h2>Estado del motor</h2>
                <p>
                  {status?.worker_online
                    ? "Tu PC está recibiendo trabajos."
                    : "Abrí worker/start-worker.bat o iniciar_studio.bat para conectar el equipo."}
                </p>
                {status?.workers.map((w) => (
                  <div className="worker-card" key={w.id}>
                    <strong>{w.id}</strong>
                    <span className={"badge " + (w.online ? "good" : "")}>
                      {w.online ? "Conectado" : "Desconectado"}
                    </span>
                    {Object.entries(w.capabilities).map(([k, v]) => (
                      <p key={k}>
                        {k.replaceAll("_", " ")}{" "}
                        <strong>
                          {v ? "Disponible" : "Revisar instalación"}
                        </strong>
                      </p>
                    ))}
                  </div>
                ))}
                <button disabled={busy} onClick={() => act(refresh)}>
                  Actualizar estado
                </button>
              </section>
              <section className="panel">
                <h2>Tu configuración</h2>
                <dl>
                  <dt>Modo</dt>
                  <dd>{status?.mode}</dd>
                  <dt>Salida final</dt>
                  <dd>1080 × 1920 · 30 fps · H.264 / AAC</dd>
                  <dt>Límite por subida</dt>
                  <dd>{Math.round((status?.max_bytes || 0) / 1024 ** 2)} MB</dd>
                  <dt>Procesamiento</dt>
                  <dd>Una edición a la vez · Whisper local</dd>
                  <dt>Contenido V3</dt>
                  <dd>
                    {status?.seed_loaded ? "Importado" : "Seed pendiente"}
                  </dd>
                </dl>
                <p className="muted">
                  El modo remoto necesita almacenamiento privado, base de datos,
                  acceso de propietario y un worker conectado. No se ha validado
                  el despliegue remoto.
                </p>
              </section>
            </div>
          )}
          <footer>
            Hecho para explicar mejor.{" "}
            <span>Silencio por defecto · revisión antes de publicar</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
