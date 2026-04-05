"""
Backward-compatible entry point — delegates to src.generate.pipeline.

Run:  python world_gen.py
"""
from src.generate.pipeline import generate_world

if __name__ == "__main__":
    generate_world()
