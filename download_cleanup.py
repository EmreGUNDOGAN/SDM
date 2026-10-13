"""Remove an exact download's files only after its writer has stopped."""
from pathlib import Path
import shutil


def delete_download_files(record, task=None, timeout=45):
    if task:
        task.cancel()
        worker = getattr(task, '_worker', None) or getattr(task, '_thread', None)
        if worker and worker.is_alive():
            worker.join(timeout)
            if worker.is_alive():
                raise RuntimeError('İndirme henüz durmadı. Biraz sonra silmeyi tekrar deneyin.')
    target = Path(record['filepath'])
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
        stage = target.parent / f'.sdm-video-{did}'
        if stage.exists():
            # Resolve and verify this exact per-download directory before recursion.
            if stage.is_symlink() or stage.resolve() != target.parent.resolve() / stage.name:
                raise RuntimeError('Geçici video klasörünün yolu doğrulanamadı.')
            shutil.rmtree(stage)
    for path in paths:
        path.unlink(missing_ok=True)
