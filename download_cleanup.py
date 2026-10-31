"""Remove an exact download's files only after its writer has stopped."""
from pathlib import Path
import shutil


def video_staging(dest_folder, did):
    """yt-dlp work folder of one download, kept out of the user's download folder.

    Downloads paused before 1.0.1 resume from their old in-place folder.
    """
    legacy = Path(dest_folder) / f'.sdm-video-{int(did)}'
    if legacy.is_dir():
        return legacy
    from utils import ensure_config_dir
    return ensure_config_dir() / 'staging' / f'video-{int(did)}'


def remove_staging(stage, dest_folder, did):
    """Delete exactly this download's work folder (either location), nothing else."""
    from utils import ensure_config_dir
    stage = Path(stage)
    if not stage.exists():
        return
    expected = {(Path(dest_folder).resolve() / f'.sdm-video-{int(did)}'),
                (ensure_config_dir().resolve() / 'staging' / f'video-{int(did)}')}
    # Resolve and verify this exact per-download directory before recursion.
    if stage.is_symlink() or stage.resolve() not in expected:
        raise RuntimeError('Geçici video klasörünün yolu doğrulanamadı.')
    shutil.rmtree(stage)


def delete_download_files(record, task=None, timeout=45):
    if task:
        task.cancel()
        worker = getattr(task, '_worker', None) or getattr(task, '_thread', None)
        if worker and worker.is_alive():
            worker.join(timeout)
            if worker.is_alive():
                raise RuntimeError('İndirme henüz durmadı. Biraz sonra silmeyi tekrar deneyin.')
    actual_path=getattr(task,'dest_path',None) or getattr(task,'target_filepath',None) if task else None
    target = Path(actual_path or record['filepath'])
    did = int(record['id'])
    paths = [target, target.with_name(target.name + '.temp_final'),
             target.with_name(f'{target.name}.sdm-{did}.temp_final')]
    for index in range(32):
        paths += [target.with_name(f'{target.name}.part.{index}'),
                  target.with_name(f'{target.name}.sdm-{did}.part.{index}')]
    # Legacy yt-dlp temporary files: exact basename and numbered format IDs.
    if record.get('download_type') == 'video':
        import re
        pattern = re.compile(re.escape(target.stem) + r'(?:\.f\d+)?\.(?:mp4|mkv|webm|m4a|mp3|opus)(?:\.part(?:-Frag\d+)?|\.ytdl)')
        if target.parent.exists():
            paths += [p for p in target.parent.iterdir() if pattern.fullmatch(p.name)]
        remove_staging(target.parent / f'.sdm-video-{did}', target.parent, did)
        remove_staging(video_staging(target.parent, did), target.parent, did)
        from utils import ensure_config_dir
        (ensure_config_dir() / 'staging' / f'album-{did}.json').unlink(missing_ok=True)
    for path in paths:
        # An album row points at its Artist/Album folder; its songs stay.
        if not path.is_dir():
            path.unlink(missing_ok=True)
