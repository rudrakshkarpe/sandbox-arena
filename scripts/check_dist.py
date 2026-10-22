"""Check release contents and write checksums without importing the source package."""

import argparse
import hashlib
import tarfile
import tomllib
import zipfile
from pathlib import Path


def check_dist(directory: Path, tag: str | None = None) -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    version = project['version']
    if tag is not None and tag != f'v{version}':
        raise ValueError('Release tag must match pyproject.toml')
    wheel = directory / f'sandbox_arena-{version}-py3-none-any.whl'
    source = directory / f'sandbox_arena-{version}.tar.gz'
    package = root / 'src' / 'sandbox_arena'
    resources = [*package.glob('scenario_packs/*.json'), *package.glob('static/*'), *package.glob('static/providers/*')]
    resources = [path for path in resources if path.is_file()]
    with zipfile.ZipFile(wheel) as archive:
        for path in resources:
            name = f'sandbox_arena/{path.relative_to(package).as_posix()}'
            if archive.read(name) != path.read_bytes():
                raise ValueError(f'Wheel resource differs from source: {name}')
        names = archive.namelist()
        if any(part in {'artifacts', '.env', '.git', '.venv'} for name in names for part in Path(name).parts):
            raise ValueError('Local state must not be included in release archives')
        metadata = archive.read(f'sandbox_arena-{version}.dist-info/METADATA').decode()
        if f'Version: {version}\n' not in metadata:
            raise ValueError('Wheel metadata version mismatch')
    with tarfile.open(source) as archive:
        names = archive.getnames()
        if any(part in {'artifacts', '.env', '.git', '.venv'} for name in names for part in Path(name).parts):
            raise ValueError('Local state must not be included in release archives')
        for path in package.glob('scenario_packs/*.json'):
            name = f'sandbox_arena-{version}/src/sandbox_arena/scenario_packs/{path.name}'
            member = archive.extractfile(name)
            if member is None or member.read() != path.read_bytes():
                raise ValueError(f'Source archive is missing a scenario: {path.name}')
    artifacts = [wheel, source]
    (directory / 'SHA256SUMS').write_text(
        ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in artifacts)
    )
    print(f'Checked {len(resources)} packaged resources; wrote SHA256SUMS for {version}')
    return artifacts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path('dist'))
    parser.add_argument('--tag')
    args = parser.parse_args()
    check_dist(args.dist, args.tag)
