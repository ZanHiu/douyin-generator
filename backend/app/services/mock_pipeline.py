from app.core.config import settings
from app.services.audio_extractor_service import AudioExtractorService
from app.services.errors import ProcessingError
from app.services.job_service import JobService
from app.services.storage_service import StorageService
from app.services.subtitle_service import SubtitleService
from app.services.tts_service import TTSService
from app.services.transcription_service import TranscriptionService
from app.services.translation_service import TranslationService
from app.services.video_renderer_service import VideoRendererService
from app.services.video_resolver_service import VideoResolverService


class MockPipeline:
    def __init__(
        self,
        jobs: JobService,
        storage: StorageService | None = None,
        video_resolver: VideoResolverService | None = None,
        audio_extractor: AudioExtractorService | None = None,
        transcription: TranscriptionService | None = None,
        translation: TranslationService | None = None,
        subtitle: SubtitleService | None = None,
        tts: TTSService | None = None,
        renderer: VideoRendererService | None = None,
    ) -> None:
        self.jobs = jobs
        self.storage = storage or StorageService()
        self.video_resolver = video_resolver or VideoResolverService(self.storage)
        self.audio_extractor = audio_extractor or AudioExtractorService(self.storage)
        self.transcription = transcription or TranscriptionService(self.storage)
        self.translation = translation or TranslationService(self.storage)
        self.subtitle = subtitle or SubtitleService(self.storage)
        self.tts = tts or TTSService(self.storage)
        self.renderer = renderer or VideoRendererService(self.storage)

    def run(self, job_id: str) -> None:
        job = self.jobs.get_job(job_id)
        if job is None:
            raise ProcessingError("UNKNOWN_ERROR", f"Job not found: {job_id}")
        self._check_cancel(job_id)

        self._stage(job_id, "fetching_video", 10, "Downloading source video")
        if job.input_video_path:
            input_video_path = str(self.storage.resolve_path(job.input_video_path))
            metadata_path = str(self.storage.job_dir(job_id) / "metadata.json")
            self.jobs.log(
                job_id,
                "info",
                "fetching_video",
                "Using uploaded source video",
                {"input_video_path": input_video_path},
            )
        else:
            input_video_path, metadata_path = self.video_resolver.fetch(job_id, job.source_url)
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "input_video_path", input_video_path)
        self.jobs.log(
            job_id,
            "info",
            "fetching_video",
            "Video downloaded",
            {"input_video_path": input_video_path, "metadata_path": metadata_path},
        )

        self._stage(job_id, "extracting_audio", 25, "Extracting audio with FFmpeg")
        audio_path = self.audio_extractor.extract(job_id, input_video_path)
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "audio_path", audio_path)
        self.jobs.log(job_id, "info", "extracting_audio", "Audio extracted", {"audio_path": audio_path})

        self._stage(job_id, "transcribing", 40, "Generating Chinese transcript")
        transcript_zh_path = self.transcription.transcribe(
            job_id,
            audio_path,
            cancel_checker=lambda: self.jobs.is_cancel_requested(job_id),
            progress_logger=lambda message: self.jobs.log(job_id, "info", "transcribing", message),
        )
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "transcript_zh_path", transcript_zh_path)
        self.jobs.log(
            job_id,
            "info",
            "transcribing",
            "Transcript generated",
            {"transcript_zh_path": transcript_zh_path},
        )

        self._stage(job_id, "translating", 55, "Translating transcript to Vietnamese")
        transcript_vi_path = self.translation.translate(job_id, transcript_zh_path)
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "transcript_vi_path", transcript_vi_path)
        self.jobs.log(
            job_id,
            "info",
            "translating",
            "Translation generated",
            {"transcript_vi_path": transcript_vi_path},
        )

        self._stage(job_id, "generating_subtitles", 70, "Generating SRT subtitle")
        subtitle_path = self.subtitle.generate_srt(job_id, transcript_vi_path)
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "subtitle_path", subtitle_path)
        self.jobs.log(
            job_id,
            "info",
            "generating_subtitles",
            "Subtitle generated",
            {"subtitle_path": subtitle_path},
        )

        self._stage(job_id, "generating_tts", 82, "Generating Vietnamese voice audio")
        tts_path = self.tts.generate_voice(job_id, transcript_vi_path, job.voice_id)
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "tts_audio_path", tts_path)
        self.jobs.log(job_id, "info", "generating_tts", "Voice audio generated", {"tts_audio_path": tts_path})

        self._stage(job_id, "rendering_video", 94, "Rendering final video")
        final_render_config = job.final_config_json or self.jobs.build_editor_baseline_config(job)
        output_path = self.renderer.render(
            job_id,
            input_video_path,
            tts_path,
            subtitle_path,
            original_audio_path=audio_path,
            mix_original_audio=job.mix_original_audio,
            burn_subtitle=job.burn_subtitle,
            subtitle_font_size=final_render_config["subtitle_font_size"],
            subtitle_position=final_render_config["subtitle_position"],
            subtitle_text_color=final_render_config["subtitle_text_color"],
        )
        self._check_cancel(job_id)
        self.jobs.attach_artifact(job_id, "final_config_json", final_render_config)
        self.jobs.attach_artifact(job_id, "output_video_path", output_path)
        self.jobs.log(
            job_id,
            "info",
            "rendering_video",
            "Video rendered",
            {"output_video_path": output_path, "final_render_config": final_render_config},
        )

        self.jobs.mark_completed(job_id)

    def _stage(self, job_id: str, stage: str, progress: int, message: str) -> None:
        if settings.mock_fail_stage == stage:
            raise RuntimeError(f"Forced mock failure at stage: {stage}")
        self.jobs.mark_processing(job_id, stage, progress, message)

    def _check_cancel(self, job_id: str) -> None:
        if self.jobs.is_cancelled(job_id) or self.jobs.is_cancel_requested(job_id):
            raise ProcessingError("JOB_CANCELLED", "Job cancelled")
