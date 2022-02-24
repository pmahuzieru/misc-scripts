"""
What does this script have to do? What should it offer the user?

Use cases:
    - Restrict: We have N branches whose BAAs (independently if default or custom/restricted) need to be restricted to X given zones.
    - Free up: We have N branches that have custom/not-default BAAs, but need to be freed from any restriction.
    - [NOT COMPLETE] Extend to zone: extend current BAA with a zone's geometry.

What should its output be?
    - The user wants the GeoJSON Django Admin-ready files for implementation for each N branches.

"""

from json import dumps
from os.path import dirname
from tkinter import Tk
from tkinter.filedialog import askdirectory, askopenfilename

from geopandas import GeoDataFrame
from numpy import isnan
from pandas import read_csv
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, mapping
from shapely.ops import transform
from shapely.wkt import loads

# Ask for files and save directory
Tk().withdraw()
acc_filetypes = (('CSV files','*.csv'),)

branches_filepath = askopenfilename(title='Select branches CSV', filetypes=acc_filetypes)
zones_filepath = askopenfilename(title='Select zones CSV', filetypes=acc_filetypes)

if branches_filepath and zones_filepath:

    save_dir = askdirectory(title='Select folder to save results:', initialdir=dirname(branches_filepath))

    # Read from CSVs
    branches = read_csv(branches_filepath)
    zones = read_csv(zones_filepath)

    # Transform into GeoDataFrames
    branches = GeoDataFrame(branches, geometry=branches.baa_wkt.apply(
        loads)).set_crs(4326).set_index('branch_id')
    zones = GeoDataFrame(zones, geometry=zones.zone_wkt.apply(
        loads)).set_crs(4326).set_index('zone_id')

    # Save what CRS we will be working on and the respective projection Transformers
    wgs84_crs = 'EPSG:4326'
    utm_crs = zones.estimate_utm_crs()
    to_utm_transformer = Transformer.from_crs(
        wgs84_crs, utm_crs, always_xy=True).transform
    to_wgs84_transformer = Transformer.from_crs(
        utm_crs, wgs84_crs, always_xy=True).transform

    # Select what branches to consider from the file
    br_input = input(
        'Enter [all] to consider all branches in file. Enter branch IDs separated by commas, otherwise: ')

    if br_input == 'all':
        branch_id_list = list(branches.index)
    else:
        branch_id_list = [int(id.strip()) for id in br_input.split(",")]

    # Select what zones to restrict to
    zone_input = input(
        "Enter the zone IDs to which you'd like to restrict (leave blank to 'free' the BAAs): ")

    free_from_all_zones = False
    if not zone_input:
        free_from_all_zones = True
    else:
        zone_id_list = [int(id.strip()) for id in zone_input.split(",")]
        selected_zone_union_geom = zones.loc[zone_id_list].geometry.unary_union

    # For each of the selected branches...
    for branch_id in branch_id_list:

        branch = branches.loc[branch_id]
        branch_loc = Point(branch.br_lng, branch.br_lat)

        # If there is no set branch_area_radius for the branch, then ask for input...
        if isnan(branch.branch_area_radius):
            print(
                f'>> Branch {branch.name} does not have a defined branch radius. Please enter it below [meters]:')
            branch_radius = int(input())
        else:
            branch_radius = branch.branch_area_radius

        # To recreate the branch area, buffer the branch location with branch_radius (reprojecting first into UTM!)
        default_baa_geom_utm = transform(
            to_utm_transformer, branch_loc).buffer(branch_radius)
        default_baa_geom = transform(
            to_wgs84_transformer, default_baa_geom_utm)

        # Intersect the recreated BAA with the selected zones unary union
        if not free_from_all_zones:
            new_baa_geom = MultiPolygon(
                [default_baa_geom.intersection(selected_zone_union_geom)])
        else:
            new_baa_geom = default_baa_geom

        # Save to GeoJSON file
        json_string = dumps(mapping(new_baa_geom))
        with open(f"{branch.store_id}_{branch.store}_{branch.name}_{branch.branch}.geojson", "w") as f:
            f.write(json_string)

    print('Done!')
