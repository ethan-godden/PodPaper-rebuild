"""Pipeline stages. Each module exposes plain functions over the models in ``types``.

Stages do no caching themselves; ``podpaper.pipeline`` wraps them with the stage cache.
"""
