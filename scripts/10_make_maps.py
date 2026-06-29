import ssl
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from shapely.geometry import Point

ssl._create_default_https_context = ssl._create_unverified_context

ROOT = Path(__file__).resolve().parents[1]

def get_india_map():
    """Streams the official administrative state boundaries of India."""
    url = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
    return gpd.read_file(url)

def generate_continuous_surface(df: pd.DataFrame, value_col: str, india_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Interpolates point data across a dense coordinate grid and 
    strictly filters out empty values and ocean pixels.
    """
    # Clean incoming data to ensure no NaN target values exist
    df = df.dropna(subset=[value_col, "longitude", "latitude"])
    
    if len(df) < 2:
        return gpd.GeoDataFrame()
        
    # 1. Create a dense grid matrix wrapping India's spatial zone
    lon_grid = np.linspace(67, 98, 200)
    lat_grid = np.linspace(6, 38, 200)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    
    known_points = df[["longitude", "latitude"]].values
    known_values = df[value_col].values
    
    # 2. Run multi-tier grid interpolation (Linear with explicit Nearest neighbor padding)
    grid_values = griddata(known_points, known_values, (lon_mesh, lat_mesh), method='linear')
    nan_mask = np.isnan(grid_values)
    if np.any(nan_mask):
        grid_values[nan_mask] = griddata(known_points, known_values, (lon_mesh, lat_mesh), method='nearest')[nan_mask]
        
    # 3. Flatten structure into a pandas dataframe layout
    flat_lon = lon_mesh.flatten()
    flat_lat = lat_mesh.flatten()
    flat_val = grid_values.flatten()
    
    grid_df = pd.DataFrame({"longitude": flat_lon, "latitude": flat_lat, value_col: flat_val})
    geometry = [Point(xy) for xy in zip(grid_df["longitude"], grid_df["latitude"])]
    geo_grid = gpd.GeoDataFrame(grid_df, geometry=geometry, crs="EPSG:4326")
    
    # 4. Clip the smooth mesh layer cleanly inside national borders
    if hasattr(india_gdf, "union_all"):
        india_dissolved = india_gdf.union_all()
    else:
        india_dissolved = india_gdf.unary_union
        
    inside_mask = geo_grid.geometry.within(india_dissolved)
    filtered_gdf = geo_grid[inside_mask].copy()
    
    # CRITICAL FIX: Ensure no leftover non-finite edge elements bypass the filter
    filtered_gdf = filtered_gdf.dropna(subset=[value_col])
    return filtered_gdf

def render_surface_map(df: pd.DataFrame, value_col: str, title: str, out_path: Path, india_gdf: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 10))
    
    # Compute the seamless continuous data sheet
    surface_gdf = generate_continuous_surface(df, value_col, india_gdf)
    
    # 1. Render smooth color gradients behind frame details
    if not surface_gdf.empty:
        surf = ax.tricontourf(
            surface_gdf["longitude"], surface_gdf["latitude"], surface_gdf[value_col],
            levels=50, cmap="turbo", alpha=0.85, zorder=1
        )
        cbar = fig.colorbar(surf, ax=ax, shrink=0.8, pad=0.04)
        cbar.set_label(value_col, fontsize=11, weight='bold', labelpad=10)
        
    # 2. Render state outlines precisely over the color layer
    india_gdf.plot(ax=ax, color="none", edgecolor="#444444", linewidth=0.8, zorder=2)
    ax.grid(True, linestyle="--", alpha=0.25, color="#6c757d", zorder=0)
    
    # 3. Overlay the exact monitor markers as white validation anchors
    ax.scatter(
        df["longitude"], df["latitude"], 
        color="white", edgecolor="black", s=100, linewidth=1.6, 
        label="Anchor Monitoring Stations", zorder=3
    )
    
    ax.set_xlim(67, 98)
    ax.set_ylim(6, 38)
    ax.set_title(title, fontsize=14, pad=15, fontweight='bold')
    ax.set_xlabel("Longitude (Degrees East)", fontsize=10, labelpad=8)
    ax.set_ylabel("Latitude (Degrees North)", fontsize=10, labelpad=8)
    ax.legend(loc="upper right", facecolor="#ffffff", framealpha=0.9)
    
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=250)
    plt.close(fig)

def main() -> None:
    print("Loading official India map layout framework...")
    try:
        india_gdf = get_india_map()
    except Exception as e:
        print(f"CRITICAL Base Map Load Failed: {e}")
        return

    # --- PROCESS SURFACE LAYER AQI ---
    aqi_path = ROOT / "data" / "processed" / "station_aqi_daily.csv"
    registry_path = ROOT / "data" / "processed" / "stations_registry.csv"
    
    if aqi_path.exists() and registry_path.exists():
        print("Compiling Continuous Spatial Surfaces for Ground Sensor Grids...")
        aqi = pd.read_csv(aqi_path).drop(columns=["latitude", "longitude"], errors="ignore")
        registry = pd.read_csv(registry_path)
        
        lat_map = {row['station'].lower(): row['latitude'] for _, row in registry.iterrows()}
        lon_map = {row['station'].lower(): row['longitude'] for _, row in registry.iterrows()}
        
        def match_coord(s, c_dict):
            sc = str(s).lower()
            for k, val in c_dict.items():
                if k in sc or sc in k: return val
            return None

        aqi["latitude"] = aqi["station"].apply(lambda x: match_coord(x, lat_map))
        aqi["longitude"] = aqi["station"].apply(lambda x: match_coord(x, lon_map))
        aqi_mapped = aqi.dropna(subset=["latitude", "longitude"])
        
        aqi_spatial = aqi_mapped.groupby(["station", "latitude", "longitude"])["AQI"].mean().reset_index()
        
        if not aqi_spatial.empty:
            render_surface_map(aqi_spatial, "AQI", "Interpolated Continuous AQI Surface over India Map", ROOT / "outputs" / "maps" / "station_aqi.png", india_gdf)
            print("Wrote smooth continuous vector output to outputs/maps/station_aqi.png\n")

    print("Pipeline compilation finished successfully.")

if __name__ == "__main__":
    main()