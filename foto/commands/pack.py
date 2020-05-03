import re
import zipfile
import shutil
import functools
from pathlib import Path
from subprocess import run
import tempfile

import click
from slugify import slugify

from foto import config
from foto.logger import Logger


__all__ = ['pack']


def pack(directory):
    logger = Logger('pack')

    zip_file = Path.cwd() / directory.with_suffix('.zip').name
    if zip_file.exists():
        logger.err(f'Exists! {zip_file}')
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        for file_in in directory.rglob(f'*.*'):
            ext = parse_ext(file_in)
            if ext == 'heic':
                file_out_rel = file_in.relative_to(directory).with_suffix('.jpg')
                file_out_rel = normalize(file_out_rel)

                file_out = tmp_dir / file_out_rel
                file_out.parent.mkdir(parents=True, exist_ok=True)

                file_out_fmt = f'(zip)/{file_out_rel}'
                file_out_fmt = click.style(file_out_fmt, fg='green')
                logger.log(f"{file_in.relative_to(directory)} → {file_out_fmt}")

                run(['magick', 'convert', file_in, file_out], check=True)

            elif ext in config['media_exts']:
                file_in_rel = file_in.relative_to(directory)
                file_out = tmp_dir / normalize(file_in_rel)
                file_out_rel = file_out.relative_to(tmp_dir)
                file_out_fmt = click.style(f'(zip)/{file_out_rel}', fg='green')
                logger.log(f'{file_in_rel} → {file_out_fmt}')

                file_out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_in, file_out)

        size = config['packing']['photo_max_size']
        for file_photo in tmp_dir.rglob('*.*'):
            if parse_ext(file_photo) not in config['photo_exts']:
                continue

            logger.log(f'(zip)/{file_photo.relative_to(tmp_dir)} → {size}px')
            run(['magick', 'convert', file_photo, '-resize',
                f'{size}x{size}>', file_photo], check=True)

        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as z:
            for filename in tmp_dir.glob('**/*.*'):
                if filename.is_dir():
                    continue

                filename_rel = filename.relative_to(tmp_dir)
                logger.log(f"{filename_rel} → zip")
                z.write(filename, filename_rel)

        logger.log(click.style(str(zip_file), bold=True))


def normalize(path):
    path = Path(re.sub(r'\.jpeg$', '.jpg', str(path), re.I))
    clean = functools.partial(slugify, regex_pattern=r'[^a-z0-9\-_\.]')
    return Path(*list(map(clean, path.parts)))


def parse_ext(path):
    return path.suffix.lower().lstrip('.')