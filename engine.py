import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

class ConversionJob:
    def __init__(self, file_path, src_format, target_format):
        self.file_path = Path(file_path)
        self.src_format = src_format.lower()
        self.target_format = target_format.lower()
        self.status = "Pending"  # Pending, Converting, Completed, Failed, Cancelled
        self.progress = 0.0      # 0.0 to 1.0
        self.error_msg = ""
        self.dest_path = None
        self.temp_files = []
        self.process = None      # Keep track of active Popen process
        self.cancelled = False

    def clean_temps(self):
        for temp in self.temp_files:
            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception:
                pass
        self.temp_files.clear()

class ConverterEngine:
    def __init__(self, settings):
        self.settings = settings
        self.ffmpeg_path = "ffmpeg"
        self.magick_path = "magick"
        self.validate_engines()

    def validate_engines(self):
        self.ffmpeg_available = shutil.which(self.ffmpeg_path) is not None
        self.magick_available = shutil.which(self.magick_path) is not None

    def run_command(self, cmd, job: ConversionJob, on_progress=None, start_prog=0.1, end_prog=0.9):
        if job.cancelled:
            raise Exception("Cancelled")

        job.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stderr_lines = []

        def reader_thread(proc, job, start_prog, end_prog, on_progress):
            total_seconds = None
            try:
                for line in proc.stderr:
                    if job.cancelled:
                        break
                    line = line.strip()
                    stderr_lines.append(line)
                    if "Duration:" in line and not total_seconds:
                        try:
                            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
                            h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                            total_seconds = h * 3600 + m * 60 + s
                        except Exception:
                            pass
                    if "time=" in line and total_seconds:
                        try:
                            time_part = line.split("time=")[1].split()[0].strip()
                            parts = time_part.split(":")
                            h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                            curr_seconds = h * 3600 + m * 60 + s
                            pct = min(max(curr_seconds / total_seconds, 0.0), 1.0)
                            job.progress = start_prog + (end_prog - start_prog) * pct
                            if on_progress:
                                on_progress(job)
                        except Exception:
                            pass
            except Exception:
                pass

        t = threading.Thread(target=reader_thread, args=(job.process, job, start_prog, end_prog, on_progress), daemon=True)
        t.start()

        while True:
            ret = job.process.poll()
            if ret is not None:
                t.join(timeout=2.0)
                if ret != 0:
                    err_tail = "\n".join(stderr_lines[-10:]) if stderr_lines else ""
                    raise Exception(f"Process failed (code {ret}): {err_tail}")
                break

            if job.cancelled:
                job.process.kill()
                job.process.wait()
                t.join(timeout=2.0)
                raise Exception("Cancelled")

            time.sleep(0.05)

        job.process = None

    def convert(self, job: ConversionJob, output_dir=None, on_progress=None):
        if job.cancelled:
            job.status = "Cancelled"
            return

        job.status = "Converting"
        job.progress = 0.1
        if on_progress:
            on_progress(job)

        # Determine target file path
        out_folder = Path(output_dir) if output_dir else job.file_path.parent
        target_filename = job.file_path.stem + f".{job.target_format}"
        job.dest_path = out_folder / target_filename

        # Avoid collision if overwriting is disabled
        if not self.settings.get("overwrite_existing", True) and job.dest_path.exists():
            counter = 1
            while True:
                candidate = out_folder / f"{job.file_path.stem}_{counter}.{job.target_format}"
                if not candidate.exists():
                    job.dest_path = candidate
                    break
                counter += 1

        src_ext = job.file_path.suffix.lower()
        dest_ext = f".{job.target_format}"

        try:
            # Check engines
            if src_ext in [".gif", ".mp4", ".webm", ".mov", ".webp"] and not self.ffmpeg_available:
                raise Exception("FFmpeg not found. Please install FFmpeg.")
            needs_magick = (src_ext == ".webp") or (src_ext == ".gif" and dest_ext == ".webp")
            if needs_magick and not self.magick_available:
                raise Exception("ImageMagick not found. Please install ImageMagick.")

            # --- CONVERSION ROUTINES ---
            # 1. WebP to MP4
            if src_ext == ".webp" and dest_ext == ".mp4":
                fd, temp_gif = tempfile.mkstemp(suffix=".gif")
                os.close(fd)
                job.temp_files.append(temp_gif)
                
                cmd1 = [self.magick_path, str(job.file_path), "-coalesce", temp_gif]
                self.run_command(cmd1, job, on_progress=on_progress, start_prog=0.1, end_prog=0.5)
                
                job.progress = 0.5
                if on_progress:
                    on_progress(job)
                
                cmd2 = [
                    self.ffmpeg_path, "-y", "-f", "gif", "-i", temp_gif,
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-movflags", "faststart", "-pix_fmt", "yuv420p", str(job.dest_path)
                ]
                self.run_command(cmd2, job, on_progress=on_progress, start_prog=0.5, end_prog=0.9)

            # 2. MP4 to GIF
            elif src_ext == ".mp4" and dest_ext == ".gif":
                fps = self.settings.get("gif_fps", "15")
                width = self.settings.get("gif_width", "480")
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                    str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 3. GIF to MP4
            elif src_ext == ".gif" and dest_ext == ".mp4":
                cmd = [
                    self.ffmpeg_path, "-y", "-f", "gif", "-i", str(job.file_path),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-movflags", "faststart", "-pix_fmt", "yuv420p", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 4. MOV to MP4
            elif src_ext == ".mov" and dest_ext == ".mp4":
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-c:v", "libx264", "-c:a", "aac", "-strict", "experimental", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 5. MP4 to MOV
            elif src_ext == ".mp4" and dest_ext == ".mov":
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-c:v", "copy", "-c:a", "copy", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 6. WEBM to MP4
            elif src_ext == ".webm" and dest_ext == ".mp4":
                crf = self.settings.get("video_crf", "23")
                preset = self.settings.get("video_preset", "fast")
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-c:v", "libx264", "-crf", crf, "-preset", preset,
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 7. MP4 to WEBM
            elif src_ext == ".mp4" and dest_ext == ".webm":
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                    "-b:a", "128k", "-c:a", "libvorbis", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 8. MP4 to WEBP
            elif src_ext == ".mp4" and dest_ext == ".webp":
                fps = self.settings.get("gif_fps", "15")
                cmd = [
                    self.ffmpeg_path, "-y", "-i", str(job.file_path),
                    "-vcodec", "libwebp", "-filter_complex", f"[0:v] fps=fps={fps} [v]",
                    "-map", "[v]", "-loop", "0", str(job.dest_path)
                ]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 9. WEBP to GIF
            elif src_ext == ".webp" and dest_ext == ".gif":
                cmd = [self.magick_path, str(job.file_path), "-coalesce", str(job.dest_path)]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 10. GIF to WEBP
            elif src_ext == ".gif" and dest_ext == ".webp":
                cmd = [self.magick_path, str(job.file_path), str(job.dest_path)]
                self.run_command(cmd, job, on_progress=on_progress, start_prog=0.1, end_prog=0.9)

            # 11. GENERAL TRANSCODE VIA MP4 (FALLBACK PATHWAY)
            else:
                job.progress = 0.3
                if on_progress:
                    on_progress(job)

                sub_job_1 = ConversionJob(job.file_path, src_ext[1:], "mp4")
                self.convert(sub_job_1, output_dir=tempfile.gettempdir(), on_progress=None)

                if sub_job_1.status == "Failed":
                    raise Exception(f"Intermediate conversion failed: {sub_job_1.error_msg}")
                elif sub_job_1.status == "Cancelled":
                    raise Exception("Cancelled")

                job.temp_files.append(str(sub_job_1.dest_path))

                job.progress = 0.6
                if on_progress:
                    on_progress(job)

                sub_job_2 = ConversionJob(sub_job_1.dest_path, "mp4", job.target_format)
                self.convert(sub_job_2, output_dir=str(out_folder), on_progress=None)

                if sub_job_2.status == "Failed":
                    raise Exception(f"Final stage conversion failed: {sub_job_2.error_msg}")
                elif sub_job_2.status == "Cancelled":
                    raise Exception("Cancelled")

            # Conversion Succeeded!
            job.status = "Completed"
            job.progress = 1.0
            job.clean_temps()
            if on_progress:
                on_progress(job)

        except Exception as e:
            if str(e) == "Cancelled" or job.cancelled:
                job.status = "Cancelled"
                job.progress = 0.0
            else:
                job.status = "Failed"
                job.error_msg = str(e)
            job.clean_temps()
            if on_progress:
                on_progress(job)
