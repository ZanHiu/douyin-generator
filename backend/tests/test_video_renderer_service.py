import pytest

from app.core.config import settings
from app.services.errors import ProcessingError
from app.services.storage_service import StorageService
from app.services.video_renderer_service import VideoRendererService


def test_renderer_rejects_missing_input_video(tmp_path) -> None:
    storage = StorageService(tmp_path)
    voice_path = storage.write_text("job-1", "voice_vi.wav", "voice")
    subtitle_path = storage.write_text("job-1", "subtitles_vi.srt", "subtitle")

    with pytest.raises(ProcessingError, match="input video"):
        VideoRendererService(storage).render("job-1", str(tmp_path / "missing.mp4"), voice_path, subtitle_path)


def test_renderer_rejects_missing_voice(tmp_path) -> None:
    storage = StorageService(tmp_path)
    input_path = storage.write_text("job-1", "input.mp4", "video")
    subtitle_path = storage.write_text("job-1", "subtitles_vi.srt", "subtitle")

    with pytest.raises(ProcessingError, match="voice"):
        VideoRendererService(storage).render("job-1", input_path, str(tmp_path / "missing.wav"), subtitle_path)


def test_renderer_rejects_missing_subtitle(tmp_path) -> None:
    storage = StorageService(tmp_path)
    input_path = storage.write_text("job-1", "input.mp4", "video")
    voice_path = storage.write_text("job-1", "voice_vi.wav", "voice")

    with pytest.raises(ProcessingError, match="subtitle"):
        VideoRendererService(storage).render("job-1", input_path, voice_path, str(tmp_path / "missing.srt"))


def test_subtitle_filter_path_escapes_windows_drive() -> None:
    escaped = VideoRendererService._escape_subtitle_filter_path(
        __import__("pathlib").Path("D:/SideProject/DouyinGenerator/storage/jobs/job/subtitles_vi.srt")
    )

    assert "\\:" in escaped


def test_voice_polish_args_pad_trim_and_boost_volume(tmp_path) -> None:
    voice_path = tmp_path / "voice_vi.wav"
    output_path = tmp_path / "voice_vi_render.wav"

    args = VideoRendererService._build_voice_polish_args(voice_path, output_path, 61.743)

    assert args[0] == settings.ffmpeg_bin
    assert str(voice_path) in args
    assert str(output_path) in args
    audio_filter = args[args.index("-af") + 1]
    assert f"volume={settings.voice_volume_multiplier}" in audio_filter
    assert f"loudnorm=I={settings.voice_loudnorm_target_i}" in audio_filter
    assert f"TP={settings.voice_loudnorm_target_tp}" in audio_filter
    assert f"LRA={settings.voice_loudnorm_target_lra}" in audio_filter
    assert "apad" in audio_filter
    assert "atrim=0:61.743" in audio_filter


def test_render_args_encode_player_compatible_aac_audio(tmp_path) -> None:
    input_path = tmp_path / "input.mp4"
    voice_path = tmp_path / "voice_vi_render.wav"
    subtitle_path = tmp_path / "subtitles_vi.srt"
    output_path = tmp_path / "output_vi.mp4"

    args = VideoRendererService._build_render_args(input_path, voice_path, subtitle_path, output_path)

    assert args[args.index("-map") + 1] == "0:v:0"
    assert "1:a:0" in args
    assert "-filter_complex" not in args
    assert args[args.index("-c:a") + 1] == "aac"
    assert args[args.index("-b:a") + 1] == "192k"
    assert args[args.index("-ar") + 1] == "44100"
    assert args[args.index("-ac") + 1] == "2"
    assert args[args.index("-metadata:s:a:0") + 1] == "language=vie"
    assert args[args.index("-disposition:a:0") + 1] == "default"
    assert "+faststart" in args


def test_render_args_mix_original_audio_under_voice(tmp_path) -> None:
    input_path = tmp_path / "input.mp4"
    voice_path = tmp_path / "voice_vi_render.wav"
    original_audio_path = tmp_path / "audio.wav"
    subtitle_path = tmp_path / "subtitles_vi.srt"
    output_path = tmp_path / "output_vi.mp4"

    args = VideoRendererService._build_render_args(
        input_path,
        voice_path,
        subtitle_path,
        output_path,
        original_audio_path=original_audio_path,
    )

    assert str(original_audio_path) in args
    assert args[args.index("-map") + 1] == "0:v:0"
    assert "[aout]" in args
    assert "-filter_complex" in args
    audio_filter = args[args.index("-filter_complex") + 1]
    assert f"[1:a]volume={settings.mixed_voice_volume_multiplier}[voice]" in audio_filter
    assert f"[2:a]volume={settings.original_audio_volume_multiplier}[original]" in audio_filter
    assert "amix=inputs=2:duration=first" in audio_filter


def test_render_args_blur_original_subtitle_region(tmp_path) -> None:
    input_path = tmp_path / "input.mp4"
    voice_path = tmp_path / "voice_vi_render.wav"
    subtitle_path = tmp_path / "subtitles_vi.srt"
    output_path = tmp_path / "output_vi_blurred.mp4"

    args = VideoRendererService._build_render_args(
        input_path,
        voice_path,
        subtitle_path,
        output_path,
        blur_original_subtitles=True,
        blur_height_ratio=0.25,
        blur_strength=20,
    )

    assert "-vf" not in args
    assert "-filter_complex" in args
    assert "[vout]" in args
    filter_complex = args[args.index("-filter_complex") + 1]
    assert "[0:v]split[base][blur]" in filter_complex
    assert "crop=iw*1.0000:ih*0.2200:iw*0.0000:ih*0.7800" in filter_complex
    assert "boxblur=luma_radius=20:luma_power=1" in filter_complex
    assert "overlay=W*0.0000:H*0.7800" in filter_complex
    assert "subtitles=" in filter_complex


def test_edit_render_args_support_trim_speed_audio_and_subtitle_style(tmp_path) -> None:
    input_path = tmp_path / "input.mp4"
    voice_path = tmp_path / "voice_vi_edit_render.wav"
    original_audio_path = tmp_path / "audio.wav"
    subtitle_path = tmp_path / "subtitles_vi.srt"
    output_path = tmp_path / "output_vi_edit.mp4"

    args = VideoRendererService._build_edit_render_args(
        input_path=input_path,
        voice_path=voice_path,
        original_audio_path=original_audio_path,
        subtitle_path=subtitle_path,
        output_path=output_path,
        trim_start_seconds=1.5,
        trim_end_seconds=15.0,
        playback_speed=1.25,
        blur_original_subtitles=True,
        blur_height_ratio=0.20,
        blur_strength=12,
        voice_volume_multiplier=0.9,
        original_volume_multiplier=0.3,
        include_audio=True,
        burn_subtitle=True,
        subtitle_font_size=28,
        subtitle_position="top",
        subtitle_text_color="#FFCC00",
        overlay_enabled=True,
        overlay_text="Demo overlay",
        overlay_position="top_right",
        overlay_font_size=26,
        overlay_text_color="#FFFFFF",
    )

    assert "-filter_complex" in args
    filter_complex = args[args.index("-filter_complex") + 1]
    assert "trim=start=1.500:end=15.000" in filter_complex
    assert "setpts=PTS/1.2500" in filter_complex
    assert "atrim=start=1.500:end=15.000" in filter_complex
    assert "atempo=1.2500" in filter_complex
    assert "volume=0.9000" in filter_complex
    assert "volume=0.3000" in filter_complex
    assert "amix=inputs=2:duration=longest" in filter_complex
    assert "subtitles=" in filter_complex
    assert "Fontsize=28" in filter_complex
    assert "Alignment=8" in filter_complex
    assert "PrimaryColour=&H0000CCFF" in filter_complex
    assert "drawtext=" in filter_complex
    assert "Demo overlay" in filter_complex
    assert "[vout]" in args
    assert "[aout]" in args


def test_edit_render_args_can_disable_audio_and_subtitles(tmp_path) -> None:
    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output_vi_edit.mp4"

    args = VideoRendererService._build_edit_render_args(
        input_path=input_path,
        voice_path=None,
        original_audio_path=None,
        subtitle_path=None,
        output_path=output_path,
        trim_start_seconds=0.0,
        trim_end_seconds=None,
        playback_speed=1.0,
        blur_original_subtitles=False,
        blur_height_ratio=0.22,
        blur_strength=18,
        voice_volume_multiplier=1.0,
        original_volume_multiplier=0.35,
        include_audio=False,
        burn_subtitle=False,
        subtitle_font_size=22,
        subtitle_position="bottom",
        subtitle_text_color="#FFFFFF",
        overlay_enabled=False,
        overlay_text="",
        overlay_position="top_right",
        overlay_font_size=18,
        overlay_text_color="#FFFFFF",
    )

    assert "-an" in args
    filter_complex = args[args.index("-filter_complex") + 1]
    assert "subtitles=" not in filter_complex
