"""Load reviewed package resources only; never resolve user-supplied paths."""

from importlib.resources import files

from .evidence_integrity import digest
from .scenario_models import ScenarioPack


def load_catalog() -> dict[str, ScenarioPack]:
    packs = {}
    root = files('sandbox_arena').joinpath('scenario_packs')
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.name.endswith('.json'):
            pack = ScenarioPack.model_validate_json(path.read_text())
            if path.name != f'{pack.id}.json' or pack.id in packs:
                raise ValueError(f'Conflicting scenario identity: {path.name}')
            packs[pack.id] = pack
    return packs


PACKS = load_catalog()


def pack_digest(pack: ScenarioPack) -> str:
    return digest(pack.model_dump(mode='json'))


def catalog_entries() -> list[dict]:
    return [{**pack.model_dump(mode='json'), 'sha256': pack_digest(pack)} for pack in PACKS.values()]
