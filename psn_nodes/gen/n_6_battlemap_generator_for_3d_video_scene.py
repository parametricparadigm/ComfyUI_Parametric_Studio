"""
PSN_Battlemap_Generate: Generates a top-down battlemap as a pure-logic data structure.

This module implements the core logic for generating battlemap grids and heightmaps
without relying on GPU, torch, ComfyUI, or image libraries (PIL/numpy). Instead, it
returns plain Python lists (2D arrays) representing the map and heightmap, which can
be easily converted to images by downstream nodes or external tools.

The node supports three styles:
- "grid": A simple grid pattern with alternating cell colors.
- "terrain": A pseudo-random terrain heightmap with elevation variations.
- "urban": A structured urban layout with roads and building blocks.

All outputs are deterministic based on the input parameters and a seeded random
generator for reproducibility.
"""

import random
import math

# Constants for map generation
GRID_STYLES = ["grid", "terrain", "urban"]

# Color palettes for different styles (RGB tuples)
GRID_COLORS = {
    "light": (200, 200, 200),
    "dark": (150, 150, 150),
    "border": (50, 50, 50)
}

TERRAIN_COLORS = {
    "water": (0, 100, 200),
    "sand": (220, 200, 150),
    "grass": (100, 180, 100),
    "forest": (50, 120, 50),
    "mountain": (150, 150, 150),
    "snow": (255, 255, 255)
}

URBAN_COLORS = {
    "road": (80, 80, 80),
    "building": (180, 180, 180),
    "park": (100, 180, 100),
    "water": (0, 100, 200)
}


def _generate_grid_map(width, height, cell_size, seed=42):
    """
    Generate a simple grid battlemap.
    
    Returns:
        tuple: (map_data, heightmap_data)
        - map_data: 2D list of RGB tuples
        - heightmap_data: 2D list of float values (0.0 to 1.0)
    """
    map_data = []
    heightmap_data = []
    
    for y in range(height):
        row_colors = []
        row_heights = []
        for x in range(width):
            # Alternating checkerboard pattern
            if (x + y) % 2 == 0:
                color = GRID_COLORS["light"]
            else:
                color = GRID_COLORS["dark"]
            
            # Border cells are darker
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                color = GRID_COLORS["border"]
            
            row_colors.append(color)
            # Grid has uniform height
            row_heights.append(0.5)
        
        map_data.append(row_colors)
        heightmap_data.append(row_heights)
    
    return map_data, heightmap_data


def _generate_terrain_map(width, height, cell_size, seed=42):
    """
    Generate a terrain battlemap with pseudo-random elevation.
    
    Uses a simple value noise approach for smooth terrain.
    
    Returns:
        tuple: (map_data, heightmap_data)
        - map_data: 2D list of RGB tuples
        - heightmap_data: 2D list of float values (0.0 to 1.0)
    """
    rng = random.Random(seed)
    
    # Generate base noise
    noise = []
    for y in range(height):
        row = []
        for x in range(width):
            # Simple pseudo-random value with some smoothing
            base = rng.random()
            # Add some structure based on position
            structure = 0.3 * math.sin(x * 0.5) * math.cos(y * 0.5)
            value = max(0.0, min(1.0, base * 0.7 + structure * 0.3 + 0.5))
            row.append(value)
        noise.append(row)
    
    # Smooth the noise (simple box blur)
    smoothed = []
    for y in range(height):
        row = []
        for x in range(width):
            total = 0.0
            count = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ny = y + dy
                    nx = x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        total += noise[ny][nx]
                        count += 1
            row.append(total / count if count > 0 else 0.5)
        smoothed.append(row)
    
    # Convert to colors and heightmap
    map_data = []
    heightmap_data = []
    
    for y in range(height):
        row_colors = []
        row_heights = []
        for x in range(width):
            h = smoothed[y][x]
            
            # Map height to color
            if h < 0.2:
                color = TERRAIN_COLORS["water"]
            elif h < 0.35:
                color = TERRAIN_COLORS["sand"]
            elif h < 0.55:
                color = TERRAIN_COLORS["grass"]
            elif h < 0.75:
                color = TERRAIN_COLORS["forest"]
            elif h < 0.9:
                color = TERRAIN_COLORS["mountain"]
            else:
                color = TERRAIN_COLORS["snow"]
            
            row_colors.append(color)
            row_heights.append(h)
        
        map_data.append(row_colors)
        heightmap_data.append(row_heights)
    
    return map_data, heightmap_data


def _generate_urban_map(width, height, cell_size, seed=42):
    """
    Generate an urban battlemap with roads and buildings.
    
    Returns:
        tuple: (map_data, heightmap_data)
        - map_data: 2D list of RGB tuples
        - heightmap_data: 2D list of float values (0.0 to 1.0)
    """
    rng = random.Random(seed)
    
    # Create road grid
    road_interval = max(3, width // 4)
    
    map_data = []
    heightmap_data = []
    
    for y in range(height):
        row_colors = []
        row_heights = []
        for x in range(width):
            # Determine if this cell is a road
            is_road = (x % road_interval == 0) or (y % road_interval == 0)
            
            if is_road:
                color = URBAN_COLORS["road"]
                height = 0.1
            else:
                # Random building or park
                r = rng.random()
                if r < 0.15:
                    color = URBAN_COLORS["park"]
                    height = 0.2
                elif r < 0.7:
                    color = URBAN_COLORS["building"]
                    height = 0.5 + rng.random() * 0.3
                else:
                    color = URBAN_COLORS["water"]
                    height = 0.05
            
            row_colors.append(color)
            row_heights.append(height)
        
        map_data.append(row_colors)
        heightmap_data.append(row_heights)
    
    return map_data, heightmap_data


class PSN_Battlemap_Generate:
    """
    Generates a top-down battlemap as a 2D array of RGB colors and a corresponding
    heightmap for 3D rendering pipelines.
    
    The output is pure Python data (lists of lists) that can be easily converted
    to images by downstream nodes or external tools.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 10, "min": 1, "max": 100, "step": 1}),
                "height": ("INT", {"default": 10, "min": 1, "max": 100, "step": 1}),
                "cell_size": ("INT", {"default": 32, "min": 1, "max": 256, "step": 1}),
                "style": (GRID_STYLES,),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1, "step": 1})
            }
        }
    
    RETURN_TYPES = ("MAP_DATA", "HEIGHTMAP_DATA")
    RETURN_NAMES = ("map_image", "heightmap")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Battlemap"
    
    def run(self, width, height, cell_size, style, seed):
        """
        Generate the battlemap and heightmap.
        
        Args:
            width: Map width in cells
            height: Map height in cells
            cell_size: Size of each cell in pixels (used for metadata)
            style: Map style ("grid", "terrain", or "urban")
            seed: Random seed for reproducibility
        
        Returns:
            tuple: (map_data, heightmap_data)
            - map_data: 2D list of RGB tuples
            - heightmap_data: 2D list of float values (0.0 to 1.0)
        """
        # Validate inputs
        if width < 1 or height < 1:
            raise ValueError("Width and height must be at least 1")
        if cell_size < 1:
            raise ValueError("Cell size must be at least 1")
        if style not in GRID_STYLES:
            raise ValueError(f"Style must be one of {GRID_STYLES}")
        
        # Generate map based on style
        if style == "grid":
            map_data, heightmap_data = _generate_grid_map(width, height, cell_size, seed)
        elif style == "terrain":
            map_data, heightmap_data = _generate_terrain_map(width, height, cell_size, seed)
        elif style == "urban":
            map_data, heightmap_data = _generate_urban_map(width, height, cell_size, seed)
        else:
            raise ValueError(f"Unknown style: {style}")
        
        return (map_data, heightmap_data)


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Battlemap_Generate": PSN_Battlemap_Generate
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Battlemap_Generate": "Battlemap Generator"
}
