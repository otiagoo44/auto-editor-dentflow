from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Winget actualiza el PATH de usuario, pero una terminal ya abierta no lo hereda.
if sys.platform == "win32":
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as _key:
        try:
            os.environ["PATH"] += os.pathsep + os.path.expandvars(winreg.QueryValueEx(_key, "Path")[0])
        except FileNotFoundError:
            pass


def run(cmd, cwd=None):
    result = subprocess.run([str(x) for x in cmd], cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{cmd[0]} falló ({result.returncode}):\n{result.stderr[-5000:]}")
    return result.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", path]))


def ffprobe_duration(path):
    return float(probe(path)["format"]["duration"])


def choose_source_video(folder):
    preferred = [folder / n for n in ("raw.mp4", "video.mp4", "grabacion.mp4") if (folder / n).exists()]
    if len(preferred) == 1:
        return preferred[0]
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS
             and not any(s in p.stem.lower() for s in ("final", "output", "editado"))]
    if len(files) != 1:
        raise ValueError("Indica source en edicion.json o deja un único video / raw.mp4.")
    return files[0]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class Word:
    start: float
    end: float
    text: str


def validate_words(data, duration):
    words = [Word(float(w["start"]), float(w["end"]), str(w["text"]).strip()) for w in data]
    prev = -1.0
    for w in words:
        if not (math.isfinite(w.start) and math.isfinite(w.end)
                and 0 <= w.start < w.end <= duration + 0.05 and w.start >= prev and w.text):
            raise ValueError(f"Palabra o tiempo inválido: {w}")
        prev = w.start
    return words


def transcribe_worker(source, dest, cfg):
    # Worker separado: devuelve la RAM del modelo antes del render.
    from faster_whisper import WhisperModel
    model = WhisperModel(cfg["model"], device="cpu", compute_type="int8",
                         cpu_threads=cfg.get("threads", 2), num_workers=1,
                         local_files_only=cfg.get("offline", False))
    segments, info = model.transcribe(str(source), language=cfg.get("language", "es"),
                                     word_timestamps=True, vad_filter=True, beam_size=3)
    words = [dict(start=float(w.start), end=float(w.end), text=w.word.strip())
             for segment in segments for w in (segment.words or []) if w.end > w.start]
    write_json(dest, {"words": words, "language": info.language, "backend": "faster-whisper-local"})


def get_words(source, folder, out, cfg, duration, digest):
    corrected = folder / "transcript.json"
    if corrected.exists():
        data = read_json(corrected)
        return validate_words(data["words"], duration), "transcript.json (usuario)"
    if not cfg["transcription"]["enabled"]:
        return [], "desactivada"
    cache = out / "transcript_cache.json"
    key = {"sha256": digest, "transcription": cfg["transcription"], "schema": 1}
    if cache.exists():
        data = read_json(cache)
        if data.get("key") == key:
            return validate_words(data["words"], duration), "cache local"
    with tempfile.TemporaryDirectory(prefix="dentflow_asr_") as td:
        dest = Path(td) / "transcript.json"
        options = Path(td) / "cfg.json"
        write_json(options, cfg["transcription"])
        print("Transcripción local: modelo " + cfg["transcription"]["model"], flush=True)
        run([sys.executable, Path(__file__), "--asr-worker", source, dest, options])
        data = read_json(dest)
    words = validate_words(data["words"], duration)
    data["key"] = key
    write_json(cache, data)
    return words, "faster-whisper local"


def validate_ranges(ranges, duration, fps):
    result = []
    for pair in ranges:
        if len(pair) != 2:
            raise ValueError("Cada intervalo necesita inicio y fin.")
        a, b = map(float, pair)
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= duration + 0.05):
            raise ValueError(f"Intervalo fuera del video: {pair}")
        a, b = math.floor(a * fps + 1e-6) / fps, math.ceil(b * fps - 1e-6) / fps
        if b <= a or (result and a < result[-1][1] - 1e-6):
            raise ValueError("Intervalos deben estar ordenados, sin superposición.")
        result.append((a, b))
    if not result:
        raise ValueError("No se puede eliminar todo el video.")
    return result


def build_keep_segments(words, duration, cfg):
    # Sólo propone cortes entre palabras. Conserva comienzo, final y emisiones breves.
    if not words:
        return [(0, duration)]
    c = cfg["cuts"]
    removals = []
    for prev, cur in zip(words, words[1:]):
        if cur.start - prev.end >= c["gap_to_suggest_seconds"]:
            a = prev.end + c["keep_after_seconds"]
            b = cur.start - c["keep_before_seconds"]
            if a < b:
                removals.append((a, b))
    kept, start = [], 0.0
    for a, b in removals:
        kept.append((start, a))
        start = b
    kept.append((start, duration))
    return kept


def remap_time(t, keep):
    elapsed = 0.0
    for a, b in keep:
        if a <= t <= b:
            return elapsed + t - a
        elapsed += b - a
    raise ValueError(f"Tiempo {t} eliminado del montaje.")


def validate_cut_boundaries(words, keep):
    for w in words:
        for a, b in keep:
            if w.start < a < w.end or w.start < b < w.end:
                raise ValueError(f"Corte atraviesa palabra '{w.text}' ({w.start:.2f}–{w.end:.2f}).")


def lines_for(text, limit):
    lines, current = [], ""
    for token in text.split():
        if len(token) > limit:
            raise ValueError(f"Palabra demasiado larga para subtítulo: {token}; revisa transcript.json.")
        if current and len(current) + 1 + len(token) > limit:
            lines.append(current)
            current = token
        else:
            current = (current + " " + token).strip()
    if current:
        lines.append(current)
    return lines


def make_captions(words, keep, cfg):
    s = cfg["subtitles"]
    caps, offset = [], 0.0
    for a, b in keep:
        group = []
        def flush():
            if group:
                text = " ".join(w.text for w in group)
                caps.append((offset + group[0].start - a, offset + group[-1].end - a,
                             "\n".join(lines_for(text, s["max_chars_per_line"]))))
                group.clear()
        for w in words:
            if not (a <= w.start and w.end <= b + 1e-6):
                continue
            candidate = " ".join(x.text for x in group + [w])
            if group and (w.start - group[-1].end > s["phrase_gap_seconds"]
                          or w.end - group[0].start > s["max_duration_seconds"]
                          or len(lines_for(candidate, s["max_chars_per_line"])) > 2):
                flush()
            group.append(w)
            if re.search(r"[.!?;:]$", w.text):
                flush()
        flush()
        offset += b - a
    return caps


def ass_time(t):
    centis = round(t * 100)
    return f"{centis // 360000}:{centis // 6000 % 60:02d}:{centis // 100 % 60:02d}.{centis % 100:02d}"


def write_ass(captions, path, cfg):
    v, s = cfg["video"], cfg["subtitles"]
    scale = v["width"] / 1080
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {v['width']}
PlayResY: {v['height']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{s['font']},{s['font_size']*scale},&H00FFFFFF,&H000000FF,&H00101010,&H66000000,-1,0,0,0,100,100,0,0,1,{3*scale},0,2,{80*scale},{80*scale},{s['margin_v']*scale},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    for start, end, text in captions:
        # Texto no puede introducir instrucciones ASS.
        text = text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", r"\N")
        content += f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}\n"
    path.write_text(content, encoding="utf-8")


def prepare_events(specs, keep, folder, duration):
    events = []
    for spec in specs:
        ev = dict(spec)
        a, b = float(ev["start"]), float(ev["end"])
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= duration):
            raise ValueError("Evento fuera del video.")
        if not str(ev.get("reason", "")).strip():
            raise ValueError("Cada evento necesita reason: qué explica o destaca.")
        if not any(x <= a and b <= y + 1e-6 for x, y in keep):
            raise ValueError("Un evento cruza un corte: ajusta start/end al tramo conservado.")
        ev["source_start"], ev["source_end"] = a, b
        ev["start"], ev["end"] = remap_time(a, keep), remap_time(b, keep)
        if ev["type"] == "asset":
            if ev.get("approved") is not True:
                raise ValueError("Asset requiere approved:true (propio o autorizado).")
            p = (folder / ev["file"]).resolve()
            if p.suffix.lower() not in IMAGE_EXTS | VIDEO_EXTS or not p.is_file():
                raise ValueError(f"Asset local no válido: {p}")
            if "videos_estudiar" in p.parts or "research" in p.parts:
                raise ValueError("Los materiales de investigación no se usan como assets.")
            ev["file"] = str(p)
            ev["offset"] = float(ev.get("offset", 0))
            if not math.isfinite(ev["offset"]) or ev["offset"] < 0:
                raise ValueError("offset inválido.")
            if p.suffix.lower() in VIDEO_EXTS and ev["offset"] + b - a > ffprobe_duration(p) + 0.02:
                raise ValueError("El clip auxiliar no cubre la duración del evento.")
            if ev.get("layout", "card") not in ("card", "full"):
                raise ValueError("layout debe ser card o full.")
        elif ev["type"] == "reframe":
            ev["scale"] = float(ev.get("scale", 1.08))
            ev["x"], ev["y"] = float(ev.get("x", .5)), float(ev.get("y", .5))
            if not (1 < ev["scale"] <= 1.3 and 0 <= ev["x"] <= 1 and 0 <= ev["y"] <= 1):
                raise ValueError("Reencuadre: escala (1,1.3], x/y entre 0 y 1.")
        else:
            raise ValueError("Evento desconocido: usa asset o reframe.")
        events.append(ev)
    events.sort(key=lambda x: x["start"])
    if any(b["start"] < a["end"] for a, b in zip(events, events[1:])):
        raise ValueError("V1 admite un solo evento visual a la vez.")
    return events


def ffmpeg_base(cfg):
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-filter_threads", "1", "-filter_complex_threads", "1"]


def fit_filter(cfg):
    v = cfg["video"]
    w, h = v["width"], v["height"]
    if v["fit"] == "contain":
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    if v["fit"] == "cover":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase:force_divisible_by=2,crop={w}:{h},setsar=1"
    raise ValueError("video.fit debe ser contain o cover.")


def render_cut_video(source, keep, temp, cfg):
    v = cfg["video"]
    has_audio = any(s["codec_type"] == "audio" for s in probe(source)["streams"])
    paths = []
    for i, (a, b) in enumerate(keep):
        part = temp / f"part_{i:03d}.mkv"
        dur = b - a
        cmd = ffmpeg_base(cfg) + ["-threads", str(v["threads"]), "-ss", f"{a:.6f}", "-i", source]
        if not has_audio:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        cmd += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                "-vf", f"setpts=PTS-STARTPTS,fps={v['fps']}," + fit_filter(cfg) + ",tpad=stop_mode=clone:stop_duration=1",
                "-af", f"asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=duration={dur:.6f}",
                "-t", f"{dur:.6f}", "-c:v", "libx264", "-threads", str(v["threads"]),
                "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", part]
        run(cmd)
        paths.append(part)
    listing = temp / "concat.txt"
    listing.write_text("\n".join(f"file '{p.name}'" for p in paths), encoding="utf-8")
    cut = temp / "cut.mkv"
    run(ffmpeg_base(cfg) + ["-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", cut], cwd=temp)
    return cut


def render_final(cut, ass, events, out, cfg, temp, duration):
    v, filters = cfg["video"], []
    w, h = v["width"], v["height"]
    cmd = ffmpeg_base(cfg) + ["-threads", str(v["threads"]), "-i", cut]
    current, index = "[0:v]", 0
    for n, ev in enumerate(events):
        start, end = ev["start"], ev["end"]
        output = f"[event{n}]"
        enable = f"gte(t,{start:.6f})*lt(t,{end:.6f})"
        if ev["type"] == "reframe":
            cw, ch = int(w / ev["scale"]) // 2 * 2, int(h / ev["scale"]) // 2 * 2
            filters += [f"{current}split[base{n}][zoom{n}]",
                        f"[zoom{n}]crop={cw}:{ch}:(iw-ow)*{ev['x']}:(ih-oh)*{ev['y']},scale={w}:{h}[z{n}]",
                        f"[base{n}][z{n}]overlay=0:0:enable='{enable}'{output}"]
        else:
            index += 1
            path = Path(ev["file"])
            if path.suffix.lower() in IMAGE_EXTS:
                cmd += ["-loop", "1", "-framerate", str(v["fps"]), "-i", path]
            else:
                cmd += ["-threads", str(v["threads"]), "-ss", str(ev["offset"]), "-i", path]
            full = ev.get("layout", "card") == "full"
            aw, ah = (w, h) if full else (int(w*.88)//2*2, int(h*.52)//2*2)
            x, y = (0, 0) if full else ((w-aw)//2, int(h*.12))
            dur = end-start
            fade = min(.12, dur/4)
            filters.append(f"[{index}:v]trim=duration={dur:.6f},setpts=PTS-STARTPTS,"
                           f"fps={v['fps']},scale={aw}:{ah}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                           f"pad={aw}:{ah}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=rgba,"
                           f"fade=t=in:st=0:d={fade}:alpha=1,"
                           f"fade=t=out:st={dur-fade:.6f}:d={fade}:alpha=1,"
                           f"setpts=PTS+{start:.6f}/TB[asset{n}]")
            filters.append(f"{current}[asset{n}]overlay={x}:{y}:eof_action=pass:repeatlast=0:"
                           f"enable='{enable}'{output}")
        current = output
    if cfg["subtitles"]["enabled"]:
        # ASS copiado a nombre fijo en cwd: evita escape de C: y apóstrofos de rutas.
        filters.append(f"{current}ass=subtitulos.ass[vout]")
    else:
        filters.append(f"{current}null[vout]")
    # FFmpeg 9 loudnorm puede producir NaN con silencio digital: no normalizarlo.
    normalize = cfg["audio"]["normalize"]
    if normalize:
        scan = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(cut), "-vn", "-af",
                               "astats=metadata=0:reset=0", "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        peaks = re.findall(r"Peak level dB: ([-\w.]+)", scan.stderr)
        if scan.returncode:
            raise RuntimeError("No se pudo medir el audio antes de normalizar.")
        normalize = bool(peaks) and any(float(p) > -90 for p in peaks)
    af = f"loudnorm=I={cfg['audio']['target_lufs']}:LRA=11:TP=-1.5" if normalize else "anull"
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "0:a:0",
            "-af", af, "-t", f"{duration:.6f}", "-r", str(v["fps"]),
            "-c:v", "libx264", "-threads", str(v["threads"]), "-preset", v["preset"],
            "-crf", str(v["crf"]), "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
            "-b:a", "160k", "-movflags", "+faststart", out]
    run(cmd, cwd=temp)


def process_reel(folder, cfg, plan_only=False, preview=False):
    started = time.monotonic()
    folder = folder.resolve()
    spec = read_json(folder / "edicion.json") if (folder / "edicion.json").exists() else {}
    source = (folder / spec["source"]).resolve() if "source" in spec else choose_source_video(folder)
    duration, digest = ffprobe_duration(source), fingerprint(source)
    output = folder / "OUTPUT"
    output.mkdir(exist_ok=True)
    words, transcript_source = get_words(source, folder, output, cfg, duration, digest)
    fps = cfg["video"]["fps"]
    suggested = validate_ranges(build_keep_segments(words, duration, cfg), duration, fps)
    # Por defecto conserva las pausas; las sugerencias se aprueban copiando a keep_segments.
    keep = validate_ranges(spec.get("keep_segments", [[0, duration]]), duration, fps)
    validate_cut_boundaries(words, keep)
    events = prepare_events(spec.get("events", []), keep, folder, duration)
    captions = make_captions(words, keep, cfg) if cfg["subtitles"]["enabled"] else []
    run_dir = output / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir.mkdir()
    mapping, offset = [], 0.0
    for a, b in keep:
        mapping.append({"source_start": a, "source_end": b, "output_start": offset, "output_end": offset+b-a})
        offset += b-a
    warnings = ["Revisar manualmente nombres, cifras, negaciones y sincronía."]
    if not words:
        warnings.append("Sin palabras: no hay subtítulos; no implica que el audio no tenga voz.")
    for a,b,t in captions:
        if len(t.replace("\n", " ")) / (b-a) > cfg["subtitles"]["warn_chars_per_second"]:
            warnings.append(f"Lectura rápida: {a:.2f}–{b:.2f}s; revisar frase/pausa.")
    plan = dict(version=1, source=str(source), sha256=digest, transcript_source=transcript_source,
                source_duration=duration, output_duration=offset, keep_segments=keep,
                suggested_keep_segments=suggested, time_map=mapping, events=events,
                captions=[dict(start=a,end=b,text=t) for a,b,t in captions], warnings=warnings,
                config=cfg, preview=preview, status="plan")
    write_json(run_dir / "plan_edicion.json", plan)
    write_json(run_dir / "transcript.json", {"words": [asdict(w) for w in words]})
    write_ass(captions, run_dir / "subtitulos.ass", cfg)
    print(f"Plan: {run_dir}", flush=True)
    if plan_only:
        return run_dir
    with tempfile.TemporaryDirectory(prefix="dentflow_render_") as td:
        temp = Path(td)
        shutil.copyfile(run_dir / "subtitulos.ass", temp / "subtitulos.ass")
        cut = render_cut_video(source, keep, temp, cfg)
        partial = run_dir / "render.partial.mp4"
        render_final(cut, temp / "subtitulos.ass", events, partial, cfg, temp, offset)
        measured = ffprobe_duration(partial)
        if abs(measured - offset) > max(.15, 2 / fps):
            raise RuntimeError(f"Duración inesperada: {measured} vs {offset}")
        final = run_dir / ("PREVIEW.mp4" if preview else "FINAL.mp4")
        partial.rename(final)
    plan.update(status="rendered", rendered_duration=measured,
                elapsed_seconds=round(time.monotonic()-started, 2), file=str(final))
    write_json(run_dir / "plan_edicion.json", plan)
    print(f"LISTO: {final}", flush=True)
    return final


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--asr-worker":
        transcribe_worker(Path(sys.argv[2]), Path(sys.argv[3]), read_json(Path(sys.argv[4])))
        return
    ap = argparse.ArgumentParser(description="DentFlow V1 local: plan, subtítulos y montaje explícito.")
    ap.add_argument("target", nargs="?", type=Path)
    ap.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    ap.add_argument("--week", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--warmup", action="store_true", help="Descarga inicial explicita del modelo; luego usar offline.")
    args = ap.parse_args()
    if args.warmup:
        import numpy as np
        from faster_whisper import WhisperModel
        cfg = yaml.safe_load(args.config.read_text(encoding="utf-8-sig"))["transcription"]
        model = WhisperModel(cfg["model"], device="cpu", compute_type="int8", cpu_threads=cfg.get("threads", 2))
        segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language=cfg.get("language", "es"), vad_filter=True)
        list(segments)
        print("Modelo preparado. Render local offline disponible.")
        return
    if args.diagnose:
        from importlib.metadata import version
        print(json.dumps({"python": sys.version, "ffmpeg": shutil.which("ffmpeg"),
                          "ffprobe": shutil.which("ffprobe"), "faster-whisper": version("faster-whisper"),
                          "libass": " ass " in run(["ffmpeg", "-hide_banner", "-filters"]),
                          "api_paid": False}, indent=2))
        return
    if not args.target:
        ap.error("Indica carpeta Reel o semana.")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            ap.error(f"Falta {binary} en PATH.")
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8-sig"))
    if args.preview:
        cfg["video"].update(width=360, height=640, preset="veryfast", crf=24)
    targets = [args.target]
    if args.week:
        targets = sorted((p for p in args.target.iterdir() if p.is_dir() and p.name.lower().startswith("reel")),
                         key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])
        if not targets:
            ap.error("No hay carpetas Reel.")
    failures = 0
    for target in targets:
        try:
            process_reel(target, cfg, args.plan_only, args.preview)
        except Exception as exc:
            failures += 1
            print(f"ERROR {target}: {exc}", file=sys.stderr, flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
