import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from typing import Dict, List, Optional

import yt_dlp
from yt_dlp.utils import DownloadCancelled


@dataclass
class FormatChoice:
    label: str
    format_id: str
    ext: str
    info: Dict


class YoutubeDownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YouTube Downloader (Python)")
        self.root.geometry("720x520")
        self.root.resizable(False, False)

        self.info_queue: "queue.Queue" = queue.Queue()
        self.video_choices: List[FormatChoice] = []
        self.audio_choices: List[FormatChoice] = []
        self.current_info: Optional[Dict] = None
        self.current_display_info: Optional[Dict] = None
        self.current_url: str = ""
        self.is_playlist = False
        self.playlist_count = 0
        self.download_thread: Optional[threading.Thread] = None
        self.cancel_requested = False

        self._build_ui()
        self._poll_queue()

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}

        url_frame = ttk.LabelFrame(self.root, text="YouTube URL")
        url_frame.pack(fill=tk.X, **padding)

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=80)
        url_entry.pack(side=tk.LEFT, padx=5, pady=8, expand=True, fill=tk.X)
        url_entry.focus_set()

        fetch_btn = ttk.Button(url_frame, text="Info laden", command=self.fetch_info)
        fetch_btn.pack(side=tk.RIGHT, padx=5, pady=8)

        info_frame = ttk.LabelFrame(self.root, text="Video-Informationen")
        info_frame.pack(fill=tk.X, **padding)

        self.title_var = tk.StringVar(value="Titel: -")
        self.duration_var = tk.StringVar(value="Dauer: -")
        self.channel_var = tk.StringVar(value="Kanal: -")

        ttk.Label(info_frame, textvariable=self.title_var).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Label(info_frame, textvariable=self.duration_var).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Label(info_frame, textvariable=self.channel_var).pack(anchor=tk.W, padx=8, pady=2)

        format_frame = ttk.LabelFrame(self.root, text="Format-Auswahl")
        format_frame.pack(fill=tk.X, **padding)

        self.download_type = tk.StringVar(value="video")
        ttk.Radiobutton(format_frame, text="Video (MP4)", variable=self.download_type, value="video", command=self._toggle_format_controls).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Radiobutton(format_frame, text="Audio", variable=self.download_type, value="audio", command=self._toggle_format_controls).pack(anchor=tk.W, padx=8, pady=2)

        self.video_combo = ttk.Combobox(format_frame, state="readonly")
        self.audio_combo = ttk.Combobox(format_frame, state="readonly")
        self.video_combo.pack(fill=tk.X, padx=12, pady=4)
        self.audio_combo.pack(fill=tk.X, padx=12, pady=4)

        output_frame = ttk.LabelFrame(self.root, text="Speicherort")
        output_frame.pack(fill=tk.X, **padding)

        self.output_var = tk.StringVar(value=os.getcwd())
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=60)
        output_entry.pack(side=tk.LEFT, padx=5, pady=8, fill=tk.X, expand=True)

        browse_btn = ttk.Button(output_frame, text="Ordner wählen", command=self.choose_directory)
        browse_btn.pack(side=tk.RIGHT, padx=5, pady=8)

        progress_frame = ttk.LabelFrame(self.root, text="Download")
        progress_frame.pack(fill=tk.BOTH, expand=True, **padding)

        self.progress = ttk.Progressbar(progress_frame, length=580, mode="determinate")
        self.progress.pack(padx=12, pady=12)

        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W, padx=12, pady=2)

        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=8)

        self.download_btn = ttk.Button(button_frame, text="Download starten", command=self.start_download, state=tk.DISABLED)
        self.download_btn.grid(row=0, column=0, padx=5)

        self.cancel_btn = ttk.Button(button_frame, text="Abbrechen", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=1, padx=5)

        self._toggle_format_controls()

    def choose_directory(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)

    def fetch_info(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Fehler", "Bitte gib eine gültige URL ein.")
            return

        self.status_var.set("Lade Video-Informationen...")
        self.download_btn.config(state=tk.DISABLED)
        self.video_combo.set("")
        self.audio_combo.set("")
        self.video_choices.clear()
        self.audio_choices.clear()

        thread = threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True)
        thread.start()

    def _fetch_info_thread(self, url: str) -> None:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": False,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if (info.get("_type") in {"playlist", "multi_video"}) or info.get("entries"):
                    entries = [entry for entry in (info.get("entries") or []) if entry]
                    if entries:
                        first_entry = entries[0]
                        if not first_entry.get("formats"):
                            entry_url = first_entry.get("webpage_url") or first_entry.get("url")
                            if entry_url:
                                try:
                                    detailed = ydl.extract_info(entry_url, download=False)
                                except Exception:
                                    detailed = first_entry
                                info["_first_entry"] = detailed
                            else:
                                info["_first_entry"] = first_entry
                        else:
                            info["_first_entry"] = first_entry
        except Exception as exc:
            self.info_queue.put(("error", f"Fehler beim Laden der Informationen: {exc}"))
            return

        self.info_queue.put(("info", info))

    def start_download(self) -> None:
        if not self.current_info:
            messagebox.showwarning("Fehler", "Bitte lade zuerst die Video-Informationen.")
            return

        download_type = self.download_type.get()
        if download_type == "video":
            selection = self.video_combo.current()
            choices = self.video_choices
        else:
            selection = self.audio_combo.current()
            choices = self.audio_choices

        if selection < 0 or selection >= len(choices):
            messagebox.showwarning("Fehler", "Bitte wähle ein Format aus.")
            return

        format_choice = choices[selection]
        output_dir = self.output_var.get()
        if not os.path.isdir(output_dir):
            messagebox.showwarning("Fehler", "Bitte gib einen gültigen Zielordner an.")
            return

        self.progress.config(value=0)
        self.cancel_requested = False
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_var.set("Playlist-Download läuft..." if self.is_playlist else "Download läuft...")

        format_selector = self._build_format_selector(format_choice, download_type)
        self.download_thread = threading.Thread(
            target=self._download_thread,
            args=(self.current_url, format_selector, output_dir, self.is_playlist),
            daemon=True,
        )
        self.download_thread.start()

    def cancel_download(self) -> None:
        if self.download_thread and self.download_thread.is_alive():
            self.cancel_requested = True
            self.status_var.set("Abbruch wird vorbereitet...")

    def _build_format_selector(self, choice: FormatChoice, download_type: str) -> str:
        base = choice.format_id or "best"
        if download_type == "video":
            return f"{base}/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
        return f"{base}/bestaudio/best"

    def _download_thread(self, url: str, format_selector: str, output_dir: str, is_playlist: bool) -> None:
        def progress_hook(data: Dict) -> None:
            if self.cancel_requested:
                raise DownloadCancelled("Vom Benutzer abgebrochen")

            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                speed = data.get("speed") or 0
                eta = data.get("eta")
                info_dict = data.get("info_dict") or {}
                self.info_queue.put(
                    (
                        "progress",
                        {
                            "percent": percent,
                            "downloaded": downloaded,
                            "total": total,
                            "speed": speed,
                            "eta": eta,
                            "playlist_index": info_dict.get("playlist_index"),
                            "playlist_count": info_dict.get("playlist_count"),
                        },
                    )
                )
            elif status == "finished":
                info_dict = data.get("info_dict") or {}
                self.info_queue.put(
                    (
                        "progress",
                        {
                            "percent": 100.0,
                            "status": "finished",
                            "playlist_index": info_dict.get("playlist_index"),
                            "playlist_count": info_dict.get("playlist_count"),
                        },
                    )
                )

        outtmpl = os.path.join(
            output_dir,
            "%(playlist_index)s - %(title)s.%(ext)s" if is_playlist else "%(title)s.%(ext)s",
        )
        ydl_opts = {
            "format": format_selector,
            "outtmpl": outtmpl,
            "noplaylist": not is_playlist,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except DownloadCancelled:
            self.info_queue.put(("cancelled", "Download abgebrochen."))
        except Exception as exc:
            self.info_queue.put(("error", f"Download fehlgeschlagen: {exc}"))
        else:
            message = "Playlist-Download abgeschlossen." if is_playlist else "Download abgeschlossen."
            self.info_queue.put(("done", message))

    def _toggle_format_controls(self) -> None:
        if self.download_type.get() == "video":
            self.video_combo.config(state="readonly" if self.video_choices else tk.DISABLED)
            self.audio_combo.config(state=tk.DISABLED)
        else:
            self.video_combo.config(state=tk.DISABLED)
            self.audio_combo.config(state="readonly" if self.audio_choices else tk.DISABLED)

    def _update_info(self, info: Dict) -> None:
        self.current_info = info
        self.is_playlist = (info.get("_type") in {"playlist", "multi_video"}) or bool(info.get("entries"))
        self.playlist_count = 0

        if self.is_playlist:
            entries = [entry for entry in (info.get("entries") or []) if entry]
            self.playlist_count = len(entries)
            display_info = info.get("_first_entry") or (entries[0] if entries else info)
            playlist_title = info.get("title") or "-"
            channel = info.get("uploader") or info.get("channel") or "-"
            self.title_var.set(f"Titel: {playlist_title} (Playlist)")
            self.duration_var.set(f"Inhalte: {self.playlist_count} Videos")
            self.channel_var.set(f"Ersteller: {channel}")
            status_note = "Playlist erkannt. Alle Elemente werden heruntergeladen."
        else:
            display_info = info
            title = info.get("title") or "-"
            duration = info.get("duration") or 0
            channel = info.get("uploader") or info.get("channel") or "-"

            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                duration_text = f"{hours:d}:{minutes:02d}:{seconds:02d}"
            else:
                duration_text = f"{minutes:d}:{seconds:02d}"

            self.title_var.set(f"Titel: {title}")
            self.duration_var.set(f"Dauer: {duration_text}")
            self.channel_var.set(f"Kanal: {channel}")
            status_note = "Informationen geladen. Wähle ein Format aus."

        self.current_display_info = display_info
        self.current_url = info.get("webpage_url") or info.get("url") or self.url_var.get()

        if display_info and display_info is not info and not display_info.get("formats"):
            entry_url = display_info.get("webpage_url") or display_info.get("url")
            if entry_url:
                try:
                    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
                        enriched = ydl.extract_info(entry_url, download=False)
                    display_info = enriched
                    self.current_display_info = enriched
                except Exception:
                    pass

        self._populate_format_choices(self.current_display_info or info)
        self.status_var.set(status_note)
        self.download_btn.config(state=tk.NORMAL)

    def _populate_format_choices(self, info: Dict) -> None:
        formats = info.get("formats") or []

        def human_size(value: Optional[float]) -> str:
            if not value:
                return "Unbekannt"
            for unit in ["B", "KB", "MB", "GB"]:
                if value < 1024 or unit == "GB":
                    return f"{value:.1f} {unit}"
                value /= 1024
            return f"{value:.1f} TB"

        mp4_formats = [
            f for f in formats
            if f.get("vcodec") not in (None, "none")
            and f.get("ext") == "mp4"
        ]
        mp4_formats.sort(key=lambda f: (-(f.get("height") or 0), -(f.get("fps") or 0)))

        self.video_choices = []
        video_labels = []
        for fmt in mp4_formats:
            height = fmt.get("height") or 0
            fps = fmt.get("fps") or 0
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
            bitrate = fmt.get("tbr") or 0
            label_parts = [f"{height}p"] if height else ["Unbekannte Auflösung"]
            if fps:
                label_parts.append(f"{fps}fps")
            if bitrate:
                label_parts.append(f"~{int(bitrate)}kbps")
            label_parts.append(f"{human_size(filesize)}")
            label = " | ".join(label_parts)
            self.video_choices.append(FormatChoice(label=label, format_id=fmt.get("format_id"), ext=fmt.get("ext"), info=fmt))
            video_labels.append(label)

        audio_formats = [
            f for f in formats
            if f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none")
        ]
        audio_formats.sort(key=lambda f: -(f.get("abr") or f.get("tbr") or 0))

        self.audio_choices = []
        audio_labels = []
        for fmt in audio_formats:
            abr = fmt.get("abr") or fmt.get("tbr") or 0
            ext = fmt.get("ext") or "audio"
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
            label = f"{int(abr)}kbps {ext.upper()} | {human_size(filesize)}"
            self.audio_choices.append(FormatChoice(label=label, format_id=fmt.get("format_id"), ext=fmt.get("ext"), info=fmt))
            audio_labels.append(label)

        if not video_labels:
            video_labels = ["Keine MP4-Formate gefunden"]
        if not audio_labels:
            audio_labels = ["Keine Audio-Formate gefunden"]

        self.video_combo.config(values=video_labels)
        self.audio_combo.config(values=audio_labels)

        if self.video_choices:
            self.video_combo.current(0)
        else:
            self.video_combo.set(video_labels[0])

        if self.audio_choices:
            self.audio_combo.current(0)
        else:
            self.audio_combo.set(audio_labels[0])

        # fallback to available type if current selection has no options
        if self.download_type.get() == "video" and not self.video_choices and self.audio_choices:
            self.download_type.set("audio")
        elif self.download_type.get() == "audio" and not self.audio_choices and self.video_choices:
            self.download_type.set("video")

        has_options = bool(self.video_choices or self.audio_choices)
        self.download_btn.config(state=tk.NORMAL if has_options else tk.DISABLED)
        if not has_options:
            self.status_var.set("Keine passenden Formate gefunden.")

        self._toggle_format_controls()

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.info_queue.get_nowait()
                msg_type = item[0]

                if msg_type == "info":
                    self._update_info(item[1])
                elif msg_type == "progress":
                    data = item[1]
                    percent = data.get("percent", 0)
                    self.progress.config(value=percent)
                    downloaded = data.get("downloaded")
                    total = data.get("total")
                    speed = data.get("speed")
                    eta = data.get("eta")
                    playlist_index = data.get("playlist_index")
                    playlist_count = data.get("playlist_count") or (self.playlist_count or None)
                    status_flag = data.get("status")

                    parts = []
                    if downloaded is not None and total:
                        parts.append(f"{downloaded / 1024 / 1024:.2f} / {total / 1024 / 1024:.2f} MB")
                    elif downloaded is not None:
                        parts.append(f"{downloaded / 1024 / 1024:.2f} MB")
                    if speed:
                        parts.append(f"{speed / 1024:.1f} KB/s")
                    if eta:
                        parts.append(f"ETA {int(eta)}s")
                    prefix = ""
                    if playlist_index:
                        index_text = f"Video {int(playlist_index)}"
                        if playlist_count:
                            index_text += f"/{int(playlist_count)}"
                        prefix = f"{index_text}: "
                    if status_flag == "finished":
                        if prefix:
                            self.status_var.set(f"{prefix}abgeschlossen.")
                        else:
                            self.status_var.set("Download abgeschlossen.")
                    elif parts:
                        self.status_var.set(prefix + " ".join(parts))
                    elif prefix:
                        self.status_var.set(prefix.strip())
                elif msg_type == "done":
                    self.status_var.set(item[1])
                    self.progress.config(value=100)
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.download_btn.config(state=tk.NORMAL)
                    self.cancel_requested = False
                    self.download_thread = None
                elif msg_type == "error":
                    self.status_var.set(item[1])
                    messagebox.showerror("Fehler", item[1])
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.download_btn.config(state=tk.NORMAL if self.current_info else tk.DISABLED)
                    self.cancel_requested = False
                    self.download_thread = None
                elif msg_type == "cancelled":
                    self.status_var.set(item[1])
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.download_btn.config(state=tk.NORMAL if self.current_info else tk.DISABLED)
                    self.cancel_requested = False
                    self.download_thread = None
                self.info_queue.task_done()
        except queue.Empty:
            pass

        self.root.after(150, self._poll_queue)


def main() -> None:
    root = tk.Tk()
    YoutubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
