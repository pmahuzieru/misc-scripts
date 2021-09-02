"""
Script that will convert a file containing polygon geometries into a Geohash grid containing them
"""

from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from shapely import wkt
from shapely.ops import cascaded_union
from shapely.geometry import box, Polygon
import pandas as pd
import geopandas as gpd
import geohash

##### FUNCTIONS

def is_geohash_in_bounding_box(current_geohash, bbox_coordinates):
    """Checks if the box of a Geohash is inside the bounding box

    :param current_Geohash: a Geohash
    :param bbox_coordinates: bounding box coordinates
    :return: true if the the center of the Geohash is in the bounding box
    """

    coordinates = geohash.decode(current_geohash)
    geohash_in_bounding_box = (bbox_coordinates[1] < coordinates[0] < bbox_coordinates[3]) and (
            bbox_coordinates[0] < coordinates[1] < bbox_coordinates[2])
    return geohash_in_bounding_box

def is_geohash_intersecting_bounding_box(current_geohash, bbox_coordinates):
    """Checks if the box of a Geohash intersects the bounding box

    :param current_Geohash: a Geohash
    :param bbox_coordinates: bounding box coordinates
    :return: true if the the center of the Geohash is in the bounding box
    """

    geohash_poly = Polygon(build_geohash_box(current_geohash))

    bbox_poly = box(*bbox_coordinates)

    geohash_intersects_bounding_box = geohash_poly.intersects(bbox_poly)
    return geohash_intersects_bounding_box

def build_geohash_box(current_geohash):
    """Returns a GeoJSON Polygon for a given Geohash

    :param current_Geohash: a Geohash
    :return: a list representation of th polygon
    """

    b = geohash.bbox(current_geohash)
    polygon = [(b['w'], b['s']), (b['w'], b['n']), (b['e'], b['n']), (b['e'], b['s'],), (b['w'], b['s'])]
    return polygon

def compute_geohash_tiles(bbox_coordinates, precision = 6):
    """Computes all Geohash tile in the given bounding box

    :param bbox_coordinates: the bounding box coordinates of the Geohashes
    :return: a list of Geohashes
    """

    checked_geohashes = set()
    geohash_stack = set()
    geohashes = []
    # get center of bounding box, assuming the earth is flat ;)
    center_latitude = (bbox_coordinates[1] + bbox_coordinates[3]) / 2
    center_longitude = (bbox_coordinates[0] + bbox_coordinates[2]) / 2

    center_geohash = geohash.encode(center_latitude, center_longitude, precision=precision)
    geohashes.append(center_geohash)
    geohash_stack.add(center_geohash)
    checked_geohashes.add(center_geohash)
    while len(geohash_stack) > 0:
        current_geohash = geohash_stack.pop()
        neighbors = geohash.neighbors(current_geohash)
        for neighbor in neighbors:
            if neighbor not in checked_geohashes and is_geohash_intersecting_bounding_box(neighbor, bbox_coordinates):
                geohashes.append(neighbor)
                geohash_stack.add(neighbor)
                checked_geohashes.add(neighbor)
    return geohashes

def get_geohash_grid_df(gdf, precision = 6):
	"""
	From a GeoDataFrame, build a DataFrame object containing the geohash grid and their single polygons
	"""

	geoms = [g for g in gdf.geometry]
			
	union_geom = cascaded_union(geoms)

	# Get union_geom bounding box to determine Geohash grid limits
	geohash_list = compute_geohash_tiles(union_geom.bounds, 6)

	geohash_poly_list = []
	for geohash_str in geohash_list:
		geohash_poly = Polygon(build_geohash_box(geohash_str))
		geohash_poly_list.append(geohash_poly)
	
	geohash_df = pd.DataFrame(zip(geohash_list, geohash_poly_list), columns=['geohash','wkt'])

	return geohash_df

#####
print('')
print('## Please select file to use')

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
filename = askopenfilename() # show an "Open" dialog box and return the path to the selected file

# File should be either a CSV with a WKT field, or a GeoJSON file with a single geometry.

accepted_ext = ['.csv','.geojson']

if filename:

	dot_index = filename.find('.')
	file_ext = filename[dot_index:]

	if file_ext in accepted_ext:

		if file_ext == '.csv':

			# Handle as CSV, look for WKT column
			df = pd.read_csv(filename)

			print('Which of {} is the geometry column? (WKT format)'.format(list(df.columns)))
			ask = True

			while ask:
				wkt_col = input()
				if wkt_col not in df.columns:
					print('"{}" column not available. Please try again.'.format(wkt_col))
				else:
					ask = False
			
			# Transform the union of all geometries into a Geohash grid. The geometries must be polygons
			gdf = gpd.GeoDataFrame(df, geometry=df[wkt_col].apply(wkt.loads))
			
			geohash_df = get_geohash_grid_df(gdf)

			save_path = asksaveasfilename()

			geohash_df.to_csv(save_path, index=False)
			print('File saved in {}'.format(save_path))


		elif file_ext == '.geojson':
			# Handle as GeoJSON
			gdf = gpd.read_file(filename)
			geohash_df = get_geohash_grid_df(gdf)

			save_path = asksaveasfilename()

			geohash_df.to_csv(save_path, index=False)
			print('File saved in {}'.format(save_path))

	else:
		print('File must be CSV or GeoJSON. "{}" currently not supported.'.format(file_ext))
		